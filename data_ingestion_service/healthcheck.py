import os, sys, psycopg2

DB = dict(
  host=os.getenv('DB_HOST','postgres'),
  port=int(os.getenv('DB_PORT','5432')),
  dbname=os.getenv('DB_NAME','cryptoflux'),
  user=os.getenv('DB_USER','cryptouser'),
  password=os.getenv('DB_PASS','crypto'),
)

# fail if the newest transaction is older than this
MAX_STALENESS_SEC = int(os.getenv('HEARTBEAT_MAX_AGE_SEC','1800'))  # 30 min

try:
    with psycopg2.connect(connect_timeout=5, **DB) as c, c.cursor() as cur:
        cur.execute("SELECT EXTRACT(EPOCH FROM (NOW() - to_timestamp(MAX(unix_time)))) FROM transactions")
        age = cur.fetchone()[0]
        if age is None:               # warmup: no rows yet → healthy
            sys.exit(0)
        if age > MAX_STALENESS_SEC:   # too old → unhealthy
            sys.exit(1)
    sys.exit(0)  # healthy
except Exception:
    sys.exit(1)  # DB down/unreachable → unhealthy
