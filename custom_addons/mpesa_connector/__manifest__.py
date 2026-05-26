{
    'name':        'M-Pesa Connector Core',
    'version':     '18.0.2.0.0',
    'category':    'Accounting/Payment',
    'summary':     'Reusable Daraja 2.0 API kernel — token cache, STK push, C2B, B2C, reversal, status query',
    'description': 'Abstract mixin model providing all Safaricom Daraja 2.0 API methods. Inherit mpesa.api.mixin in any module to add M-Pesa capabilities.',
    'author':      'Paul Nyoike',
    'maintainer':  'Paul Nyoike',
    'website':     'https://github.com/NyoikePaul/OdooERP',
    'license':     'LGPL-3',
    'depends':     ['account', 'payment'],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
    ],
    'installable':  True,
    'application':  False,
    'auto_install': False,
}
