

<div align="center">
 M-Pesa Daraja 2.0 • KRA eTIMS OSCU • Automated Accounting & Inventory • Production Docker


</div>

---

##  Who is this for?

| You are... | This gives you... |
| :--- | :--- |
| 🏢 **A Kenyan business** | Ready-to-deploy ERP with M-Pesa automated reconciliation and KRA eTIMS compliance out of the box. |
| 🏭 **A manufacturer / wholesaler** | Advanced inventory tracking, certified dispatch workflows, manufacturing orders, and cost accounting. |
| 💻 **An Odoo developer** | Reference implementation for Kenya localization, Daraja API webhooks, and secure module design. |
| 🎓 **A student / job seeker** | Production-grade portfolio showing real African fintech integrations and advanced backend architecture. |
| 🚀 **An African startup** | The fastest, most secure path to a compliant, scalable ERP system in East Africa. |

---

##  Features

###  M-Pesa Integration (Full Daraja 2.0)
- **STK Push** — customer pays directly from phone prompt
- **Auto-reconciliation** — payments matched to invoices automatically
- **Transaction log** — every Safaricom callback stored with receipt number
- **Sandbox/Live toggle** — test without real money
- Works with Sales, POS, eCommerce, and Real Estate rent

###  Real Estate CRM
- Property listings (residential, commercial, land, industrial)
- Tenant lease management with start/end dates
- One-click **PDF Tenancy Agreement** (Kenya Landlord & Tenant Act compliant)
- Bulk rent invoice generation wizard
- M-Pesa rent collection integrated

###  Kenya Localization
- KRA PIN validation
- VAT 16%, Withholding Tax schedules
- **KRA eTIMS OSCU** — real-time invoice submission (no hardware needed)
- Chart of accounts aligned to Kenya accounting standards
- Swahili (sw) translations included

###  Production-Ready DevOps
- Docker + Docker Compose v2 (dev and prod configs)
- Nginx reverse proxy + Let's Encrypt SSL
- One-command backup (`make backup`)
- GitHub Actions CI — lint, security scan (Bandit), manifest validation
- Dependabot for automated security updates

---

##  Quick Start

bash
git clone https://github.com/NyoikePaul/OdooERP.git
cd OdooERP
cp .env.example .env
# Edit .env with your M-Pesa Daraja credentials
make up

Open **http://localhost:8069** → create database → install `kenya_mpesa_acquirer` + `kenya_real_estate`

>  Full production setup: [SETUP.md](SETUP.md)

---

##  Custom Modules

| Module | Description | Depends on |
|---|---|---|
| `kenya_mpesa_acquirer` | Odoo payment provider — STK Push, callback, reconciliation | `mpesa_connector` |
| `mpesa_connector` | Daraja 2.0 API kernel — reusable mixin for any module | `payment` |
| `mpesa_integration` | M-Pesa transaction audit log | `account` |
| `kenya_real_estate` | Properties, leases, PDF reports, bulk rent wizard | `mpesa_connector` |

---


## Architecture

| M-Pesa Layer | Real Estate Layer | Kenya Layer |
|---|---|---|
| `kenya_mpesa_acquirer` | `kenya_real_estate` | KRA eTIMS OSCU |
| STK Push · Callback · Reconcile | Properties · Leases · Tenants | VAT 16% · WHT · PIN |
| `mpesa_connector` (Daraja 2.0) | PDF Agreements · Bulk Wizard | eTIMS Invoice Submission |
| Access Token · STK Push API | M-Pesa Rent Collection | |
| `mpesa_integration` | | |
| Transaction Audit Log | | |

> **Infrastructure:** PostgreSQL · Docker Compose v2 · Nginx · SSL · GitHub Actions CI


##  Screenshots

| Real Estate | 


 ** Agent Commissions
<img width="1366" height="645" alt="image" src="https://github.com/user-attachments/assets/fd374b30-7edc-482d-8da2-2f70fdf8e2c7" />



** Offers & Enquiries
<img width="1366" height="643" alt="image" src="https://github.com/user-attachments/assets/df74e856-dc71-4012-a478-06cf94afcf48" />






** Maintenance
<img width="1365" height="644" alt="image" src="https://github.com/user-attachments/assets/a3bef0d4-0de3-4350-807a-7227b8c1baeb" />


<img width="1363" height="644" alt="image" src="https://github.com/user-attachments/assets/0d8f335f-0714-4771-a43b-1eac431aa942" />


<img width="1366" height="646" alt="image" src="https://github.com/user-attachments/assets/01891f8c-438b-4003-bfc2-b696d9083de4" />


















| Accounting | Docker | Nginx |
|---|---|---|
| ![Accounting](https://github.com/user-attachments/assets/fb9badd0-8ea0-4627-b5e2-65120bff21dd) | ![Docker](https://github.com/user-attachments/assets/0a97df41-c0de-4b65-928e-a7a670341a11) | ![Nginx](https://github.com/user-attachments/assets/2cc89171-9971-4c58-9ef3-d32bef7704d8) |

---

##  Roadmap

- [x] M-Pesa STK Push + callback + reconciliation
- [x] Real Estate CRM (properties, leases, PDF agreements)
- [x] KRA eTIMS integration
- [x] Production Docker + Nginx + SSL
- [x] GitHub Actions CI + Bandit security scan
- [x] Unit tests + mock Daraja API tests
- [ ] M-Pesa C2B (paybill listener)
- [ ] M-Pesa B2C (salary/vendor payments)
- [ ] WhatsApp rent reminders via Africa's Talking
- [ ] Multi-currency (KES, USD, EUR)
- [ ] Uganda & Tanzania localization
- [ ] Odoo App Store listing

---

##  Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

bash
git checkout -b feat/your-feature
# make changes
git commit -m "feat: describe your change"
git push origin feat/your-feature
# open a Pull Request → main


---

##  Security

Found a vulnerability? See [SECURITY.md](SECURITY.md) — please **do not** open a public issue.

---

##  Commercial Support & Consulting

> Need a custom Odoo implementation for your Kenyan or African business?

**Paul Nyoike** — Python Backend Engineer | Odoo ERP Specialist | Nairobi, Kenya

-  [digifirst.com](https://digifirst.com)
-  [LinkedIn](https://linkedin.com/in/nyoikepaul)
-  [GitHub](https://github.com/NyoikePaul)
-  [paul@digifirst.com](mailto:paul@digifirst.com)

Services: Odoo deployment · M-Pesa integration · KRA eTIMS setup · Custom module development · Training

---

##  License

MIT © 2026 [NyoikePaul](https://github.com/NyoikePaul) — free to use, modify, and distribute.

---

<div align="center">

**If this saved you time, please ⭐ star the repo — it helps others find it!**

Made with 🇰🇪 in Nairobi

</div>

##  Live Landing Page

**[View Marketing Site →](index.html)**
