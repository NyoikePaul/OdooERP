from odoo import models, fields, api


class EstateBuilding(models.Model):
    _name        = 'estate.building'
    _description = 'Building / Block'
    _inherit     = ['mail.thread']
    _order       = 'name'

    name         = fields.Char("Building Name", required=True, tracking=True)
    ref          = fields.Char("Building Ref", readonly=True, default='New', copy=False)
    landlord_id  = fields.Many2one('res.partner', string="Owner", required=True)
    agent_id     = fields.Many2one('res.users', string="Manager")
    street       = fields.Char("Street / Estate")
    county       = fields.Char("County")
    year_built   = fields.Integer("Year Built")
    total_floors = fields.Integer("Total Floors")
    image_1920   = fields.Image("Building Photo", max_width=1920, max_height=1920)
    description  = fields.Html("Description")
    active       = fields.Boolean(default=True)

    unit_ids     = fields.One2many('estate.unit', 'building_id', string="Units")
    unit_count   = fields.Integer(compute='_compute_stats', store=True)
    occupied     = fields.Integer(compute='_compute_stats', store=True)
    vacant       = fields.Integer(compute='_compute_stats', store=True)
    occupancy_rate = fields.Float(compute='_compute_stats', store=True, string="Occupancy %")

    @api.depends('unit_ids', 'unit_ids.status')
    def _compute_stats(self):
        for b in self:
            units    = b.unit_ids
            occupied = units.filtered(lambda u: u.status == 'leased')
            b.unit_count      = len(units)
            b.occupied        = len(occupied)
            b.vacant          = len(units) - len(occupied)
            b.occupancy_rate  = (len(occupied) / len(units) * 100) if units else 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('ref', 'New') == 'New':
                v['ref'] = self.env['ir.sequence'].next_by_code('estate.building') or 'New'
        return super().create(vals_list)


class EstateUnit(models.Model):
    _name        = 'estate.unit'
    _description = 'Property Unit / Apartment'
    _inherit     = ['mail.thread']
    _order       = 'building_id, floor, name'

    name         = fields.Char("Unit Name/No.", required=True, tracking=True)
    ref          = fields.Char("Unit Ref", readonly=True, default='New', copy=False)
    building_id  = fields.Many2one('estate.building', string="Building",
                                   ondelete='restrict', tracking=True)
    property_id  = fields.Many2one('estate.property', string="Or Standalone Property",
                                   ondelete='set null',
                                   help="Link to a property if not part of a building")
    floor        = fields.Integer("Floor")
    unit_type    = fields.Selection([
        ('studio',    'Studio'),
        ('1br',       '1 Bedroom'),
        ('2br',       '2 Bedroom'),
        ('3br',       '3 Bedroom'),
        ('4br+',      '4+ Bedroom'),
        ('penthouse', 'Penthouse'),
        ('office',    'Office'),
        ('shop',      'Shop'),
    ], string="Unit Type", default='2br')
    size_sqft    = fields.Float("Size (sq ft)")
    monthly_rent = fields.Monetary("Monthly Rent (KES)", currency_field='currency_id')
    currency_id  = fields.Many2one('res.currency', default=lambda s: s.env.ref('base.KES'))
    status       = fields.Selection([
        ('vacant',      'Vacant'),
        ('leased',      'Leased'),
        ('maintenance', 'Under Maintenance'),
        ('reserved',    'Reserved'),
    ], default='vacant', tracking=True)
    tenant_id    = fields.Many2one('res.partner', string="Current Tenant", readonly=True)
    lease_ids    = fields.One2many('estate.lease', 'unit_id', string="Leases")
    active       = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('ref', 'New') == 'New':
                v['ref'] = self.env['ir.sequence'].next_by_code('estate.unit') or 'New'
        return super().create(vals_list)
