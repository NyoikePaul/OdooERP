from odoo import models, fields, api, _
from odoo.exceptions import UserError


class EstateCommission(models.Model):
    _name        = 'estate.commission'
    _description = 'Agent Commission'
    _inherit     = ['mail.thread']
    _order       = 'create_date desc'

    name         = fields.Char("Commission Ref", readonly=True, copy=False, default='New')
    agent_id     = fields.Many2one('res.users',   string="Agent", required=True)
    property_id  = fields.Many2one('estate.property')
    lease_id     = fields.Many2one('estate.lease')
    comm_type    = fields.Selection([
        ('letting','Letting Fee'),('sale','Sale Commission'),
        ('management','Management Fee'),('renewal','Renewal Fee'),
    ], required=True, default='letting')
    basis        = fields.Selection([('fixed','Fixed'),('percent','Percentage')], default='percent')
    rate         = fields.Float("Rate (%)", default=8.33)
    currency_id  = fields.Many2one('res.currency', default=lambda s: s.env.ref('base.KES'))
    base_amount  = fields.Monetary("Base Amount", currency_field='currency_id')
    commission   = fields.Monetary("Commission (KES)", currency_field='currency_id',
                                    compute='_compute_commission', store=True)
    status       = fields.Selection([('draft','Draft'),('approved','Approved'),('paid','Paid')], default='draft', tracking=True)
    invoice_id   = fields.Many2one('account.move', string="Invoice")
    notes        = fields.Text()

    @api.depends('basis','rate','base_amount')
    def _compute_commission(self):
        for r in self:
            r.commission = r.base_amount * r.rate / 100 if r.basis=='percent' else r.base_amount

    def action_approve(self):
        self.write({'status':'approved'})

    def action_create_invoice(self):
        self.ensure_one()
        inv = self.env['account.move'].create({
            'move_type':'in_invoice','partner_id':self.agent_id.partner_id.id,
            'invoice_line_ids':[(0,0,{
                'name':f"Commission — {self.comm_type} — {self.property_id.name}",
                'quantity':1,'price_unit':self.commission,
            })]
        })
        self.write({'invoice_id':inv.id,'status':'paid'})
        return {'type':'ir.actions.act_window','res_model':'account.move','res_id':inv.id,'view_mode':'form'}

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name','New')=='New':
                v['name'] = self.env['ir.sequence'].next_by_code('estate.commission') or 'New'
        return super().create(vals_list)
