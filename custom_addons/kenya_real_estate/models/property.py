from odoo import models, fields, api

class EstateProperty(models.Model):
    _name = 'estate.property'
    _description = 'Real Estate Property'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char("Property Name", required=True, tracking=True)
    ref = fields.Char("Property Ref", readonly=True, copy=False, default='New')
    property_type = fields.Selection([
        ('residential', 'Residential'),
        ('commercial',  'Commercial'),
        ('land',        'Land'),
        ('industrial',  'Industrial'),
    ], string="Type", required=True, default='residential', tracking=True)
    status = fields.Selection([
        ('available',  'Available'),
        ('leased',     'Leased'),
        ('for_sale',   'For Sale'),
        ('sold',       'Sold'),
        ('maintenance','Under Maintenance'),
    ], string="Status", default='available', tracking=True)
    monthly_rent   = fields.Monetary("Monthly Rent (KES)", currency_field='currency_id')
    sale_price     = fields.Monetary("Sale Price (KES)",   currency_field='currency_id')
    currency_id    = fields.Many2one('res.currency', default=lambda s: s.env.ref('base.KES'))
    landlord_id    = fields.Many2one('res.partner', string="Landlord", required=True)
    location       = fields.Char("Location / Estate")
    county         = fields.Char("County")
    bedrooms       = fields.Integer("Bedrooms")
    bathrooms      = fields.Integer("Bathrooms")
    size_sqft      = fields.Float("Size (sq ft)")
    description    = fields.Html("Description")
    active         = fields.Boolean(default=True)
    lease_ids      = fields.One2many('estate.lease', 'property_id', string="Leases")
    lease_count    = fields.Integer(compute='_compute_lease_count', string="Leases")

    @api.depends('lease_ids')
    def _compute_lease_count(self):
        for rec in self:
            rec.lease_count = len(rec.lease_ids)

    def action_open_leases(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Leases',
            'res_model': 'estate.lease',
            'view_mode': 'list,form',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id},
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('ref', 'New') == 'New':
                vals['ref'] = self.env['ir.sequence'].next_by_code('estate.property') or 'New'
        return super().create(vals_list)
