from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class EstateProperty(models.Model):
    _name = 'estate.property'
    _description = 'Real Estate Property'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    # ── Identity ──────────────────────────────────────
    name             = fields.Char("Property Name", required=True, tracking=True)
    ref              = fields.Char("Property Ref", readonly=True, copy=False, default='New')
    property_type_id = fields.Many2one('estate.property.type', string="Category", tracking=True)
    tag_ids          = fields.Many2many('estate.property.tag', string="Tags")
    amenity_ids      = fields.Many2many('estate.amenity', string="Amenities")

    # ── Classification ────────────────────────────────
    property_type = fields.Selection([
        ('residential', 'Residential'),
        ('commercial',  'Commercial'),
        ('land',        'Land'),
        ('industrial',  'Industrial'),
    ], string="Type", required=True, default='residential', tracking=True)

    status = fields.Selection([
        ('available',   'Available'),
        ('leased',      'Leased'),
        ('for_sale',    'For Sale'),
        ('sold',        'Sold'),
        ('maintenance', 'Under Maintenance'),
    ], string="Status", default='available', tracking=True)

    # ── Financials ────────────────────────────────────
    monthly_rent    = fields.Monetary("Monthly Rent (KES)",  currency_field='currency_id', tracking=True)
    sale_price      = fields.Monetary("Sale Price (KES)",    currency_field='currency_id')
    expected_yield  = fields.Float("Expected Yield (%)", compute='_compute_yield', store=True)
    total_revenue   = fields.Monetary("Total Revenue (KES)", currency_field='currency_id',
                                      compute='_compute_revenue', store=True)
    currency_id     = fields.Many2one('res.currency', default=lambda s: s.env.ref('base.KES'))

    # ── Location ──────────────────────────────────────
    landlord_id     = fields.Many2one('res.partner', string="Landlord/Owner", required=True)
    agent_id        = fields.Many2one('res.users', string="Listing Agent")
    location        = fields.Char("Location / Estate")
    street          = fields.Char("Street")
    county          = fields.Char("County")
    constituency    = fields.Char("Constituency")
    latitude        = fields.Float("GPS Latitude",  digits=(10, 7))
    longitude       = fields.Float("GPS Longitude", digits=(10, 7))

    # ── Physical Details ──────────────────────────────
    bedrooms        = fields.Integer("Bedrooms")
    bathrooms       = fields.Integer("Bathrooms")
    size_sqft       = fields.Float("Size (sq ft)")
    floor           = fields.Integer("Floor Number")
    total_floors    = fields.Integer("Total Floors in Building")
    year_built      = fields.Integer("Year Built")
    furnished       = fields.Selection([
        ('unfurnished',  'Unfurnished'),
        ('semi',         'Semi-Furnished'),
        ('fully',        'Fully Furnished'),
    ], default='unfurnished')
    parking_spaces  = fields.Integer("Parking Spaces")
    garden          = fields.Boolean("Garden / Compound")
    garden_area_sqft = fields.Float("Garden Area (sq ft)")

    # ── Media ─────────────────────────────────────────
    image_1920      = fields.Image("Main Photo", max_width=1920, max_height=1920)
    image_128       = fields.Image("Thumbnail", related='image_1920',
                                   max_width=128, max_height=128, store=True)
    description     = fields.Html("Description")
    active          = fields.Boolean(default=True)

    # ── Relations ─────────────────────────────────────
    lease_ids           = fields.One2many('estate.lease', 'property_id', string="Leases")
    offer_ids           = fields.One2many('estate.offer',      'property_id', string="Offers")
    commission_ids      = fields.One2many('estate.commission', 'property_id', string="Commissions")
    inspection_ids      = fields.One2many('estate.inspection', 'property_id', string="Inspections")
    unit_ids            = fields.One2many('estate.unit',       'property_id', string="Units")
    offer_ids           = fields.One2many('estate.offer',      'property_id', string="Offers")
    commission_ids      = fields.One2many('estate.commission', 'property_id', string="Commissions")
    inspection_ids      = fields.One2many('estate.inspection', 'property_id', string="Inspections")
    unit_ids            = fields.One2many('estate.unit',       'property_id', string="Units")
    offer_ids           = fields.One2many('estate.offer',      'property_id', string="Offers")
    commission_ids      = fields.One2many('estate.commission', 'property_id', string="Commissions")
    inspection_ids      = fields.One2many('estate.inspection', 'property_id', string="Inspections")
    unit_ids            = fields.One2many('estate.unit',       'property_id', string="Units")
    maintenance_ids     = fields.One2many('estate.maintenance.request', 'property_id',
                                          string="Maintenance Requests")

    # ── Computed ──────────────────────────────────────
    lease_count         = fields.Integer(compute='_compute_lease_count',       store=True)
    active_lease_id     = fields.Many2one('estate.lease', compute='_compute_active_lease',
                                          string="Current Lease", store=True)
    current_tenant_id   = fields.Many2one('res.partner', compute='_compute_active_lease',
                                          string="Current Tenant", store=True)
    maintenance_count   = fields.Integer(compute='_compute_maintenance_count',  store=True)
    offer_count         = fields.Integer(compute='_compute_offer_count', store=True)
    offer_count         = fields.Integer(compute='_compute_offer_count', store=True)
    offer_count         = fields.Integer(compute='_compute_offer_count', store=True)
    occupancy_days      = fields.Integer(compute='_compute_occupancy',          store=True)
    annual_revenue      = fields.Monetary(compute='_compute_revenue',
                                          currency_field='currency_id',         store=True)

    # ── Compute Methods ───────────────────────────────
    @api.depends('lease_ids')
    def _compute_lease_count(self):
        for rec in self:
            rec.lease_count = len(rec.lease_ids)

    @api.depends('lease_ids', 'lease_ids.status')
    def _compute_active_lease(self):
        for rec in self:
            active = rec.lease_ids.filtered(lambda l: l.status == 'active')
            rec.active_lease_id   = active[0] if active else False
            rec.current_tenant_id = active[0].tenant_id if active else False

    @api.depends('offer_ids')
    def _compute_offer_count(self):
        for rec in self:
            rec.offer_count = len(rec.offer_ids)

    @api.depends('offer_ids')
    def _compute_offer_count(self):
        for rec in self:
            rec.offer_count = len(rec.offer_ids)

    @api.depends('offer_ids')
    def _compute_offer_count(self):
        for rec in self:
            rec.offer_count = len(rec.offer_ids)

    @api.depends('maintenance_ids')
    def _compute_maintenance_count(self):
        for rec in self:
            rec.maintenance_count = len(rec.maintenance_ids)

    @api.depends('lease_ids', 'lease_ids.date_start', 'lease_ids.date_end', 'lease_ids.status')
    def _compute_occupancy(self):
        for rec in self:
            total = sum(
                (l.date_end - l.date_start).days
                for l in rec.lease_ids
                if l.status in ('active', 'expired') and l.date_start and l.date_end
            )
            rec.occupancy_days = total

    @api.depends('lease_ids', 'lease_ids.payment_ids',
                 'lease_ids.payment_ids.payment_state', 'monthly_rent')
    def _compute_revenue(self):
        for rec in self:
            paid = sum(
                inv.amount_total
                for lease in rec.lease_ids
                for inv in lease.payment_ids
                if inv.payment_state == 'paid' and inv.move_type == 'out_invoice'
            )
            rec.total_revenue   = paid
            rec.annual_revenue  = rec.monthly_rent * 12

    @api.depends('sale_price', 'annual_revenue')
    def _compute_yield(self):
        for rec in self:
            if rec.sale_price:
                rec.expected_yield = (rec.annual_revenue / rec.sale_price) * 100
            else:
                rec.expected_yield = 0.0

    # ── Actions ───────────────────────────────────────
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

    def action_open_offers(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Offers & Enquiries',
            'res_model': 'estate.offer',
            'view_mode': 'list,form',
            'domain': [('property_id','=',self.id)],
            'context': {'default_property_id': self.id},
        }

    def action_open_offers(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Offers & Enquiries',
            'res_model': 'estate.offer',
            'view_mode': 'list,form',
            'domain': [('property_id','=',self.id)],
            'context': {'default_property_id': self.id},
        }

    def action_open_offers(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Offers & Enquiries',
            'res_model': 'estate.offer',
            'view_mode': 'list,form',
            'domain': [('property_id','=',self.id)],
            'context': {'default_property_id': self.id},
        }

    def action_open_maintenance(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Maintenance Requests',
            'res_model': 'estate.maintenance.request',
            'view_mode': 'list,form',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id},
        }

    def action_set_available(self):
        self.write({'status': 'available'})

    def action_set_for_sale(self):
        self.write({'status': 'for_sale'})

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('ref', 'New') == 'New':
                vals['ref'] = self.env['ir.sequence'].next_by_code('estate.property') or 'New'
        return super().create(vals_list)

    # ── Compute Methods ────────────────────────────────
    @api.depends('monthly_rent', 'sale_price')
    def _compute_yield(self):
        for record in self:
            if record.sale_price and record.monthly_rent:
                record.expected_yield = ((record.monthly_rent * 12) / record.sale_price) * 100
            else:
                record.expected_yield = 0.0

    @api.depends('status', 'monthly_rent')
    def _compute_revenue(self):
        for record in self:
            record.total_revenue = record.total_revenue or 0.0

    # ── CRUD Overrides ─────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('ref', 'New') == 'New':
                vals['ref'] = self.env['ir.sequence'].next_by_code('estate.property') or 'New'
        return super().create(vals_list)
