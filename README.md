<div align="center">

# OdooERP Kenya 🇰🇪

**Enterprise ERP built for the African market.**
M-Pesa · Real Estate CRM · KRA eTIMS · Odoo 18

[![Odoo](https://img.shields.io/badge/Odoo-18.0-4A4A4A?style=for-the-badge&logo=odoo)](https://odoo.com)
[![M-Pesa](https://img.shields.io/badge/M--Pesa-Daraja_2.0-00A651?style=for-the-badge)](https://developer.safaricom.co.ke)
[![KRA eTIMS](https://img.shields.io/badge/KRA-eTIMS-FF6600?style=for-the-badge)](https://etims.kra.go.ke)
[![License](https://img.shields.io/badge/License-LGPL--3-blue?style=for-the-badge)](LICENSE)
[![Kenya](https://img.shields.io/badge/Made_for-Kenya-006600?style=for-the-badge)](https://github.com/NyoikePaul/OdooERP)

[Live Demo](https://nyoikepaul.github.io/OdooERP/) · [Setup Guide](SETUP.md) · [Changelog](CHANGELOG.md)

</div>

---

## What's Inside

| Module | Description | Version |
|--------|-------------|---------|
| `mpesa_connector` | Daraja 2.0 API kernel — token cache, retry, all endpoints | 2.0.0 |
| `mpesa_integration` | Transaction audit log + reconciliation wizard | 2.0.0 |
| `kenya_mpesa_acquirer` | Odoo payment provider — STK Push, C2B, B2C | 2.0.0 |
| `kenya_real_estate` | Enterprise Real Estate CRM — 16 models, 7 crons | 4.0.0 |

---

## Real Estate CRM — Feature Matrix

| Feature | Status |
|---------|--------|
| Building + Unit hierarchy | ✅ |
| Full lease lifecycle (draft → renew → surrender) | ✅ |
| KRA WHT 5%/10% auto-computed | ✅ |
| Auto monthly rent invoicing | ✅ |
| Late payment penalties + grace period | ✅ |
| Rent escalation engine + auto-apply cron | ✅ |
| Security deposit ledger | ✅ |
| Property insurance tracking + alerts | ✅ |
| Property valuation history | ✅ |
| Lease templates | ✅ |
| Tenant broadcast messaging | ✅ |
| Agent commission tracking | ✅ |
| Move-in/out inspection checklists | ✅ |
| Utility billing (water/electricity) | ✅ |
| Property offers & enquiry pipeline | ✅ |
| PDF Rent Roll report | ✅ |
| PDF Arrears Aging report | ✅ |
| PDF Tenancy Agreement (Kenya law) | ✅ |
| NOI, Cap Rate, Gross Yield KPIs | ✅ |
| Vacancy tracking + revenue loss | ✅ |

---

## Quick Start

```bash
git clone https://github.com/NyoikePaul/OdooERP.git
cd OdooERP
cp .env.example .env
# Edit .env — add your M-Pesa Daraja credentials
docker compose up -d
```

Open **http://localhost:8069** → login `admin / admin`

---

## M-Pesa Setup

1. Create an app at [developer.safaricom.co.ke](https://developer.safaricom.co.ke)
2. Copy Consumer Key + Secret → add to `.env`
3. In Odoo: **Invoicing → Configuration → Payment Providers → M-Pesa Kenya**
4. Enter credentials → **Test Connection** ✅
5. Click **Register C2B URLs** to enable paybill

---

## Deploy to Production

```bash
# Production deployment with Nginx + SSL
cp .env.example .env
# Set DOMAIN, LETSENCRYPT_EMAIL in .env
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## Kenya Compliance

| Regulation | Implementation |
|-----------|----------------|
| KRA WHT (Section 35 KITA) | 5% residential / 10% commercial auto-computed |
| KRA eTIMS OSCU | Real-time invoice submission — no hardware needed |
| Kenya Landlord & Tenant Act (Cap 301) | PDF tenancy agreement template |
| Safaricom Daraja 2.0 | Full API — STK Push, C2B, B2C, reversal |

---

## Architecture

OdooERP Kenya
├── mpesa_connector        # Abstract Daraja 2.0 API mixin

├── mpesa_integration      # Transaction log + reconciliation

├── kenya_mpesa_acquirer   # Payment provider UI + webhooks

└── kenya_real_estate      # Real Estate CRM (16 models)

├── estate.building    # Buildings + units

├── estate.property    # Property portfolio

├── estate.lease       # Tenancy agreements

├── estate.offer       # Enquiry pipeline

├── estate.inspection  # Move-in/out checklists

├── estate.deposit     # Deposit ledger

├── estate.commission  # Agent commissions

├── estate.utility.*   # Meter readings + billing

├── estate.insurance   # Policy tracking

├── estate.*.valuation # Valuation history

└── estate.maintenance # Maintenance requests

---
##   Container 
<img width="1366" height="724" alt="image" src="https://github.com/user-attachments/assets/37b82ea1-0daa-41c0-a8b6-b3acaa4f1bca" />


## License

[LGPL-3.0](LICENSE) — matches Odoo Community Edition.
Free to use in commercial projects. Modifications to these modules must be open-sourced.

**© 2026 Paul Nyoike — Nairobi, Kenya 🇰🇪**
