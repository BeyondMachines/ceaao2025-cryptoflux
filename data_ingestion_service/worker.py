#!/usr/bin/env python3
"""
Data Ingestion Worker (precompute mode)
- Fetches random trades from External Trading API
- Inserts raw rows into `transactions`
- Recomputes last N minutes of 5-min aggregates into `aggregates_5m`
- Prunes old raw rows to keep DB small
"""
import os
import time
import requests
import psycopg2
from psycopg2.extras import execute_batch
from datetime import datetime
from decimal import Decimal

# --- Config ---
EXT_API_URL      = os.getenv("EXT_API_URL")
EXT_API_KEY      = os.getenv("EXT_API_KEY")
INTERVAL_SECONDS = int(os.getenv("INTERVAL_SECONDS", "300"))   # poll cadence
BATCH_SIZE       = int(os.getenv("BATCH_SIZE", "100"))         # API rows per pull
RETENTION_DAYS   = int(os.getenv("RETENTION_DAYS", "1"))       # keep raw rows
AGG_LOOKBACK_MIN = int(os.getenv("AGG_LOOKBACK_MIN", "60"))    # recompute last N minutes of 5-min buckets


DB_HOST = os.environ.get('DB_HOST')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_NAME = os.environ.get('DB_NAME')
DB_USER = os.environ.get('DB_USER')
DB_PASS = os.environ.get('DB_PASS')
DATABASE_URL = f'postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'


# --- DB util ---

DATABASE_URL

def get_db_connection():
    url = DATABASE_URL.replace("postgresql+psycopg2://", "postgresql://")
    return psycopg2.connect(url)

def ensure_schema(conn):
    """Make sure aggregates table + helpful indexes exist."""
    with conn.cursor() as cur:
        # aggregates_5m
        cur.execute("""
            CREATE TABLE IF NOT EXISTS aggregates_5m (
              symbol       VARCHAR(32) NOT NULL,
              bucket_unix  INTEGER     NOT NULL,
              volume_usd   NUMERIC(24,8) NOT NULL DEFAULT 0,
              trades_count INTEGER       NOT NULL DEFAULT 0,
              PRIMARY KEY (symbol, bucket_unix)
            );
        """)
        # indexes (idempotent)
        cur.execute("CREATE INDEX IF NOT EXISTS ix_tx_symbol ON transactions(symbol);")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_tx_unix   ON transactions(unix_time);")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_agg5m_symbol ON aggregates_5m(symbol);")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_agg5m_bucket ON aggregates_5m(bucket_unix);")
    conn.commit()

# --- API ---
def fetch_transactions(count=None):
    headers = {"X-API-Key": EXT_API_KEY} if EXT_API_KEY else {}
    params  = {"count": count} if count else {}
    r = requests.get(EXT_API_URL, headers=headers, params=params, timeout=20)
    r.raise_for_status()
    payload = r.json()
    return payload["data"] if isinstance(payload, dict) else payload

# --- Transform/validate ---
def validate_tx(tx):
    try:
        name   = tx.get("name")
        symbol = tx.get("symbol")
        side   = tx.get("side")
        price  = Decimal(str(tx["price"]))
        qty    = Decimal(str(tx["quantity"]))
        unix   = int(tx.get("unix_time") or int(datetime.utcnow().timestamp()))
        return (name, symbol, side, price, qty, unix)
    except Exception:
        return None

# --- Load raw ---
def insert_raw(conn, txs):
    valid = [v for v in (validate_tx(t) for t in txs) if v]
    if not valid:
        return 0
    sql = """
      INSERT INTO transactions (name, symbol, side, price, quantity, unix_time)
      VALUES (%s,%s,%s,%s,%s,%s)
    """
    with conn.cursor() as cur:
        execute_batch(cur, sql, valid, page_size=1000)
    conn.commit()
    return len(valid)

# --- Aggregate 5m (REPLACE the last N minutes) ---
def upsert_agg_5m(conn, lookback_min=60):
    """
    Recompute all 5-min buckets that intersect the last `lookback_min` minutes.
    We REPLACE existing rows to avoid double counting.
    """
    with conn.cursor() as cur:
        cur.execute(f"""
            WITH agg AS (
              SELECT
                symbol,
                (FLOOR(unix_time/300.0)*300)::int AS bucket_unix,
                SUM((price::numeric)*(quantity::numeric)) AS volume_usd,
                COUNT(*) AS trades_count
              FROM transactions
              WHERE unix_time >= EXTRACT(EPOCH FROM (NOW() - INTERVAL '{lookback_min} minutes'))
              GROUP BY symbol, (FLOOR(unix_time/300.0)*300)::int
            )
            INSERT INTO aggregates_5m(symbol, bucket_unix, volume_usd, trades_count)
            SELECT symbol, bucket_unix, volume_usd, trades_count
            FROM agg
            ON CONFLICT (symbol, bucket_unix) DO UPDATE
            SET volume_usd   = EXCLUDED.volume_usd,
                trades_count = EXCLUDED.trades_count;
        """)
    conn.commit()

# --- One cycle ---
def run_cycle():
    print("\n" + "="*60)
    print(f"Starting ingestion cycle at {datetime.now().isoformat()}")
    print("="*60)

    txs = fetch_transactions(count=BATCH_SIZE)
    print(f"Received {len(txs)} transactions")

    with get_db_connection() as conn:
        ensure_schema(conn)
        inserted = insert_raw(conn, txs)
        print(f"Inserted raw rows: {inserted}")

        upsert_agg_5m(conn, lookback_min=AGG_LOOKBACK_MIN)
        print(f"Updated 5-min aggregates (last {AGG_LOOKBACK_MIN} min)")


    total_vol = sum(float(t.get("price", 0)) * float(t.get("quantity", 0)) for t in txs)
    print(f"Total batch volume: ${total_vol:,.2f}")

# --- Main loop ---
def main():
    print("="*60)
    print("Data Ingestion Worker (precompute mode)")
    print("="*60)
    print(f"External API: {EXT_API_URL}")
    print(f"Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'configured'}")
    print(f"Poll Interval: {INTERVAL_SECONDS}s | Batch Size: {BATCH_SIZE}")
    print(f"Raw retention: {RETENTION_DAYS} days | Agg lookback: {AGG_LOOKBACK_MIN} min")
    print("="*60)

    # quick DB readiness probe
    for i in range(30):
        try:
            with get_db_connection() as c:
                with c.cursor() as cur:
                    cur.execute("SELECT 1;")
            break
        except Exception:
            time.sleep(2)

    cycles = ok = bad = 0
    while True:
        cycles += 1
        try:
            run_cycle()
            ok += 1
        except KeyboardInterrupt:
            print("Shutdown requested.")
            break
        except Exception as e:
            bad += 1
            print(f"Cycle failed: {e}")
        print(f"\nStats: cycles={cycles} ok={ok} bad={bad}")
        print(f"Sleeping {INTERVAL_SECONDS}s…")
        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
