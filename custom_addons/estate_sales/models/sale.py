"""
Property Sales Workflow — Kenya
Lead → Viewing → Offer → Reservation → Sale Agreement → Invoice → Payment → Transfer → Sold
"""
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging
_logger = logging.getLogger(__name__)


class EstatePropertySale(models.Model):
    _name        = 'estate.property.sale'
    _description = 'Property Sale Transaction'
    _inherit     = ['mail.thread', 'mail.activity.mixin']
    _order       = 'create_date desc'
    _rec_name    = 'name'

    name         = fields.Char("Sale Ref", readonly=True, copy=False, default='New')
    property_id  = fields.Many2one('estate.property', required=True,
                                    ondelete='restrict', tracking=True)
    buyer_id     = fields.Many2one('res.partner', string="Buyer", required=True, tracking=True)
    agent_id     = fields.Many2one('res.users',   string="Agent", tracking=True)
    source       = fields.Selection([
        ('website','Website'),('walk_in','Walk-in'),
        ('facebook','Facebook/Social'),('referral','Referral'),
        ('agent','Agent'),('other','Other'),
    ], default='walk_in', string="Lead Source")

    # Financials
    currency_id   = fields.Many2one('res.currency', default=lambda s: s.env.ref('base.KES'))
    asking_price  = fields.Monetary("Asking Price (KES)", currency_field='currency_id',
                                     related='property_id.sale_price', readonly=True)
    agreed_price  = fields.Monetary("Agreed Sale Price (KES)", currency_field='currency_id',
                                     tracking=True)
    deposit_paid  = fields.Monetary("Reservation Deposit (KES)", currency_field='currency_id')
    stamp_duty    = fields.Monetary("Stamp Duty (4%) KES", currency_field='currency_id',
                                     compute='_compute_charges', store=True)
    legal_fees    = fields.Monetary("Legal Fees (KES)", currency_field='currency_id')
    agent_commission = fields.Monetary("Agent Commission (KES)", currency_field='currency_id',
                                        compute='_compute_charges', store=True)
    commission_rate = fields.Float("Commission Rate (%)", default=3.0)
    total_payable   = fields.Monetary("Total Payable (KES)", currency_field='currency_id',
                                       compute='_compute_charges', store=True)

    # Dates
    date_viewing       = fields.Date("Viewing Date")
    date_offer         = fields.Date("Offer Date")
    date_reservation   = fields.Date("Reservation Date")
    date_agreement     = fields.Date("Sale Agreement Date")
    date_completion    = fields.Date("Completion/Transfer Date")

    # Documents
    title_number       = fields.Char("Title Deed Number")
    sale_agreement_ref = fields.Char("Sale Agreement Ref")
    transfer_ref       = fields.Char("Transfer/Registration Ref")

    # Status
    status = fields.Selection([
        ('lead',        'Lead'),
        ('viewing',     'Viewing Scheduled'),
        ('offer',       'Offer Made'),
        ('reserved',    'Reserved'),
        ('agreement',   'Sale Agreement'),
        ('invoiced',    'Invoiced'),
        ('paid',        'Payment Complete'),
        ('transfer',    'Transfer in Progress'),
        ('sold',        'Sold'),
        ('cancelled',   'Cancelled'),
    ], default='lead', tracking=True)

    invoice_ids  = fields.One2many('account.move', 'sale_id', string="Invoices")
    invoice_count = fields.Integer(compute='_compute_inv_count')
    notes        = fields.Text()

    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'Sale ref must be unique.'),
        ('agreed_price_pos', 'CHECK(agreed_price >= 0)', 'Price cannot be negative.'),
    ]

    @api.depends('agreed_price', 'commission_rate')
    def _compute_charges(self):
        for r in self:
            r.stamp_duty       = r.agreed_price * 0.04
            r.agent_commission = r.agreed_price * r.commission_rate / 100
            r.total_payable    = r.agreed_price + r.stamp_duty + (r.legal_fees or 0)

    def _compute_inv_count(self):
        for r in self:
            r.invoice_count = len(r.invoice_ids)

    @api.constrains('property_id', 'status')
    def _check_not_sold(self):
        for r in self:
            if r.status == 'reserved':
                others = self.search([
                    ('property_id', '=', r.property_id.id),
                    ('status', 'in', ('reserved','agreement','invoiced','paid','transfer')),
                    ('id', '!=', r.id),
                ])
                if others:
                    raise ValidationError(
                        _(f"Property {r.property_id.name} is already reserved/sold: {others[:1].name}"))

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name','New') == 'New':
                v['name'] = self.env['ir.sequence'].next_by_code('estate.property.sale') or 'New'
        return super().create(vals_list)

    def action_schedule_viewing(self):
        self.write({'status':'viewing','date_viewing':fields.Date.today()})
        self.property_id.write({'status':'reserved'})

    def action_make_offer(self):
        self.write({'status':'offer','date_offer':fields.Date.today()})

    def action_reserve(self):
        if not self.agreed_price:
            raise UserError(_("Set agreed price before reserving."))
        self.write({'status':'reserved','date_reservation':fields.Date.today()})
        self.property_id.write({'status':'reserved'})
        self.message_post(body=_(
            f"Property reserved for {self.buyer_id.name} at KES {self.agreed_price:,.0f}. "
            f"Deposit: KES {self.deposit_paid:,.0f}."))

    def action_sign_agreement(self):
        self.write({'status':'agreement','date_agreement':fields.Date.today()})

    def action_create_invoice(self):
        self.ensure_one()
        inv = self.env['account.move'].create({
            'move_type':    'out_invoice',
            'partner_id':   self.buyer_id.id,
            'sale_id':      self.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [
                (0,0,{'name':f"Property Sale — {self.property_id.name}",
                      'quantity':1,'price_unit':self.agreed_price}),
                (0,0,{'name':f"Stamp Duty (4%)",
                      'quantity':1,'price_unit':self.stamp_duty}),
            ] + ([(0,0,{'name':'Legal Fees','quantity':1,'price_unit':self.legal_fees})]
                 if self.legal_fees else []),
        })
        self.write({'status':'invoiced'})
        return {'type':'ir.actions.act_window','res_model':'account.move',
                'res_id':inv.id,'view_mode':'form'}

    def action_complete_transfer(self):
        self.write({'status':'sold','date_completion':fields.Date.today()})
        self.property_id.write({'status':'sold'})
        # Create agent commission record
        if self.agent_commission and self.agent_id:
            self.env['estate.commission'].create({
                'agent_id':    self.agent_id.id,
                'property_id': self.property_id.id,
                'comm_type':   'sale',
                'basis':       'fixed',
                'commission':  self.agent_commission,
                'base_amount': self.agreed_price,
                'rate':        self.commission_rate,
            })
        self.message_post(body=_(
            f"SOLD ✅ Property transferred to {self.buyer_id.name}. "
            f"Sale price: KES {self.agreed_price:,.0f}. Title: {self.title_number or 'Pending'}."))

    def action_cancel(self):
        prev_status = self.property_id.status
        self.write({'status':'cancelled'})
        if prev_status in ('reserved','for_sale'):
            self.property_id.write({'status':'available'})

    def action_open_invoices(self):
        self.ensure_one()
        return {'type':'ir.actions.act_window','name':'Invoices','res_model':'account.move',
                'view_mode':'list,form','domain':[('sale_id','=',self.id)]}
