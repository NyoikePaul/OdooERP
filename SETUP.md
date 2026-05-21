# Full Setup Guide — OdooERP Kenya

## Prerequisites
| Tool | Version | Install |
|---|---|---|
| Docker | 24+ | [docs.docker.com](https://docs.docker.com/get-docker/) |
| Docker Compose | v2 | Included with Docker Desktop |
| Git | Any | `apt install git` |

---

## 1. Clone & Configure

```bash
git clone https://github.com/NyoikePaul/OdooERP.git
cd OdooERP
cp .env.example .env
nano .env   # Fill in your credentials
```

---

## 2. Development Setup (Local)

```bash
make up       # Start Odoo + PostgreSQL
make logs     # Watch logs
```

Open: **http://localhost:8069**
- Create database
- Install modules: `kenya_mpesa_acquirer`, `kenya_real_estate`

---

## 3. M-Pesa Configuration

### Get Daraja credentials
1. Register at [developer.safaricom.co.ke](https://developer.safaricom.co.ke)
2. Create an app → copy Consumer Key + Secret
3. Get your Passkey from Safaricom Business portal

### Configure in OdooFill in all fields. Enable **Sandbox** for testing.

### Test STK Push (sandbox)
Use Safaricom test phone: `254708374149`
Test amount: any value

---

## 4. Production Deployment

```bash
# 1. Set your domain in .env
MPESA_CALLBACK_URL=https://yourdomain.com/payment/mpesa/callback

# 2. Update nginx/odoo.conf — replace YOUR_DOMAIN
sed -i 's/YOUR_DOMAIN/yourdomain.com/g' nginx/odoo.conf

# 3. Get SSL certificate
docker run --rm -v /etc/letsencrypt:/etc/letsencrypt \
  certbot/certbot certonly --standalone -d yourdomain.com

# 4. Launch production stack
make prod-up

# 5. Verify
curl https://yourdomain.com/web/health
```

---

## 5. KRA eTIMS Setup

1. Register at [eTIMS Developer Portal](https://etims.kra.go.ke)
2. Add your KRA PIN and device serial to `.env`
3. Install the eTIMS module from Odoo KE LTD

---

## 6. Backup & Restore

```bash
# Backup
make backup    # Creates backup_YYYYMMDD_HHMMSS.sql

# Restore
docker compose exec -T db psql -U odoo odoo < backup_file.sql
```

---

## Troubleshooting

| Issue | Fix |
|---|---|
| M-Pesa callback not received | Check callback URL is HTTPS and publicly accessible |
| STK Push times out | Check Daraja credentials; verify phone format `2547XXXXXXXX` |
| Module install fails | Run `docker compose logs web` and check for missing dependencies |
| Database connection error | Ensure `.env` DB credentials match docker-compose.yml |
