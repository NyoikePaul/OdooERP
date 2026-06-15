"""
Installment Payment Log
========================
Tracks every payment received against a plan.
Auto-created when an installment invoice is paid.
"""
from odoo import models, fields, api, _


class EstateInstallmentPayment(models.Model):
    _name        = 'estate.installment.payment'
    _description = 'Installment Payment Log'
    _order       = 'payment_date desc'

    plan_id      = fields.Many2one('estate.installment.plan', required=True, ondelete='cascade')
    line_id      = fields.Many2one('estate.installment.line', string='Milestone')
    partner_id   = fields.Many2one(related='plan_id.partner_id', store=True)
    property_id  = fields.Many2one(related='plan_id.property_id', store=True)
    currency_id  = fields.Many2one(related='plan_id.currency_id')

    payment_date  = fields.Date('Payment Date', default=fields.Date.today, required=True)
    amount        = fields.Monetary('Amount (KES)', currency_field='currency_id', required=True)
    payment_method= fields.Selection([
        ('mpesa',  'M-Pesa'),
        ('bank',   'Bank Transfer'),
        ('cash',   'Cash'),
        ('cheque', 'Cheque'),
    ], default='mpesa', required=True)
    mpesa_ref     = fields.Char('M-Pesa Receipt No.')
    bank_ref      = fields.Char('Bank Reference')
    invoice_id    = fields.Many2one('account.move', string='Invoice')
    notes         = fields.Text('Notes')

    @api.onchange('payment_method')
    def _onchange_method(self):
        if self.payment_method != 'mpesa':
            self.mpesa_ref = False
        if self.payment_method not in ('bank', 'cheque'):
            self.bank_ref = False
