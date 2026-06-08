{
    'name':        'Estate Finance',
    'version':     '18.0.1.0.0',
    'category':    'Real Estate',
    'summary':     'Financial reporting — KRA MRI Returns, Owner Statements, Payment Aging, Insurance',
    'author':      'Paul Nyoike',
    'website':     'https://github.com/NyoikePaul/OdooERP',
    'license':     'LGPL-3',
    'depends':     ['estate_rental', 'estate_sales'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'views/views.xml',
        'views/menu_views.xml',
    ],
    'installable':  True,
    'application':  False,
    'auto_install': False,
}
