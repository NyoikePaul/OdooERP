<div align="center">

<pre>
 ██████╗ ██████╗  ██████╗  ██████╗     ███████╗██████╗ ██████╗ 
██╔═══██╗██╔══██╗██╔═══██╗██╔═══██╗    ██╔════╝██╔══██╗██╔══██╗
██║   ██║██║  ██║██║   ██║██║   ██║    █████╗  ██████╔╝██████╔╝
██║   ██║██║  ██║██║   ██║██║   ██║    ██╔══╝  ██╔══██╗██╔═══╝ 
╚██████╔╝██████╔╝╚██████╔╝╚██████╔╝    ███████╗██║  ██║██║     
 ╚═════╝ ╚═════╝  ╚═════╝  ╚═════╝     ╚══════╝╚═╝  ╚═╝╚═╝     
                         K E N Y A
</pre>

**Enterprise Real Estate & Property Management ERP**
Built on Odoo 18 · Kenya-localised · M-Pesa · KRA eTIMS

[![CI](https://github.com/NyoikePaul/OdooERP/actions/workflows/ci.yml/badge.svg)](https://github.com/NyoikePaul/OdooERP/actions)
[![Odoo](https://img.shields.io/badge/Odoo-18.0-875A7B?logo=odoo)](https://www.odoo.com)
[![License](https://img.shields.io/badge/License-LGPL--3-blue)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python)](https://python.org)
[![M-Pesa](https://img.shields.io/badge/M--Pesa-Daraja%202.0-00B300)](https://developer.safaricom.co.ke)

[Features](#-features) · [Modules](#-modules) · [Quick Start](#-quick-start) · [Architecture](#-architecture) · [Screenshots](#-screenshots)

</div>

---

## 🖼 Screenshots

<div align="center">

<img width="1366" height="588" alt="image" src="https://github.com/user-attachments/assets/61ca1282-2df5-42ec-95c0-54ec3f14e8a8" />


| Property Dashboard | Lease Management | 
|:---:|:---:|:---:|
| <img width="1366" height="588" alt="image" src="https://github.com/user-attachments/assets/3e7155f0-fb9a-4f1b-bd82-5eca12007cee" />
| <img width="1366" height="588" alt="image" src="https://github.com/user-attachments/assets/38dde682-d83b-4349-a527-1e90e570bf2d" />
| <img width="1365" height="591" alt="image" src="https://github.com/user-attachments/assets/949d5c3b-e47d-434f-9e6e-cc9759b509dd" />
 |

</div>

---

## ✨ Features

| Category | Capability |
|---|---|
| 💳 **Payments** | M-Pesa STK Push, C2B, B2C, auto-reconciliation, callback handling |
| 🧾 **Tax Compliance** | KRA eTIMS OSCU real-time invoice submission, WHT, VAT 16% |
| 🏠 **Property** | Multi-building, unit management, occupancy tracking, county mapping |
| 📋 **Leasing** | Lease lifecycle, renewal wizard, demand notices (Cap 301), bulk rent |
| 📊 **Dashboard** | Live OWL KPI dashboard — occupancy, arrears aging, revenue, pipeline |
| 🔧 **Maintenance** | Work orders, priority escalation, avg resolution tracking |
| 🤝 **Sales** | Viewings, offers, acquisition pipeline, commission management |
| 👤 **Screening** | Tenant screening workflow, Kenya PIN validation |
| 📄 **Reports** | Rent roll, tenancy agreement, demand notice PDF reports |

---

## 📦 Modules

<pre>
custom_addons/
├── estate_core/           # Base models: property, unit, building, lease
├── estate_rental/         # Rental workflows, demand notices, caretaker payroll
├── estate_sales/          # Sales pipeline, viewings, offers, acquisitions
├── estate_finance/        # Revenue, commissions, owner statements
├── kenya_real_estate/     # Kenya extensions + live OWL KPI dashboard
├── kenya_mpesa_acquirer/  # Odoo payment acquirer — M-Pesa
├── mpesa_connector/       # Daraja 2.0: STK, C2B, B2C, reversal, status
├── mpesa_integration/     # M-Pesa ↔ account.move auto-reconciliation
└── kenya_kra_etims/       # KRA eTIMS OSCU real-time invoice submission
</pre>

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Git

### Run locally

<pre>
git clone https://github.com/NyoikePaul/OdooERP.git
cd OdooERP
cp .env.example .env          # fill in your credentials
docker compose up -d
</pre>

Open [http://localhost:8070](http://localhost:8070) · default login: `admin / admin`

### Install Kenya modules

In Odoo → Apps → search **Kenya** → install in this order:

<pre>
1. estate_core
2. estate_rental + estate_sales + estate_finance
3. kenya_real_estate
4. mpesa_connector → kenya_mpesa_acquirer
5. kenya_kra_etims
</pre>

---

## 🏗 Architecture

<pre>
┌─────────────────────────────────────────────┐
│            Odoo 18 Web Client               │
│          OWL Dashboard · PDF Reports        │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│           Custom Addons Layer               │
│   estate_core → rental / sales / finance    │
│   kenya_real_estate  (KPIs, compliance)     │
│   mpesa_connector    · kenya_kra_etims      │
└──────────┬──────────────────┬───────────────┘
           │                  │
┌──────────▼────────┐ ┌───────▼──────────────┐
│  Safaricom        │ │  KRA eTIMS OSCU      │
│  Daraja 2.0       │ │  Invoice Submission  │
│  M-Pesa API       │ │  Real-time           │
└───────────────────┘ └──────────────────────┘
</pre>

---

## 💳 M-Pesa Integration

<pre>
- STK Push    — prompt tenant phone directly from lease or invoice
- C2B         — receive paybill/till payments, auto-match to invoice
- B2C         — send refunds or deposits to tenant phone
- Reversal    — full transaction lifecycle management
- Token cache — 55-min OAuth token cache, auto-refresh
- Retry       — 3-attempt retry with exponential backoff
- Normaliser  — handles 07xx / 2547xx / +2547xx formats
</pre>

---

## 🧾 KRA eTIMS Compliance

Real-time invoice submission to KRA eTIMS OSCU on every posted invoice.

<pre>
- VAT 16%           standard rated supplies
- Withholding Tax   WHT deduction tracking
- Zero-rated        and exempt supplies
- KRA PIN           validation on all partners
</pre>

---

## ⚙️ Environment Variables

Copy `.env.example` → `.env`:

<pre>
POSTGRES_USER=odoo
POSTGRES_PASSWORD=your_secure_password

MPESA_CONSUMER_KEY=your_daraja_consumer_key
MPESA_CONSUMER_SECRET=your_daraja_consumer_secret
MPESA_SHORTCODE=your_paybill_or_till
MPESA_PASSKEY=your_lipa_na_mpesa_passkey
MPESA_ENV=sandbox                          # or production

KRA_ETIMS_URL=https://etims-api.kra.go.ke
KRA_ETIMS_PIN=your_kra_pin
</pre>

---

## 🤝 Contributing

PRs welcome — please target the `dev` branch. See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## 📜 License

[LGPL-3.0](LICENSE) · free to use, modify, and distribute with attribution.

---

<div align="center">
<pre>
Built with ❤️  for Kenya
github.com/NyoikePaul · odoo-erp.vercel.app
</pre>
</div>
