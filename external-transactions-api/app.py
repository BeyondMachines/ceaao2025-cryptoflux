import os
import random
import hashlib
import sqlite3
from datetime import datetime, timedelta, timezone
from flask import Flask, jsonify, request

app = Flask(__name__)

USE_SQLITE = os.getenv("USE_SQLITE", "False").lower() in ("1", "true", "yes")

# ----- API Key Class -----
class ApiKey:
    def __init__(self, hashed_key, salt):
        self.hashed_key = hashed_key
        self.salt = salt

    def verify(self, provided_key):
        combined = provided_key + self.salt
        hashed_input = hashlib.sha256(combined.encode()).hexdigest()
        return hashed_input == self.hashed_key

def load_api_key_from_sqlite():
    db_path = os.getenv("API_KEY_DB_PATH", "api_keys.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT hashed_key, salt FROM api_keys LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        return ApiKey(hashed_key=row[0], salt=row[1])
    return None

def load_api_key_from_env():
    hashed_key = os.getenv("HASHED_API_KEY")
    salt = os.getenv("SALT")
    if hashed_key and salt:
        return ApiKey(hashed_key=hashed_key, salt=salt)
    return None

def load_api_key():
    return load_api_key_from_sqlite() if USE_SQLITE else load_api_key_from_env()

def verify_api_key(provided_key):
    key_obj = load_api_key()
    if not key_obj:
        return False
    return key_obj.verify(provided_key)

# ----- Crypto Lookup -----
CRYPTO_LOOKUP = {
    "BTC-USD": {"name": "Bitcoin", "symbol": "BTC", "pair": "BTC-USD", "anchor_price": 112028},
    "ETH-USD": {"name": "Ethereum", "symbol": "ETH", "pair": "ETH-USD", "anchor_price": 4173.18},
    "SOL-USD": {"name": "Solana", "symbol": "SOL", "pair": "SOL-USD", "anchor_price": 215.15},
    "USDT-USD": {"name": "Tether", "symbol": "USDT", "pair": "USDT-USD", "anchor_price": 1.00},
    "BNB-USD": {"name": "Binance Coin", "symbol": "BNB", "pair": "BNB-USD", "anchor_price": 1016.72},
    "XRP-USD": {"name": "XRP", "symbol": "XRP", "pair": "XRP-USD", "anchor_price": 2.85},
}
SYMBOLS = list(CRYPTO_LOOKUP.keys())

# ----- Transaction Generator -----
def gen_transactions(n: int):
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=24)
    base_times = [
        start + i * (now - start) / max(n - 1, 1) for i in range(n)
    ]
    rng = random.Random()

    adjusted_anchors = {}
    for sym in SYMBOLS:
        direction = rng.choice([-1, 1])
        adjustment = 1.0 + (0.10 * direction)
        adjusted_anchors[sym] = CRYPTO_LOOKUP[sym]["anchor_price"] * adjustment

    running_price = {sym: adjusted_anchors[sym] for sym in SYMBOLS}

    def qty_for(sym: str):
        if sym == "BTC-USD":  return max(0.0001, abs(rng.gauss(0.02, 0.02)))
        if sym == "ETH-USD":  return max(0.001,  abs(rng.gauss(0.3, 0.25)))
        if sym == "SOL-USD":  return max(0.01,   abs(rng.gauss(2.0, 1.5)))
        if sym == "USDT-USD": return max(1.0,    abs(rng.gauss(500.0, 300.0)))
        if sym == "BNB-USD":  return max(0.005,  abs(rng.gauss(0.5, 0.4)))
        if sym == "XRP-USD":  return max(1.0,    abs(rng.gauss(200.0, 150.0)))
        return max(0.01, abs(rng.gauss(1.0, 0.8)))

    out = []
    for t in base_times:
        sym = rng.choice(SYMBOLS)
        step = rng.uniform(-0.002, 0.002)
        running_price[sym] = max(0.0001, running_price[sym] * (1.0 + step))

        jitter_secs = rng.uniform(-60, 60)
        ts = int((t + timedelta(seconds=jitter_secs)).timestamp())

        out.append({
            "symbol": sym,
            "name": CRYPTO_LOOKUP[sym]["name"],
            "side": rng.choice(["buy", "sell"]),
            "price": round(running_price[sym], 6),
            "quantity": round(qty_for(sym), 8),
            "unix_time": ts,
        })

    rng.shuffle(out)
    return out

# ----- Routes -----
@app.get("/")
def index():
    return jsonify({
        "status": "ok",
        "message": "Welcome. Try /api/v1/transactions (requires API key), /health, or /api/v1/lookup"
    })

@app.get("/health")
def health():
    return jsonify({"status": "healthy"}), 200

@app.get("/api/v1/lookup")
def get_lookup():
    return jsonify(CRYPTO_LOOKUP)

@app.get("/api/v1/transactions")
def get_transactions():
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return jsonify({"error": "Missing API key"}), 401
    if not verify_api_key(api_key):
        return jsonify({"error": "Invalid API key"}), 403

    try:
        count_param = int(request.args.get("count", "0"))
    except Exception:
        count_param = 0

    n = random.randint(200, 300) if count_param <= 0 else max(1, min(1000, count_param))
    data = gen_transactions(n)
    return jsonify({"count": len(data), "data": data})

# ----- App Run -----
if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
