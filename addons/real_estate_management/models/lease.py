from odoo import models, fields

class RealEstateLease(models.Model):
    _name = 'real.estate.lease'
    _description = 'Real Estate Lease'

    name = fields.Char(string='Lease Reference', required=True, copy=False, readonly=True, default='New')
    property_id = fields.Many2one('real.estate.property', string='Property', required=True)
    tenant_id = fields.Many2one('real.estate.tenant', string='Tenant', required=True)
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    rent_amount = fields.Float(string='Monthly Rent', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired')
    ], string='Status', default='draft')
