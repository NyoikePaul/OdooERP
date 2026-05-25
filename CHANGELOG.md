# Changelog

## [Unreleased]
### Added
- M-Pesa Daraja STK Push integration
- KRA eTIMS OSCU real-time invoice submission
- Real Estate CRM module
- Production Docker + Nginx + SSL setup
- Kenya tax localization (VAT 16%, WHT)

## [1.0.0] - 2026-05-21
### Added
- kenya_real_estate — Properties, leases, rent invoicing
- mpesa_integration — Full transaction log with M-Pesa receipt storage
- GitHub Actions CI pipeline
- Production Nginx + SSL Docker setup
- MIT License
### Fixed
- mpesa_connector models not loading
- Deprecated attrs= syntax updated to Odoo 18
- Wrong website URLs in manifests
- Missing payment_method.xml

## [2.0.0] - 2026-05-24
### Added
- Premium Real Estate v3: Buildings/Units hierarchy
- Property Offers & Enquiries pipeline
- Move-in/Move-out Inspection Reports with checklists
- Security Deposit Ledger (full lifecycle)
- Agent Commission Tracking
- Utility Billing (water, electricity readings)
- KRA Withholding Tax auto-computation (5% residential / 10% commercial)
- Rent Escalation Engine with auto-apply cron
- NOI, Cap Rate, Gross Yield computed KPIs
- Vacancy tracking with revenue loss calculation
- Auto monthly invoice generation (1st of month cron)
- Late payment penalties with grace period
- Lease surrender/break clause workflows
- 6 scheduled crons for full automation
- Comprehensive demo data (buildings, units, deposits, offers, inspections)
### Fixed
- Removed duplicate fields and methods in property/lease models
- Clean model architecture with no code duplication
