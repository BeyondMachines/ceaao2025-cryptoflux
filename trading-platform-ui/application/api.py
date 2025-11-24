# application/api.py
import os
import requests
import datetime
from decimal import Decimal

from flask import Blueprint, jsonify, current_app, request
from sqlalchemy import func, text

from models import db, Transaction, LiquidityResults

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.get("/health")
def health():
    """
    Health is tied strictly to whether '/' (home) can render successfully.
    """
    try:
        with current_app.test_request_context("/"):
            _ = current_app.view_functions["index"]()
        return jsonify({"status": "ok", "home_render": True}), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "home_render": False,
            "reason": str(e)[:300]
        }), 500


@bp.post("/seed")
def seed():
    """
    Fetch transactions from external API and insert them.

    Expected payload from EXT_API_URL:
      { "count": <int>, "data": [
          { "symbol","name","side","price","quantity","unix_time" }, ...
        ] }
    """
    url = os.getenv("EXT_API_URL")
    api_key = os.getenv("EXT_API_KEY")

    if not url:
        return jsonify({"error": "EXT_API_URL not set"}), 400

    headers = {"X-API-Key": api_key} if api_key else {}

    try:
        r = requests.get(url, headers=headers, timeout=20)
    except Exception as e:
        current_app.logger.exception("External API request failed")
        return jsonify({"error": f"request_failed: {e.__class__.__name__}: {e}"}), 502

    if r.status_code != 200:
        return jsonify({
            "error": "ext_api_failed",
            "status": r.status_code,
            "body": r.text[:500]
        }), 502

    try:
        payload = r.json()
    except Exception as e:
        return jsonify({"error": f"invalid_json: {e}"}), 502

    # Support both {"data":[...]} and bare list responses
    items = payload.get("data", payload if isinstance(payload, list) else [])
    if not isinstance(items, list):
        return jsonify({"error": "unexpected_payload_shape"}), 502

    to_insert = []
    for it in items:
        try:
            t = Transaction(
                name=it.get("name"),
                symbol=it.get("symbol"),
                side=it.get("side"),
                price=Decimal(str(it.get("price") if it.get("price") is not None else "0")),
                quantity=Decimal(str(it.get("quantity") if it.get("quantity") is not None else "0")),
                unix_time=int(it.get("unix_time")) if it.get("unix_time") is not None
                          else int(datetime.datetime.utcnow().timestamp()),
            )
            to_insert.append(t)
        except Exception as e:
            current_app.logger.warning(
                f"Skipping malformed item: {e}; item={str(it)[:200]}"
            )

    if not to_insert:
        return jsonify({"inserted": 0, "reason": "no_valid_rows"}), 200

    try:
        db.session.add_all(to_insert)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("DB insert failed")
        return jsonify({"error": f"db_insert_failed: {e.__class__.__name__}: {e}"}), 500

    return jsonify({
        "inserted": len(to_insert),
        "ext_reported": payload.get("count")
    }), 201


# ---------- Dashboard stats for UI ----------

def _d(value):
    """Safe decimal->float for JSON."""
    if isinstance(value, Decimal):
        return float(value)
    return value


@bp.get("/stats")
def stats():
    """
    Aggregated stats for the dashboard.

    Returns JSON:
      {
        "kpis": {
          "tx_count", "total_volume_usd", "buy_count", "sell_count"
        },
        "top_by_volume": [{symbol, volume, count}],
        "top_by_count":  [{symbol, count, volume}],
        "series_7d":     [{bucket_ts, volume}],          # daily volume last 7 days
        "by_symbol_bar": [{symbol, volume}]              # total volume by symbol
      }
    """
    # KPIs
    tx_count = db.session.query(func.count(Transaction.id)).scalar() or 0
    total_volume = db.session.query(
        func.coalesce(func.sum(Transaction.price * Transaction.quantity), 0)
    ).scalar() or Decimal("0")

    # side counts
    side_counts = dict(
        db.session.query(Transaction.side, func.count(Transaction.id))
        .group_by(Transaction.side)
        .all()
    )
    buy_count = int(side_counts.get("buy", 0) or 0)
    sell_count = int(side_counts.get("sell", 0) or 0)

    # Query param ?limit=N (defaults to 5)
    try:
        limit = int(request.args.get("limit", "5"))
    except Exception:
        limit = 5
    limit = max(1, min(50, limit))

    # Top by volume
    top_by_volume = [
        {"symbol": s, "volume": _d(v), "count": int(c)}
        for s, v, c in db.session.query(
            Transaction.symbol.label("symbol"),
            func.coalesce(func.sum(Transaction.price * Transaction.quantity), 0).label("vol"),
            func.count(Transaction.id).label("cnt"),
        )
        .group_by(Transaction.symbol)
        .order_by(func.coalesce(func.sum(Transaction.price * Transaction.quantity), 0).desc())
        .limit(limit)
        .all()
    ]

    # Top by count
    top_by_count = [
        {"symbol": s, "count": int(c), "volume": _d(v)}
        for s, c, v in db.session.query(
            Transaction.symbol.label("symbol"),
            func.count(Transaction.id).label("cnt"),
            func.coalesce(func.sum(Transaction.price * Transaction.quantity), 0).label("vol"),
        )
        .group_by(Transaction.symbol)
        .order_by(func.count(Transaction.id).desc())
        .limit(limit)
        .all()
    ]

    # 7-day daily volume series
    series_rows = db.session.execute(
        text("""
            SELECT
              date_trunc('day', to_timestamp(unix_time)) AS bucket_ts,
              SUM(price * quantity) AS volume
            FROM transactions
            WHERE to_timestamp(unix_time) >= NOW() - INTERVAL '7 days'
            GROUP BY 1
            ORDER BY 1
        """)
    ).fetchall()

    series_7d = [
        {"bucket_ts": r[0].isoformat(), "volume": _d(r[1] or 0)}
        for r in series_rows
    ]

    # Bar: volume by symbol (all-time)
    by_symbol_rows = db.session.query(
        Transaction.symbol,
        func.coalesce(func.sum(Transaction.price * Transaction.quantity), 0).label("vol"),
    ).group_by(Transaction.symbol).order_by(
        func.sum(Transaction.price * Transaction.quantity).desc()
    ).all()

    by_symbol_bar = [{"symbol": s, "volume": _d(v)} for s, v in by_symbol_rows]

    # Liquidity data from liquidity_results (top 10 by liq_score)
    liquidity_data = [
        {
            "symbol": row.symbol,
            "liq_score": _d(row.liq_score),
            "volume_usd": _d(row.volume_usd),
            "trades_count": int(row.trades_count),
            "job_id": row.job_id
        }
        for row in db.session.query(LiquidityResults)
        .order_by(LiquidityResults.liq_score.desc())
        .limit(10)
        .all()
    ]

    return jsonify({
        "kpis": {
            "tx_count": int(tx_count),
            "total_volume_usd": _d(total_volume),
            "buy_count": buy_count,
            "sell_count": sell_count,
        },
        "top_by_volume": top_by_volume,
        "top_by_count": top_by_count,
        "series_7d": series_7d,
        "by_symbol_bar": by_symbol_bar,
        "liquidity": liquidity_data,  # NEW
    })
