{
    'name':        'Estate Installment Engine',
    'version':     '18.0.1.0.0',
    'summary':     'Off-plan property installment plans — deposit, milestones, handover',
    'description': """
        Kenya off-plan property installment engine.
        Supports flexible milestone-based payment schedules:
        - Booking deposit
        - Construction milestones (foundation, slab, roofing, etc.)
        - Handover balance
        Auto-generates invoices per milestone with M-Pesa STK push.
        Tracks collection rate, overdue amounts, and completion percentage.
    """,
    'author':      'Paul Nyoike',
    'website':     'https://github.com/NyoikePaul/OdooERP',
    'category':    'Real Estate',
    'license':     'LGPL-3',
    'depends':     ['estate_core', 'estate_sales', 'account', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'views/installment_plan_views.xml',
        'views/installment_line_views.xml',
        'wizard/generate_installment_wizard.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
