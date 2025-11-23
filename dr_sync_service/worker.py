import os
import time
import logging
import psycopg2
from psycopg2.extras import execute_values

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database connections
PRIMARY = {
    'host': os.getenv('PRIMARY_DB_HOST'),
    'port': int(os.getenv('PRIMARY_DB_PORT', 5432)),
    'database': os.getenv('PRIMARY_DB_NAME'),
    'user': os.getenv('PRIMARY_DB_USER'),
    'password': os.getenv('PRIMARY_DB_PASS')
}

DR = {
    'host': os.getenv('DR_DB_HOST'),
    'port': int(os.getenv('DR_DB_PORT', 5432)),
    'database': os.getenv('DR_DB_NAME'),
    'user': os.getenv('DR_DB_USER'),
    'password': os.getenv('DR_DB_PASS')
}

SYNC_INTERVAL = int(os.getenv('SYNC_INTERVAL_SECONDS', 300))
TABLE_NAME = 'transactions'
ID_COLUMN = 'id'


def get_max_id(conn):
    """Get the max ID from DR database"""
    with conn.cursor() as cur:
        cur.execute(f"SELECT MAX({ID_COLUMN}) FROM {TABLE_NAME}")
        result = cur.fetchone()[0]
        return result if result is not None else 0


def sync_new_transactions():
    """Sync only new transactions (where id > max_id_in_dr)"""
    primary_conn = None
    dr_conn = None
    
    try:
        primary_conn = psycopg2.connect(**PRIMARY)
        dr_conn = psycopg2.connect(**DR)
        
        # Get last synced ID from DR
        max_id = get_max_id(dr_conn)
        logger.info(f"Last synced ID in DR: {max_id}")
        
        # Get new rows from primary
        with primary_conn.cursor() as cur:
            cur.execute(
                f"SELECT * FROM {TABLE_NAME} WHERE {ID_COLUMN} > %s ORDER BY {ID_COLUMN}",
                (max_id,)
            )
            rows = cur.fetchall()
            
            if not rows:
                logger.info("No new transactions to sync")
                return
            
            # Get column names
            columns = [desc[0] for desc in cur.description]
        
        # Insert into DR
        with dr_conn.cursor() as cur:
            cols = ', '.join(columns)
            query = f"INSERT INTO {TABLE_NAME} ({cols}) VALUES %s"
            execute_values(cur, query, rows)
            dr_conn.commit()
        
        logger.info(f"Synced {len(rows)} new transactions (IDs {rows[0][0]} to {rows[-1][0]})")
        
    except Exception as e:
        logger.error(f"Sync error: {e}")
        if dr_conn:
            dr_conn.rollback()
    finally:
        if primary_conn:
            primary_conn.close()
        if dr_conn:
            dr_conn.close()


def main():
    logger.info("DR Sync Worker started")
    logger.info(f"Syncing table: {TABLE_NAME}")
    logger.info(f"Sync interval: {SYNC_INTERVAL} seconds")
    
    while True:
        try:
            sync_new_transactions()
            time.sleep(SYNC_INTERVAL)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            time.sleep(60)


if __name__ == "__main__":
    main()