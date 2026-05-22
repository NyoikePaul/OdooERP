from odoo import models, fields, api


class EstatePropertyType(models.Model):
    _name = 'estate.property.type'
    _description = 'Property Type'
    _order = 'sequence, name'

    name       = fields.Char("Type", required=True, translate=True)
    sequence   = fields.Integer("Sequence", default=10)
    color      = fields.Integer("Color Index")
    icon       = fields.Char("Icon", default='fa-building')
    property_ids = fields.One2many('estate.property', 'property_type_id', string="Properties")
    property_count = fields.Integer(compute='_compute_property_count', string="Properties")

    @api.depends('property_ids')
    def _compute_property_count(self):
        for rec in self:
            rec.property_count = len(rec.property_ids)


class EstatePropertyTag(models.Model):
    _name = 'estate.property.tag'
    _description = 'Property Tag'
    _order = 'name'

    name  = fields.Char("Tag", required=True, translate=True)
    color = fields.Integer("Color Index")


class EstateAmenity(models.Model):
    _name = 'estate.amenity'
    _description = 'Property Amenity'
    _order = 'name'

    name     = fields.Char("Amenity", required=True, translate=True)
    icon     = fields.Char("FA Icon", default='fa-check')
    category = fields.Selection([
        ('security', 'Security'),
        ('leisure',  'Leisure'),
        ('utility',  'Utility'),
        ('transport','Transport'),
    ], default='utility')
