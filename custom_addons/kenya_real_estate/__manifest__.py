{
    'name':        'Kenya Real Estate CRM',
    'version':     '18.0.5.0.0',
    'category':    'Real Estate',
    'summary':     'Enterprise Real Estate for East Africa — KRA MRI, Generator Billing, Service Charges, Demand Notices, Tenant Screening',
    'description': """
Kenya Real Estate CRM v5 — The most complete Odoo real estate module for East Africa.

Built specifically for Kenya/East Africa pain points:
- KRA Monthly Rental Income (MRI) tax return preparation (April 2025 compliance)
- Generator fuel tracking and tenant billing (critical for all Kenya buildings)
- Service charge apportionment (equal/sqft/bedrooms)
- Formal demand notice workflow (Landlord & Tenant Act Cap 301)
- Tenant screening with income verification and scoring
- Caretaker/facility manager management (NHIF/NSSF/KRA compliance)
- Business Premises Rent Tribunal (BPRT) escalation workflow
- M-Pesa Daraja 2.0 rent collection
- KRA Withholding Tax 5%/10% auto-computed
- Full lease lifecycle with escalation, deposit, inspection
    """,
    'author':      'Paul Nyoike',
    'maintainer':  'Paul Nyoike',
    'website':     'https://github.com/NyoikePaul/OdooERP',
    'license':     'LGPL-3',
    'depends':     ['base', 'account', 'mail', 'mpesa_connector'],
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
        'views/kenya_specific_views.xml',
        'wizard/rent_payment_wizard.xml',
        'wizard/lease_renewal_wizard.xml',
        'wizard/tenant_broadcast_wizard.xml',
        'report/lease_report.xml',
        'report/rent_roll_report.xml',
        'views/menu_views.xml',
    ],
    'demo':        ['demo/demo.xml'],
    'images':      ['static/description/icon.svg'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
