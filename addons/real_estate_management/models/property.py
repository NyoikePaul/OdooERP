from odoo import models, fields, api

class RealEstateProperty(models.Model):
    _name = 'real.estate.property'
    _description = 'Premium Real Estate Property'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Property Name", required=True)
    state = fields.Selection([
        ('available', 'Available'),
        ('rented', 'Rented'),
        ('maintenance', 'Under Maintenance')
    ], default='available', tracking=True)
    
    rent_amount = fields.Monetary(string="Monthly Rent", currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    
    def action_set_maintenance(self):
        self.state = 'maintenance'
