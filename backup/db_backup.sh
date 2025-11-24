#!/bin/bash
# =============================================================================
#  CryptoFlux – PostgreSQL Backup & Restore Script (Linux + macOS)
# =============================================================================

ACTION=$1
BACKUP_FILE=$2

CONTAINER="cryptoflux-postgres"
BACKUP_DIR="backups"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

# =====================================================================
# BACKUP MODE
# =====================================================================
if [[ "$ACTION" == "backup" ]]; then
    echo "Creating PostgreSQL backup from container: $CONTAINER"

    FILE_NAME="cryptoflux_backup_${TIMESTAMP}.sql"
    FILE_PATH="${BACKUP_DIR}/${FILE_NAME}"

    docker exec "$CONTAINER" pg_dump -U cryptouser -d cryptoflux > "$FILE_PATH"

    if [[ -s "$FILE_PATH" ]]; then
        echo "[SUCCESS] Backup saved to $FILE_PATH"
    else
        echo "[ERROR] Backup failed!"
        rm -f "$FILE_PATH"
    fi

    exit 0
fi

# =====================================================================
# RESTORE MODE
# =====================================================================
if [[ "$ACTION" == "restore" ]]; then
    
    if [[ -z "$BACKUP_FILE" ]]; then
        echo "Usage: ./db_backup.sh restore <file.sql>"
        exit 1
    fi

    if [[ ! -f "$BACKUP_FILE" ]]; then
        echo "Backup file not found: $BACKUP_FILE"
        exit 1
    fi

    echo "Restoring database from $BACKUP_FILE..."

    cat "$BACKUP_FILE" | docker exec -i "$CONTAINER" psql -U cryptouser -d cryptoflux

    echo "[SUCCESS] Database restored successfully."
    exit 0
fi

# =====================================================================
# INVALID OPTION
# =====================================================================
echo "Invalid usage."
echo "Usage:"
echo "  ./db_backup.sh backup"
echo "  ./db_backup.sh restore <backup_file.sql>"
exit 1
