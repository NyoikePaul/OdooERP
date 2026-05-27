from odoo import models, fields, api

class RealEstatePropertyType(models.Model):
    _name = "real.estate.property.type"
    _description = "Property Type"
    _order = "name"

    name = fields.Char(string="Property Type", required=True)


class RealEstatePropertyOffer(models.Model):
    _name = "real.estate.property.offer"
    _description = "Property Offer"
    _order = "price desc"

    price = fields.Float(string="Offer Amount", required=True)
    status = fields.Selection([
        ('accepted', 'Accepted'),
        ('refused', 'Refused'),
        ('pending', 'Pending')
    ], string="Status", default="pending", copy=False)
    
    partner_id = fields.Many2one('res.partner', string="Buyer", required=True)
    property_id = fields.Many2one('real.estate.property', string="Property", required=True, ondelete='cascade')


class RealEstateProperty(models.Model):
    _name = "real.estate.property"
    _description = "Real Estate Property"
    _order = "id desc"

    name = fields.Char(string="Title", required=True)
    description = fields.Text(string="Description")
    postcode = fields.Char(string="Postcode")
    date_availability = fields.Date(string="Available From", default=lambda self: fields.Date.today())
    expected_price = fields.Float(string="Expected Price", required=True)
    selling_price = fields.Float(string="Selling Price", readonly=True, copy=False)
    rent_amount = fields.Float(string="Rent Amount", default=0.0)
    bedrooms = fields.Integer(string="Bedrooms", default=2)
    living_area = fields.Integer(string="Living Area (sqm)")
    facades = fields.Integer(string="Facades")
    garage = fields.Boolean(string="Garage")
    garden = fields.Boolean(string="Garden")
    garden_area = fields.Integer(string="Garden Area (sqm)")
    garden_orientation = fields.Selection([
        ('N', 'North'),
        ('S', 'South'),
        ('E', 'East'),
        ('W', 'West')
    ], string="Garden Orientation")
    
    # Relationships
    property_type_id = fields.Many2one('real.estate.property.type', string="Property Type")
    offer_ids = fields.One2many('real.estate.property.offer', 'property_id', string="Offers")
    
    # Automated Computed Field
    total_area = fields.Integer(string="Total Area (sqm)", compute="_compute_total_area", store=True)
    
    state = fields.Selection([
        ('new', 'New'),
        ('offer_received', 'Offer Received'),
        ('offer_accepted', 'Offer Accepted'),
        ('sold', 'Sold'),
        ('canceled', 'Canceled')
    ], string="Status", default='new', copy=False, required=True)
    
    active = fields.Boolean(string="Active", default=True)

    @api.depends('living_area', 'garden_area')
    def _compute_total_area(self):
        for record in self:
            record.total_area = (record.living_area or 0) + (record.garden_area or 0)
