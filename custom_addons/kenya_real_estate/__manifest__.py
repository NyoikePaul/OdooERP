{
    'name': 'Kenya Real Estate CRM',
    'version': '18.0.1.0.0',
    'category': 'Real Estate',
    'summary': 'Property listings, tenant leases, M-Pesa rent collection for Kenya',
    'author': 'Paul Nyoike - Nairobi',
    'website': 'https://github.com/NyoikePaul/OdooERP',
    'depends': ['base', 'account', 'mail', 'mpesa_connector'],
    'data': [
        'security/ir.model.access.csv',
        'views/property_views.xml',
        'views/lease_views.xml',
        'data/sequences.xml',
        'report/lease_report.xml',
        'wizard/rent_payment_wizard.xml',
        'views/menu_views.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
