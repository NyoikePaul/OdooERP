from odoo import models, fields

class RealEstateProperty(models.Model):
    _name = 'real.estate.property'
    _description = 'Premium Property'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    state = fields.Selection([('available', 'Available')], default='available', tracking=True)
_sql_constraints = [('check_price', 'CHECK(price > 0)', 'Price must be positive')]
