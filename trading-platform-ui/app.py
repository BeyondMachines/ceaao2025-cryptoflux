# app.py
import os
import click
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_migrate import Migrate, upgrade
from flask.cli import with_appcontext
from sqlalchemy import func, desc, case

from config import Config
from models import db, init_database, Transaction
from application.home import index

load_dotenv()


def create_app(config_class=Config):
    """Application factory."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Cookie/session hardening
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = (
        False if os.getenv("LOCAL_TEST", "").lower() == "true" else True
    )

    # Extensions
    db.init_app(app)
    Migrate(app, db)

    # Routes
    app.add_url_rule("/", "index", index)

    # Optional: keep your existing API blueprint
    try:
        from application.api import bp as api_bp
        app.register_blueprint(api_bp)
    except Exception:
        # If the blueprint doesn't exist yet, that's fine for now
        pass

    # ---- Health ----
    @app.get("/health")
    def health():
        # simple OK without DB ping (healthchecks should be cheap)
        return jsonify({"status": "ok"}), 200

    @app.get("/api/health")
    def api_health():
        # quick DB ping
        try:
            _ = db.session.execute(func.now()).scalar()
            return jsonify({"status": "ok"})
        except Exception as e:
            app.logger.warning(f"/api/health failed: {e}")
            return jsonify({"status": "error"}), 500

    # ---- Stats (smart fallback window) ----
    @app.get("/api/stats")
    def api_stats():
        """
        Returns KPIs + chart data for either:
          - last 7 days (if there is data), or
          - the most recent available window (at least 24h) when ?fallback=1
            or when last-7d is empty.
        """
        latest_ts = db.session.query(func.max(Transaction.timestamp)).scalar()
        if not latest_ts:
            return jsonify({
                "kpis": {"tx_count": 0, "total_volume_usd": 0, "buy_count": 0, "sell_count": 0},
                "series": [],
                "by_symbol_bar": [],
                "top_by_volume": [],
                "top_by_count": [],
                "meta": {"window_label": "no-data"}
            })

        fallback = request.args.get("fallback", type=int) == 1

        end_ts = latest_ts
        start_7d = end_ts - timedelta(days=7)

        has_7d = (
            db.session.query(func.count(Transaction.id))
            .filter(Transaction.timestamp.between(start_7d, end_ts))
            .scalar()
            > 0
        )

        if has_7d and not fallback:
            start_ts = start_7d
            window_label = "last-7d"
        else:
            start_ts = max(end_ts - timedelta(days=1), end_ts - timedelta(days=7))
            window_label = "most-recent"

        # KPIs
        k_count, k_volume, k_buy, k_sell = (
            db.session.query(
                func.count().label("tx_count"),
                func.coalesce(func.sum(Transaction.amount_usd), 0).label("total_volume_usd"),
                func.coalesce(func.sum(case((Transaction.side == "BUY", 1), else_=0)), 0).label("buy_count"),
                func.coalesce(func.sum(case((Transaction.side == "SELL", 1), else_=0)), 0).label("sell_count"),
            )
            .filter(Transaction.timestamp.between(start_ts, end_ts))
            .one()
        )

        # Series: bucket by day
        series_rows = (
            db.session.query(
                func.date_trunc("day", Transaction.timestamp).label("bucket"),
                func.coalesce(func.sum(Transaction.amount_usd), 0).label("volume"),
            )
            .filter(Transaction.timestamp.between(start_ts, end_ts))
            .group_by(func.date_trunc("day", Transaction.timestamp))
            .order_by(func.date_trunc("day", Transaction.timestamp))
            .all()
        )

        # Volume by symbol (top 10)
        by_symbol_rows = (
            db.session.query(
                Transaction.symbol,
                func.coalesce(func.sum(Transaction.amount_usd), 0).label("volume"),
            )
            .filter(Transaction.timestamp.between(start_ts, end_ts))
            .group_by(Transaction.symbol)
            .order_by(desc("volume"))
            .limit(10)
            .all()
        )

        # Top by count (top 10)
        top_by_count_rows = (
            db.session.query(
                Transaction.symbol,
                func.count().label("count"),
                func.coalesce(func.sum(Transaction.amount_usd), 0).label("volume"),
            )
            .filter(Transaction.timestamp.between(start_ts, end_ts))
            .group_by(Transaction.symbol)
            .order_by(desc("count"))
            .limit(10)
            .all()
        )

        series = [
            {"bucket_ts": r.bucket.replace(tzinfo=timezone.utc).isoformat(), "volume": float(r.volume or 0)}
            for r in series_rows
        ]
        by_symbol_bar = [{"symbol": r.symbol, "volume": float(r.volume or 0)} for r in by_symbol_rows]
        top_by_volume = [{"symbol": r.symbol, "volume": float(r.volume or 0)} for r in by_symbol_rows]
        top_by_count = [
            {"symbol": r.symbol, "count": int(r.count or 0), "volume": float(r.volume or 0)}
            for r in top_by_count_rows
        ]

        return jsonify({
            "kpis": {
                "tx_count": int(k_count or 0),
                "total_volume_usd": float(k_volume or 0),
                "buy_count": int(k_buy or 0),
                "sell_count": int(k_sell or 0),
            },
            "series": series,
            "by_symbol_bar": by_symbol_bar,
            "top_by_volume": top_by_volume,
            "top_by_count": top_by_count,
            "meta": {
                "window_start_iso": start_ts.replace(tzinfo=timezone.utc).isoformat(),
                "window_end_iso": end_ts.replace(tzinfo=timezone.utc).isoformat(),
                "window_label": window_label,
            },
        })

    # ---- CLI helpers ----
    @click.command("upgrade-db")
    @with_appcontext
    def upgrade_db_cmd():
        """Apply Alembic migrations."""
        upgrade()
        click.echo("Migrations applied.")

    @click.command("create-all")
    @with_appcontext
    def create_all_cmd():
        """Create tables directly (dev/test only)."""
        init_database(app, allow_create_all=True)
        click.echo("db.create_all() executed.")

    @click.command("init-db")
    @with_appcontext
    def init_db_cmd():
        """Try migrations; if none exist, fall back to create_all."""
        try:
            upgrade()
            click.echo("Migrations applied.")
        except Exception as e:
            app.logger.warning(f"Upgrade failed, fallback create_all: {e}")
            init_database(app, allow_create_all=True)
            click.echo("Ran create_all() fallback.")

    app.cli.add_command(upgrade_db_cmd)
    app.cli.add_command(create_all_cmd)
    app.cli.add_command(init_db_cmd)

    return app


if __name__ == "__main__":
    app = create_app()
    debug_mode = os.environ.get("FLASK_DEBUG", "True").lower() == "true"
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
