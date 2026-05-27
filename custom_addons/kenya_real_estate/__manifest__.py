{
    'name':        'Kenya Real Estate CRM',
    'version':     '18.0.4.0.0',
    'category':    'Real Estate',
    'summary':     'Enterprise property management — Buildings, Leases, Rent Roll, Insurance, Valuations, M-Pesa, KRA WHT',
    'description': '''
Kenya Real Estate CRM — The most complete Odoo real estate module for East Africa.

Features:
- Building & unit hierarchy management
- Full lease lifecycle (activate → escalate → renew → expire → surrender)
- KRA WHT auto-computation (5% residential / 10% commercial)
- Auto monthly rent invoicing + late payment penalties
- Security deposit ledger with deductions
- Agent commission tracking
- Move-in/out inspection checklists
- Utility meter readings & billing
- Property offers & enquiry pipeline
- Insurance policy tracking with renewal alerts
- Property valuation history
- Lease templates for quick onboarding
- Tenant broadcast messaging
- PDF Rent Roll & Arrears reports
- 7 automated crons for full automation
- M-Pesa Daraja 2.0 rent collection
    ''',
    'author':       'Paul Nyoike',
    'maintainer':   'Paul Nyoike',
    'website':      'https://github.com/NyoikePaul/OdooERP',
    'license':      'LGPL-3',
    'depends': ['base', 'account', 'mail', 'mpesa_connector'],
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
    'demo': ['demo/demo.xml'],
    'images':        ['static/description/icon.svg'],
    'installable':   True,
    'application':   True,
    'auto_install':  False,
}
