#!/usr/bin/env bash
# Backup Odoo database and filestore
set -euo pipefail
DB="${1:-odoo_kenya}"
STAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./backups"
mkdir -p "$BACKUP_DIR"

echo "Backing up database $DB..."
docker compose exec db pg_dump -U odoo "$DB" | gzip > "$BACKUP_DIR/${DB}_${STAMP}.sql.gz"
echo "Backup saved: $BACKUP_DIR/${DB}_${STAMP}.sql.gz"
