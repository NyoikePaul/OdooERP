#!/bin/bash
MODULE="real_estate_management"
mkdir -p $MODULE/{models,views,security}

# Manifest
cat <<EOM > $MODULE/__manifest__.py
{
    'name': 'Premium Real Estate Management',
    'version': '1.0',
    'depends': ['base', 'mail', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/property_views.xml',
    ],
    'application': True,
}
EOM

# Init files
echo "from . import models" > $MODULE/__init__.py
echo "from . import property" > $MODULE/models/__init__.py

# The Model
cat <<EOM > $MODULE/models/property.py
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
EOM

# Security
echo "id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink" > $MODULE/security/ir.model.access.csv
echo "access_re_property,access.re.property,model_real_estate_property,base.group_user,1,1,1,1" >> $MODULE/security/ir.model.access.csv

echo "Scaffolding complete!"
