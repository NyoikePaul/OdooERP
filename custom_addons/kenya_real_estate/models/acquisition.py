"""
Property Acquisition — Kenya
Prospect → Due Diligence → Purchase → Registration → Available
Track: purchase price, legal fees, stamp duty, renovation costs.
"""
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class EstatePropertyAcquisition(models.Model):
    _name        = 'estate.property.acquisition'
    _description = 'Property Acquisition'
    _inherit     = ['mail.thread', 'mail.activity.mixin']
    _order       = 'create_date desc'

    name         = fields.Char("Acquisition Ref", readonly=True, copy=False, default='New')
    property_id  = fields.Many2one('estate.property', string="Property",
                                    required=True, ondelete='restrict')
    seller_id    = fields.Many2one('res.partner', string="Seller", required=True)
    agent_id     = fields.Many2one('res.users', string="Agent")

    currency_id  = fields.Many2one('res.currency', default=lambda s: s.env.ref('base.KES'))
    purchase_price   = fields.Monetary("Purchase Price (KES)", currency_field='currency_id')
    stamp_duty       = fields.Monetary("Stamp Duty (KES)", currency_field='currency_id',
                                        compute='_compute_costs', store=True)
    legal_fees       = fields.Monetary("Legal Fees (KES)", currency_field='currency_id')
    renovation_cost  = fields.Monetary("Renovation Cost (KES)", currency_field='currency_id')
    agent_fee        = fields.Monetary("Agent Fee (KES)", currency_field='currency_id')
    total_cost       = fields.Monetary("Total Acquisition Cost (KES)", currency_field='currency_id',
                                        compute='_compute_costs', store=True)
    roi_estimate     = fields.Float("Estimated ROI (%)", compute='_compute_roi', store=True)

    title_number    = fields.Char("Title Number")
    land_ref        = fields.Char("Land Reference Number")
    registration_ref= fields.Char("Registration Number")

    date_prospecting  = fields.Date("Prospecting Date", default=fields.Date.today)
    date_due_diligence= fields.Date("Due Diligence Date")
    date_purchase     = fields.Date("Purchase Date")
    date_registration = fields.Date("Registration Date")
    date_available    = fields.Date("Available for Letting/Sale")

    status = fields.Selection([
        ('prospect',       'Prospecting'),
        ('due_diligence',  'Due Diligence'),
        ('negotiation',    'Negotiation'),
        ('purchase',       'Purchase'),
        ('registration',   'Registration'),
        ('renovation',     'Renovation'),
        ('available',      'Available'),
        ('cancelled',      'Cancelled'),
    ], default='prospect', tracking=True)

    checklist_title_search = fields.Boolean("Title Search Done")
    checklist_rates        = fields.Boolean("Rates Clearance Certificate")
    checklist_consent      = fields.Boolean("Land Control Board Consent")
    checklist_valuation    = fields.Boolean("Independent Valuation Done")
    checklist_survey       = fields.Boolean("Survey Plan Obtained")
    notes                  = fields.Text()

    @api.depends('purchase_price','legal_fees','renovation_cost','agent_fee')
    def _compute_costs(self):
        for r in self:
            r.stamp_duty = r.purchase_price * 0.04
            r.total_cost = (r.purchase_price + r.stamp_duty +
                           (r.legal_fees or 0) + (r.renovation_cost or 0) + (r.agent_fee or 0))

    @api.depends('total_cost','property_id.monthly_rent')
    def _compute_roi(self):
        for r in self:
            if r.total_cost and r.property_id.monthly_rent:
                annual = r.property_id.monthly_rent * 12
                r.roi_estimate = (annual / r.total_cost) * 100
            else:
                r.roi_estimate = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name','New') == 'New':
                v['name'] = self.env['ir.sequence'].next_by_code('estate.acquisition') or 'New'
        return super().create(vals_list)

    def action_due_diligence(self):
        self.write({'status':'due_diligence','date_due_diligence':fields.Date.today()})

    def action_purchase(self):
        self.write({'status':'purchase','date_purchase':fields.Date.today()})
        self.property_id.write({
            'acquisition_cost': self.total_cost,
            'sale_price':       self.purchase_price,
        })

    def action_register(self):
        self.write({'status':'registration','date_registration':fields.Date.today()})
        if self.title_number:
            self.property_id.write({'status':'available'})

    def action_make_available(self):
        self.write({'status':'available','date_available':fields.Date.today()})
        self.property_id.write({'status':'available'})
        self.message_post(body=_(f"Property {self.property_id.name} is now available. "
                                  f"Total acquisition cost: KES {self.total_cost:,.0f}. "
                                  f"Estimated ROI: {self.roi_estimate:.1f}%"))
