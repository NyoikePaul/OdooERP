from odoo import models, fields

class RealEstateTenant(models.Model):
    _name = 'real.estate.tenant'
    _description = 'Real Estate Tenant'

    name = fields.Char(string='Name', required=True)
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    property_ids = fields.One2many('real.estate.lease', 'tenant_id', string='Leases')
