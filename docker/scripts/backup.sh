#!/bin/bash
# Simple Odoo DB Backup
docker exec odoo_db pg_dump -U odoo -d postgres | gzip > ./backup/db_dump_$(date +%F).sql.gz
echo "Backup created in ./backup/"
