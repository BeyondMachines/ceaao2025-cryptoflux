import os, sys, psycopg2

PRIMARY = dict(
  host=os.getenv('PRIMARY_DB_HOST','postgres'),
  port=int(os.getenv('PRIMARY_DB_PORT','5432')),
  dbname=os.getenv('PRIMARY_DB_NAME','cryptoflux'),
  user=os.getenv('PRIMARY_DB_USER','cryptouser'),
  password=os.getenv('PRIMARY_DB_PASS','crypto'),
)

DR = dict(
  host=os.getenv('DR_DB_HOST','postgres-dr'),
  port=int(os.getenv('DR_DB_PORT','5432')),
  dbname=os.getenv('DR_DB_NAME','cryptoflux'),
  user=os.getenv('DR_DB_USER','cryptouser'),
  password=os.getenv('DR_DB_PASS','crypto'),
)

# fail if DR lags too much behind primary
MAX_LAG_ROWS = int(os.getenv('DR_MAX_LAG_ROWS','500'))

try:
    with psycopg2.connect(connect_timeout=5, **PRIMARY) as cp, cp.cursor() as p, \
         psycopg2.connect(connect_timeout=5, **DR) as cd, cd.cursor() as d:
        p.execute("SELECT COALESCE(MAX(id),0) FROM transactions")
        src_max = p.fetchone()[0]
        d.execute("SELECT COALESCE(MAX(id),0) FROM transactions")
        dst_max = d.fetchone()[0]
        lag = max(0, src_max - dst_max)
        sys.exit(0 if lag <= MAX_LAG_ROWS else 1)
except Exception:
    sys.exit(1)
