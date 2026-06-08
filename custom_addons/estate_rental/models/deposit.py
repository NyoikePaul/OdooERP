from odoo import models, fields, api, _


class EstateDeposit(models.Model):
    _name        = 'estate.deposit'
    _description = 'Security Deposit Ledger'
    _inherit     = ['mail.thread']
    _order       = 'create_date desc'

    name          = fields.Char("Deposit Ref", readonly=True, copy=False, default='New')
    lease_id      = fields.Many2one('estate.lease', required=True, ondelete='restrict')
    property_id   = fields.Many2one(related='lease_id.property_id', store=True)
    tenant_id     = fields.Many2one(related='lease_id.tenant_id',   store=True)
    currency_id   = fields.Many2one('res.currency', default=lambda s: s.env.ref('base.KES'))
    amount        = fields.Monetary("Deposit Held (KES)", currency_field='currency_id', tracking=True)
    received_date = fields.Date("Date Received", default=fields.Date.today)
    method        = fields.Selection([('mpesa','M-Pesa'),('bank','Bank'),('cash','Cash'),('cheque','Cheque')], default='mpesa')
    receipt_ref   = fields.Char("M-Pesa / Bank Receipt")
    deduction_ids = fields.One2many('estate.deposit.deduction', 'deposit_id', string="Deductions")
    total_deductions = fields.Monetary("Total Deductions", currency_field='currency_id', compute='_compute_refund', store=True)
    refund_amount = fields.Monetary("Refundable Amount", currency_field='currency_id', compute='_compute_refund', store=True)
    status        = fields.Selection([('held','Held'),('refunded','Refunded'),('forfeited','Forfeited')], default='held', tracking=True)
    notes         = fields.Text()

    @api.depends('amount','deduction_ids.amount')
    def _compute_refund(self):
        for r in self:
            deductions = sum(r.deduction_ids.mapped('amount'))
            r.total_deductions = deductions
            r.refund_amount    = max(r.amount - deductions, 0)

    def action_refund(self):
        self.write({'status':'refunded'})
        self.message_post(body=_(f"Deposit refunded: KES {self.refund_amount:,.0f}"))

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name','New')=='New':
                v['name'] = self.env['ir.sequence'].next_by_code('estate.deposit') or 'New'
        return super().create(vals_list)


class EstateDepositDeduction(models.Model):
    _name = 'estate.deposit.deduction'
    _description = 'Deposit Deduction'
    deposit_id   = fields.Many2one('estate.deposit', ondelete='cascade', required=True)
    description  = fields.Char("Reason", required=True)
    currency_id  = fields.Many2one(related='deposit_id.currency_id')
    amount       = fields.Monetary("Amount (KES)", currency_field='currency_id', required=True)
