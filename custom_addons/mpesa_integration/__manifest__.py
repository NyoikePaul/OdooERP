{
    'name':        'M-Pesa Integration',
    'version':     '18.0.3.0.0',
    'category':    'Accounting/Payment',
    'summary':     'M-Pesa Daraja 2.0 — STK Push from invoices, auto-reconcile, C2B, B2C, reversal',
    'description': """
Kenya M-Pesa Integration — Enterprise rent collection.

Features:
- One-click STK Push from any invoice
- Auto-reconciliation of incoming payments
- C2B Paybill/Till transaction log
- B2C business payments
- Transaction reversal
- Scheduled auto-reconcile cron
- Smart buttons on invoices showing M-Pesa payment count
- Payment receipt on reconciled transactions
    """,
    'author':      'Paul Nyoike',
    'website':     'https://github.com/NyoikePaul/OdooERP',
    'license':     'LGPL-3',
    'depends':     ['base', 'account', 'mail', 'mpesa_connector'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/bulk_stk_wizard.xml',
        'views/views.xml',
        'views/invoice_mpesa_views.xml',
    ],
    'installable':  True,
    'application':  True,
    'auto_install': False,
}
