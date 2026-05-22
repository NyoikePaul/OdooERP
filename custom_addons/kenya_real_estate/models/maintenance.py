from odoo import models, fields, api
from odoo.exceptions import UserError


class EstateMaintenanceRequest(models.Model):
    _name = 'estate.maintenance.request'
    _description = 'Property Maintenance Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, create_date desc'

    name        = fields.Char("Issue", required=True, tracking=True)
    ref         = fields.Char("Ref", readonly=True, default='New', copy=False)
    property_id = fields.Many2one('estate.property', string="Property",
                                  required=True, ondelete='cascade', tracking=True)
    lease_id    = fields.Many2one('estate.lease', string="Reported by Lease",
                                  domain="[('property_id','=',property_id)]")
    reported_by = fields.Many2one('res.partner', string="Reported By")
    assigned_to = fields.Many2one('res.users', string="Assigned To", tracking=True)
    category    = fields.Selection([
        ('plumbing',   'Plumbing'),
        ('electrical', 'Electrical'),
        ('structural', 'Structural'),
        ('cleaning',   'Cleaning'),
        ('security',   'Security'),
        ('other',      'Other'),
    ], required=True, default='other', tracking=True)
    priority    = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Urgent'),
        ('2', 'Very Urgent'),
        ('3', 'Emergency'),
    ], default='0', tracking=True)
    status      = fields.Selection([
        ('new',         'New'),
        ('in_progress', 'In Progress'),
        ('done',        'Done'),
        ('cancelled',   'Cancelled'),
    ], default='new', tracking=True)
    description    = fields.Text("Description")
    estimated_cost = fields.Monetary("Estimated Cost (KES)", currency_field='currency_id')
    actual_cost    = fields.Monetary("Actual Cost (KES)",    currency_field='currency_id')
    currency_id    = fields.Many2one('res.currency', default=lambda s: s.env.ref('base.KES'))
    date_reported  = fields.Date("Date Reported", default=fields.Date.today)
    date_resolved  = fields.Date("Date Resolved")

    def action_start(self):
        self.write({'status': 'in_progress'})
        self.property_id.write({'status': 'maintenance'})

    def action_done(self):
        self.write({'status': 'done', 'date_resolved': fields.Date.today()})
        # Restore property status if no other open maintenance requests
        open_requests = self.env['estate.maintenance.request'].search([
            ('property_id', '=', self.property_id.id),
            ('status', 'in', ['new', 'in_progress']),
            ('id', '!=', self.id),
        ])
        if not open_requests:
            active_lease = self.env['estate.lease'].search([
                ('property_id', '=', self.property_id.id),
                ('status', '=', 'active')
            ], limit=1)
            new_status = 'leased' if active_lease else 'available'
            self.property_id.write({'status': new_status})

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('ref', 'New') == 'New':
                vals['ref'] = self.env['ir.sequence'].next_by_code('estate.maintenance') or 'New'
        return super().create(vals_list)
