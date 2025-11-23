# application/home.py
from flask import render_template
from models import db, Transaction

def index():
    tx_count = db.session.query(Transaction).count()
    return render_template("index.html", tx_count=tx_count)
