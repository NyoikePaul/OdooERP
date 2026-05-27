{
    'name': 'Real Estate Management',
    'version': '1.0',
    'summary': 'Manage properties, tenants, and lease contracts.',
    'category': 'Real Estate',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/property_views.xml',
    ],
    'installable': True,
    'application': True,
}
