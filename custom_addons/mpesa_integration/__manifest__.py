{
    'name':        'M-Pesa Integration',
    'version':     '18.0.2.0.0',
    'category':    'Accounting/Payment',
    'summary':     'M-Pesa transaction log, auto-reconciliation, STK Push, B2C, reversal',
    'author':      'Paul Nyoike',
    'website':     'https://github.com/NyoikePaul/OdooERP',
    'license':     'LGPL-3',
    'depends':     ['base', 'account', 'mail', 'mpesa_connector'],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
    ],
    'installable':  True,
    'application':  False,
    'auto_install': False,
}
