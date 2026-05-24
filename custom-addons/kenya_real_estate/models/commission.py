from odoo import models, fields, api, _
from odoo.exceptions import UserError


class EstateCommission(models.Model):
    _name        = 'estate.commission'
    _description = 'Agent Commission'
    _inherit     = ['mail.thread']
    _order       = 'create_date desc'

    name         = fields.Char("Commission Ref", readonly=True, default='New')
    agent_id     = fields.Many2one('res.users', string="Agent", required=True, tracking=True)
    property_id  = fields.Many2one('estate.property', string="Property", tracking=True)
    lease_id     = fields.Many2one('estate.lease', string="Lease")
    commission_type = fields.Selection([
        ('letting',    'Letting Fee'),
        ('sale',       'Sale Commission'),
        ('management', 'Management Fee'),
        ('renewal',    'Lease Renewal'),
    ], required=True, default='letting', tracking=True)
    basis        = fields.Selection([
        ('fixed',   'Fixed Amount'),
        ('percent', 'Percentage of Rent/Sale'),
    ], default='percent')
    rate         = fields.Float("Rate (%)", default=8.33)
    base_amount  = fields.Monetary("Base Amount (KES)", currency_field='currency_id')
    commission_amount = fields.Monetary("Commission (KES)", currency_field='currency_id',
                                        compute='_compute_commission', store=True)
    currency_id  = fields.Many2one('res.currency', default=lambda s: s.env.ref('base.KES'))
    status       = fields.Selection([
        ('draft',   'Draft'),
        ('approved','Approved'),
        ('paid',    'Paid'),
        ('cancelled','Cancelled'),
    ], default='draft', tracking=True)
    invoice_id   = fields.Many2one('account.move', string="Commission Invoice")
    notes        = fields.Text("Notes")

    @api.depends('basis', 'rate', 'base_amount')
    def _compute_commission(self):
        for rec in self:
            if rec.basis == 'percent':
                rec.commission_amount = rec.base_amount * rec.rate / 100
            else:
                rec.commission_amount = rec.base_amount

    def action_approve(self):
        self.write({'status': 'approved'})

    def action_create_invoice(self):
        self.ensure_one()
        partner = self.agent_id.partner_id
        inv = self.env['account.move'].create({
            'move_type':  'in_invoice',
            'partner_id': partner.id,
            'invoice_line_ids': [(0, 0, {
                'name':       f"Commission — {self.commission_type} — {self.property_id.name}",
                'quantity':   1,
                'price_unit': self.commission_amount,
            })]
        })
        self.write({'invoice_id': inv.id, 'status': 'paid'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': inv.id,
            'view_mode': 'form',
        }

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name', 'New') == 'New':
                v['name'] = self.env['ir.sequence'].next_by_code('estate.commission') or 'New'
        return super().create(vals_list)
