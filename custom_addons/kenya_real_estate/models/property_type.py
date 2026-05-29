from odoo import models, fields, api


class EstatePropertyType(models.Model):
    _name        = 'estate.property.type'
    _description = 'Property Type'
    _order       = 'sequence, name'

    name         = fields.Char("Type", required=True, translate=True)
    sequence     = fields.Integer("Sequence", default=10)
    property_ids = fields.One2many('estate.property', 'property_type_id', string="Properties")
    property_count = fields.Integer(compute='_compute_count', store=True)
    active       = fields.Boolean(default=True)

    _sql_constraints = [('name_unique', 'UNIQUE(name)', 'Property type must be unique.')]

    @api.depends('property_ids')
    def _compute_count(self):
        for rec in self:
            rec.property_count = len(rec.property_ids)


class EstatePropertyTag(models.Model):
    _name        = 'estate.property.tag'
    _description = 'Property Tag'
    _order       = 'name'
    name         = fields.Char("Tag", required=True, translate=True)
    color        = fields.Integer("Color Index", default=0)
    _sql_constraints = [('name_unique', 'UNIQUE(name)', 'Tag must be unique.')]


class EstateAmenity(models.Model):
    _name        = 'estate.amenity'
    _description = 'Property Amenity'
    _order       = 'sequence, name'

    name         = fields.Char("Amenity", required=True, translate=True)
    sequence     = fields.Integer(default=10)
    category     = fields.Selection([
        ('utility',   'Utility'),
        ('security',  'Security'),
        ('leisure',   'Leisure'),
        ('transport', 'Transport'),
    ], default='utility')
    icon         = fields.Char("FA Icon", default='fa-check')
    active       = fields.Boolean(default=True)
