{
    'name':        'Kenya Real Estate CRM',
    'version':     '18.0.6.0.0',
    'category':    'Real Estate',
    'summary':     'Enterprise Real Estate for East Africa v6 — Sales, Viewings, Work Orders, Acquisition, Owner Statements, Aging, KRA, M-Pesa',
    'description': """
Kenya Real Estate CRM v6 — The most complete Odoo real estate module for East Africa.

NEW in v6:
- Property Sales workflow (Lead → Viewing → Reservation → Agreement → Transfer → Sold)
- Viewing Scheduler with double-booking prevention
- Work Orders for maintenance contractors (materials, labor, vendor bills)
- Property Acquisition workflow (Due Diligence → Purchase → Registration)
- Owner/Landlord Monthly Statements (auto-populated from invoices)
- Payment Aging Analysis (0-30, 31-60, 61-90, 90+ days)
- User Roles (Technician, Agent, Property Manager, Administrator)

EXISTING:
- Buildings + Units hierarchy
- Full lease lifecycle with KRA WHT
- M-Pesa STK Push from invoice + lease
- Bulk rent collection wizard
- KRA MRI tax returns (April 2025)
- Generator billing
- Service charge apportionment
- Demand Notices (Cap 301)
- Tenant Screening with scoring
- Caretaker NHIF/NSSF management
- PDF Rent Roll, Arrears, Tenancy Agreement, Demand Notice
- 9 automated crons
    """,
    'author':      'Paul Nyoike',
    'website':     'https://github.com/NyoikePaul/OdooERP',
    'license':     'LGPL-3',
    'depends':     ['base', 'account', 'mail', 'mpesa_connector'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'data/cron.xml',
        'wizard/rent_invoice_wizard.xml',
        'wizard/lease_renewal_wizard.xml',
        'wizard/broadcast_wizard.xml',
        'views/property_type_views.xml',
        'views/property_views.xml',
        'views/building_views.xml',
        'views/lease_views.xml',
        'views/maintenance_views.xml',
        'views/operations_views.xml',
        'views/kenya_views.xml',
        'views/insurance_valuation_views.xml',
        'views/res_partner_kenya_views.xml',
        'views/dashboard_views.xml',
        'views/sales_acquisition_views.xml',
        'report/demand_notice_report.xml',
        'report/tenancy_agreement.xml',
        'report/rent_roll.xml',
        'views/menu_views.xml',
    ],
    'demo':        ['demo/demo.xml'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'images':      ['static/description/icon.svg'],
}
