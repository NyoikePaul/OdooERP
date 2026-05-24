from odoo import models, fields, api, _
from odoo.exceptions import UserError


class EstateDeposit(models.Model):
    _name        = 'estate.deposit'
    _description = 'Security Deposit Ledger'
    _inherit     = ['mail.thread']
    _order       = 'create_date desc'

    name         = fields.Char("Deposit Ref", readonly=True, default='New')
    lease_id     = fields.Many2one('estate.lease', string="Lease",
                                   required=True, ondelete='restrict', tracking=True)
    property_id  = fields.Many2one(related='lease_id.property_id', store=True)
    tenant_id    = fields.Many2one(related='lease_id.tenant_id', store=True)
    currency_id  = fields.Many2one('res.currency', default=lambda s: s.env.ref('base.KES'))

    deposit_amount   = fields.Monetary("Deposit Held (KES)", currency_field='currency_id', tracking=True)
    received_date    = fields.Date("Date Received", default=fields.Date.today)
    received_via     = fields.Selection([
        ('mpesa',  'M-Pesa'),
        ('bank',   'Bank Transfer'),
        ('cash',   'Cash'),
        ('cheque', 'Cheque'),
    ], default='mpesa')
    mpesa_receipt    = fields.Char("M-Pesa Receipt No.")

    deduction_ids    = fields.One2many('estate.deposit.deduction', 'deposit_id',
                                       string="Deductions")
    total_deductions = fields.Monetary("Total Deductions", currency_field='currency_id',
                                       compute='_compute_totals', store=True)
    refund_amount    = fields.Monetary("Refundable Amount", currency_field='currency_id',
                                       compute='_compute_totals', store=True)

    status = fields.Selection([
        ('held',     'Held'),
        ('refunded', 'Refunded'),
        ('forfeited','Forfeited'),
    ], default='held', tracking=True)

    refund_date  = fields.Date("Refund Date")
    refund_ref   = fields.Char("Refund M-Pesa/Bank Ref")
    notes        = fields.Text("Notes")

    @api.depends('deposit_amount', 'deduction_ids.amount')
    def _compute_totals(self):
        for rec in self:
            deductions = sum(rec.deduction_ids.mapped('amount'))
            rec.total_deductions = deductions
            rec.refund_amount    = max(rec.deposit_amount - deductions, 0)

    def action_refund(self):
        self.write({'status': 'refunded', 'refund_date': fields.Date.today()})
        self.message_post(body=_(f"Deposit refunded: KES {self.refund_amount:,.0f}"))

    def action_forfeit(self):
        self.write({'status': 'forfeited'})
        self.message_post(body=_("Deposit forfeited."))

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name', 'New') == 'New':
                v['name'] = self.env['ir.sequence'].next_by_code('estate.deposit') or 'New'
        return super().create(vals_list)


class EstateDepositDeduction(models.Model):
    _name        = 'estate.deposit.deduction'
    _description = 'Deposit Deduction Item'

    deposit_id   = fields.Many2one('estate.deposit', ondelete='cascade', required=True)
    description  = fields.Char("Reason", required=True)
    amount       = fields.Monetary("Amount (KES)", currency_field='currency_id')
    currency_id  = fields.Many2one(related='deposit_id.currency_id')
    maintenance_id = fields.Many2one('estate.maintenance.request', string="Related Maintenance")
