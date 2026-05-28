#!/usr/bin/env bash
# Restore Odoo database from backup
set -euo pipefail
BACKUP="${1:?Usage: bash scripts/restore.sh <backup.sql.gz> [db_name]}"
DB="${2:-odoo_kenya}"

echo "Restoring $BACKUP to $DB..."
docker compose exec db psql -U odoo -c "DROP DATABASE IF EXISTS $DB"
docker compose exec db psql -U odoo -c "CREATE DATABASE $DB OWNER odoo"
gunzip -c "$BACKUP" | docker compose exec -T db psql -U odoo "$DB"
echo "Restore complete."
