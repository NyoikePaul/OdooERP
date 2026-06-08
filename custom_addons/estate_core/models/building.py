from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)


class EstateBuilding(models.Model):
    _name        = 'estate.building'
    _description = 'Apartment Block / Commercial Building'
    _inherit     = ['mail.thread', 'mail.activity.mixin']
    _order       = 'name'

    name         = fields.Char("Building Name", required=True, tracking=True)
    ref          = fields.Char("Building Ref", readonly=True, copy=False, default='New')
    landlord_id  = fields.Many2one('res.partner', string="Owner", required=True)
    manager_id   = fields.Many2one('res.users',   string="Property Manager")
    street       = fields.Char("Street / Estate")
    county       = fields.Selection([
        ('nairobi','Nairobi'),('mombasa','Mombasa'),('kisumu','Kisumu'),
        ('nakuru','Nakuru'),('other','Other'),
    ], string="County")
    year_built   = fields.Integer("Year Built")
    total_floors = fields.Integer("Total Floors")
    has_lift     = fields.Boolean("Has Lift/Elevator")
    has_generator= fields.Boolean("Has Generator")
    has_borehole = fields.Boolean("Has Borehole")
    image_1920   = fields.Image("Building Photo", max_width=1920, max_height=1920)
    active       = fields.Boolean(default=True)

    unit_ids     = fields.One2many('estate.unit', 'building_id', string="Units")
    unit_count   = fields.Integer(compute='_compute_stats', store=True)
    occupied     = fields.Integer(compute='_compute_stats', store=True)
    vacant       = fields.Integer(compute='_compute_stats', store=True)
    occupancy_rate = fields.Float(compute='_compute_stats', store=True, string="Occupancy %", digits=(5,1))

    currency_id  = fields.Many2one('res.currency', default=lambda s: s.env.ref('base.KES'))
    total_monthly_income = fields.Monetary("Monthly Income (KES)", currency_field='currency_id', compute='_compute_stats', store=True)

    @api.depends('unit_ids.status', 'unit_ids.monthly_rent')
    def _compute_stats(self):
        for b in self:
            units    = b.unit_ids
            leased   = units.filtered(lambda u: u.status == 'leased')
            b.unit_count    = len(units)
            b.occupied      = len(leased)
            b.vacant        = len(units) - len(leased)
            b.occupancy_rate= (len(leased)/len(units)*100) if units else 0.0
            b.total_monthly_income = sum(leased.mapped('monthly_rent'))

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('ref','New') == 'New':
                v['ref'] = self.env['ir.sequence'].next_by_code('estate.building') or 'New'
        return super().create(vals_list)


class EstateUnit(models.Model):
    _name        = 'estate.unit'
    _description = 'Property Unit / Apartment'
    _inherit     = ['mail.thread']
    _order       = 'building_id, floor, name'

    name         = fields.Char("Unit No.", required=True, tracking=True)
    ref          = fields.Char("Unit Ref", readonly=True, copy=False, default='New')
    building_id  = fields.Many2one('estate.building', string="Building", ondelete='restrict', index=True)
    property_id  = fields.Many2one('estate.property', string="Standalone Property", ondelete='set null')
    floor        = fields.Integer("Floor")
    unit_type    = fields.Selection([
        ('bedsitter','Bedsitter'),('studio','Studio'),
        ('1br','1 Bedroom'),('2br','2 Bedroom'),('3br','3 Bedroom'),
        ('4br+','4+ Bedroom'),('penthouse','Penthouse'),
        ('office','Office Suite'),('shop','Shop/Retail'),
    ], default='2br', string="Unit Type")
    size_sqft    = fields.Float("Size (sq ft)")
    currency_id  = fields.Many2one('res.currency', default=lambda s: s.env.ref('base.KES'))
    monthly_rent = fields.Monetary("Monthly Rent (KES)", currency_field='currency_id')
    status       = fields.Selection([
        ('vacant','Vacant'),('leased','Leased'),
        ('maintenance','Under Maintenance'),('reserved','Reserved'),
    ], default='vacant', tracking=True, index=True)
    tenant_id    = fields.Many2one('res.partner', string="Current Tenant", readonly=True)
    lease_ids    = fields.One2many('estate.lease', 'unit_id', string="Leases")
    active       = fields.Boolean(default=True)

    _sql_constraints = [('ref_unique','UNIQUE(ref)','Unit reference must be unique.')]

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('ref','New') == 'New':
                v['ref'] = self.env['ir.sequence'].next_by_code('estate.unit') or 'New'
        return super().create(vals_list)
