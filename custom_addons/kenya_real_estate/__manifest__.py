{
    'name':         'Kenya Real Estate CRM',
    'version':      '18.0.4.0.0',
    'category':     'Real Estate',
    'summary':      'Enterprise Real Estate for Kenya — Buildings, Leases, M-Pesa Rent, KRA WHT, Insurance, PDF Reports',
    'description':  """
Kenya Real Estate CRM — Enterprise-grade property management for East Africa.

Key Features:
- Building + unit hierarchy (blocks, floors, apartments)
- Full lease lifecycle: draft → active → renew → expire → surrender
- KRA Withholding Tax: 5% residential / 10% commercial (KITA Section 35)
- Auto monthly rent invoicing + late payment penalties (grace period)
- Annual rent escalation engine with history log
- Security deposit ledger: received → deductions → refund
- Property insurance tracking + 30-day renewal alerts
- Property valuation history (comparable, income, DCF)
- Lease templates for quick tenant onboarding
- Agent commission tracking + invoicing
- Move-in/out inspection checklists with photos
- Utility meter readings (water, electricity) + billing
- Property offers & enquiry pipeline
- Tenant broadcast messaging (all/building/county/arrears)
- PDF Rent Roll report
- PDF Arrears Aging report
- PDF Tenancy Agreement (Kenya Landlord & Tenant Act)
- 7 automated crons (invoicing, expiry, reminders, penalties, escalation)
- M-Pesa Daraja 2.0 rent collection
- Net Operating Income, Cap Rate, Gross Yield KPIs
- Vacancy tracking with revenue loss calculation
    """,
    'author':       'Paul Nyoike',
    'maintainer':   'Paul Nyoike',
    'website':      'https://github.com/NyoikePaul/OdooERP',
    'license':      'LGPL-3',
    'depends':      ['base', 'account', 'mail', 'mpesa_connector'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'data/cron.xml',
        'views/config_views.xml',
        'views/property_views.xml',
        'views/lease_views.xml',
        'views/maintenance_views.xml',
        'views/premium_views.xml',
        'views/insurance_valuation_views.xml',
        'wizard/rent_payment_wizard.xml',
        'wizard/lease_renewal_wizard.xml',
        'wizard/tenant_broadcast_wizard.xml',
        'report/lease_report.xml',
        'report/rent_roll_report.xml',
        'views/menu_views.xml',
    ],
    'demo':         ['demo/demo.xml'],
    'images':       ['static/description/icon.svg'],
    'installable':  True,
    'application':  True,
    'auto_install': False,
}
