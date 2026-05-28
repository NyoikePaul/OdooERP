# Setup Guide — OdooERP Kenya

## Prerequisites
- Docker Desktop 4.x+
- Git

## 1. Clone & Configure

```bash
git clone https://github.com/NyoikePaul/OdooERP.git
cd OdooERP
cp .env.example .env
```

Edit `.env`:
```env
MPESA_CONSUMER_KEY=your_daraja_consumer_key
MPESA_CONSUMER_SECRET=your_daraja_consumer_secret
MPESA_SHORTCODE=174379
MPESA_PASSKEY=your_lipa_na_mpesa_passkey
MPESA_SANDBOX=true
```

## 2. Start

```bash
docker compose up -d
```

## 3. Install Modules

```bash
docker compose run --rm web odoo \
  -d odoo_kenya \
  -i mpesa_connector,mpesa_integration,kenya_mpesa_acquirer,kenya_real_estate \
  --stop-after-init --no-http
```

## 4. Set Admin Password

```bash
docker compose exec db psql -U odoo -d odoo_kenya -c \
  "UPDATE res_users SET password = 'your_password' WHERE login = 'admin';"
```

## 5. Access

Open **http://localhost:8069** → Database: `odoo_kenya` → `admin / your_password`

## Production

```bash
# Set DOMAIN and LETSENCRYPT_EMAIL in .env
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Backup / Restore

```bash
bash scripts/backup.sh odoo_kenya    # backup
bash scripts/restore.sh backup.sql.gz odoo_kenya  # restore
```
