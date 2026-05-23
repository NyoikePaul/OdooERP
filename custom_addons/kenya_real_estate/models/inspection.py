from odoo import models, fields, api, _
from odoo.exceptions import UserError


class EstateInspection(models.Model):
    _name        = 'estate.inspection'
    _description = 'Property Inspection Report'
    _inherit     = ['mail.thread', 'mail.activity.mixin']
    _order       = 'date desc'

    name         = fields.Char("Report Ref", readonly=True, default='New', copy=False)
    property_id  = fields.Many2one('estate.property', string="Property",
                                   required=True, ondelete='restrict', tracking=True)
    unit_id      = fields.Many2one('estate.unit', string="Unit")
    lease_id     = fields.Many2one('estate.lease', string="Lease")
    inspection_type = fields.Selection([
        ('move_in',    'Move-In'),
        ('move_out',   'Move-Out'),
        ('routine',    'Routine'),
        ('emergency',  'Emergency'),
    ], required=True, default='routine', tracking=True)
    date         = fields.Date("Inspection Date", default=fields.Date.today, required=True)
    inspector_id = fields.Many2one('res.users', string="Inspector")
    tenant_id    = fields.Many2one('res.partner', string="Tenant Present")
    overall_condition = fields.Selection([
        ('excellent', 'Excellent'),
        ('good',      'Good'),
        ('fair',      'Fair'),
        ('poor',      'Poor'),
    ], default='good', tracking=True)
    item_ids     = fields.One2many('estate.inspection.item', 'inspection_id', string="Checklist")
    notes        = fields.Text("General Notes")
    signed_tenant = fields.Boolean("Signed by Tenant")
    signed_landlord = fields.Boolean("Signed by Landlord/Agent")
    deduction_amount = fields.Monetary("Deposit Deduction (KES)", currency_field='currency_id')
    currency_id  = fields.Many2one('res.currency', default=lambda s: s.env.ref('base.KES'))

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name', 'New') == 'New':
                v['name'] = self.env['ir.sequence'].next_by_code('estate.inspection') or 'New'
        return super().create(vals_list)

    def action_generate_default_checklist(self):
        """Generate standard checklist items."""
        self.ensure_one()
        default_items = [
            ('Walls & Ceilings',    'Condition of walls, ceilings, paint'),
            ('Floors',              'Tiles, carpet, or wood condition'),
            ('Windows & Doors',     'Locks, hinges, glass condition'),
            ('Kitchen',             'Sink, cabinets, appliances'),
            ('Bathrooms',           'Plumbing, tiles, fixtures'),
            ('Electrical',          'Sockets, switches, lights'),
            ('Plumbing',            'Water pressure, drainage'),
            ('Compound/Garden',     'General cleanliness and condition'),
            ('Gate & Security',     'Gate, fence, CCTV'),
            ('Keys Returned',       'All keys accounted for'),
        ]
        for room, desc in default_items:
            self.env['estate.inspection.item'].create({
                'inspection_id': self.id,
                'room':          room,
                'description':   desc,
                'condition':     'good',
            })


class EstateInspectionItem(models.Model):
    _name        = 'estate.inspection.item'
    _description = 'Inspection Checklist Item'
    _order       = 'sequence, room'

    inspection_id = fields.Many2one('estate.inspection', ondelete='cascade', required=True)
    sequence      = fields.Integer(default=10)
    room          = fields.Char("Area / Room", required=True)
    description   = fields.Text("Notes / Observations")
    condition     = fields.Selection([
        ('excellent', '⭐ Excellent'),
        ('good',      '✅ Good'),
        ('fair',      '⚠️ Fair — Minor Issues'),
        ('poor',      '❌ Poor — Needs Repair'),
        ('na',        '— N/A'),
    ], default='good')
    deduction     = fields.Monetary("Deduction (KES)", currency_field='currency_id')
    currency_id   = fields.Many2one(related='inspection_id.currency_id')
    photo_ids     = fields.Many2many('ir.attachment', string="Photos")
