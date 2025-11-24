# models.py
from flask_sqlalchemy import SQLAlchemy
from decimal import Decimal

db = SQLAlchemy()

class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=True)
    symbol = db.Column(db.String(32), index=True, nullable=True)
    side = db.Column(db.String(8), nullable=True)  # 'buy' | 'sell'
    price = db.Column(db.Numeric(24, 8), nullable=False, default=Decimal("0"))
    quantity = db.Column(db.Numeric(24, 8), nullable=False, default=Decimal("0"))
    unix_time = db.Column(db.Integer, index=True, nullable=False)

def init_database(app, allow_create_all=False):
    """Helper used by CLI for first-time bootstrap (dev only)."""
    if allow_create_all:
        with app.app_context():
            db.create_all()

class Liquidity(db.Model):
    __tablename__ = "liquidity"
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(32), nullable=False, index=True)
    window_start_unix = db.Column(db.Integer, nullable=False)
    window_end_unix = db.Column(db.Integer, nullable=False)
    volume_usd = db.Column(db.Numeric(24, 8), nullable=False, server_default="0")
    trades_count = db.Column(db.Integer, nullable=False, server_default="0")
    liq_score = db.Column(db.Numeric(24, 8), nullable=False, server_default="0")


class LiquidityResults(db.Model):
    __tablename__ = "liquidity_results"
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(64), nullable=False)
    symbol = db.Column(db.String(32), nullable=False, index=True)
    window_start_unix = db.Column(db.Integer, nullable=False)
    window_end_unix = db.Column(db.Integer, nullable=False)
    volume_usd = db.Column(db.Numeric(24, 8), nullable=False, server_default="0")
    trades_count = db.Column(db.Integer, nullable=False, server_default="0")
    liq_score = db.Column(db.Numeric(24, 8), nullable=False, server_default="0")