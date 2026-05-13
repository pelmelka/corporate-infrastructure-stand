#!/usr/bin/env bash
set -euo pipefail
umask 027

BACKUP_DIR="/var/backups/postgresql/supportdesk"
DB_NAME="supportdesk"
TIMESTAMP="$(date -u +%Y%m%d-%H%M%S)"

BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.dump"
CHECKSUM_FILE="${BACKUP_FILE}.sha256"
LATEST_LINK="${BACKUP_DIR}/latest.dump"

cd /
mkdir -p "$BACKUP_DIR"

pg_dump -Fc "$DB_NAME" -f "$BACKUP_FILE"

test -s "$BACKUP_FILE"

sha256sum "$BACKUP_FILE" > "$CHECKSUM_FILE"

ln -sfn "$BACKUP_FILE" "$LATEST_LINK"

find "$BACKUP_DIR" -type f -name "${DB_NAME}_*.dump" -mtime +7 -delete
find "$BACKUP_DIR" -type f -name "${DB_NAME}_*.dump.sha256" -mtime +7 -delete

echo "Backup created: $BACKUP_FILE"
echo "Checksum created: $CHECKSUM_FILE"
echo "Latest link: $LATEST_LINK"
