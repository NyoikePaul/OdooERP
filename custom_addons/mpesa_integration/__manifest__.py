{
    'name': 'M-Pesa Integration',
    'version': '18.0.2.0.0',
    'category': 'Accounting/Payment',
    'summary': 'M-Pesa transaction log, reconciliation wizard, status queries, C2B/B2C support',
    'author': 'Paul Nyoike - Nairobi',
    'website': 'https://github.com/NyoikePaul/OdooERP',
    'depends': ['base', 'account', 'mail', 'mpesa_connector'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/mpesa_reconcile_wizard.xml',
        'views/views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
