{
    'name': "Kenya M-Pesa Payment Acquirer",
    'version': '18.0.2.0.0',
    'category': 'Accounting/Payment Acquirers',
    'summary': 'M-Pesa STK Push, C2B, B2C, Webhooks — Full Daraja 2.0 for Odoo 18',
    'author': "Paul Nyoike - Nairobi",
    'website': "https://github.com/NyoikePaul/OdooERP",
    'depends': ['payment', 'mpesa_connector', 'mpesa_integration'],
    'data': [
        'security/ir.model.access.csv',
        'views/payment_provider_views.xml',
        'data/payment_method.xml',
        'data/payment_provider.xml',
        'wizard/mpesa_stk_wizard.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
