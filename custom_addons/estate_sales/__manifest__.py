{
    'name':        'Estate Sales',
    'version':     '18.0.1.0.0',
    'category':    'Real Estate',
    'summary':     'Property sales pipeline — Lead, Viewing, Offer, Reservation, Transfer',
    'author':      'Paul Nyoike',
    'website':     'https://github.com/NyoikePaul/OdooERP',
    'license':     'LGPL-3',
    'depends':     ['estate_core'],
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
