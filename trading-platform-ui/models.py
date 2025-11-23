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
