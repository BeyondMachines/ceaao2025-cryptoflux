import os

DB_HOST=os.getenv("DB_HOST","postgres")
DB_PORT=int(os.getenv("DB_PORT","5432"))
DB_NAME=os.getenv("DB_NAME","cryptoflux")
DB_USER=os.getenv("DB_USER","cryptouser")
DB_PASS=os.getenv("DB_PASS","crypto")

API_KEY=os.getenv("TRADING_DATA_API_KEY")
