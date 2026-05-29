from odoo import models, fields, api, _


class EstateInspection(models.Model):
    _name        = 'estate.inspection'
    _description = 'Property Inspection Report'
    _inherit     = ['mail.thread', 'mail.activity.mixin']
    _order       = 'date desc'

    name         = fields.Char("Report Ref", readonly=True, cFalse, default='New')
    property_id  = fields.Many2one('estate.property', required=True, ondelete='restrict')
    unit_id      = fields.Many2one('estate.unit')
    lease_id     = fields.Many2one('estate.lease')
    inspection_type = fields.Selection([
        ('move_in','Move-In'),('move_out','Move-Out'),
        ('routine','Routine'),('emergency','Emergency'),
    ], required=True, default='routine', tracking=True)
    date         = fields.Date("Date", default=fields.Date.today, required=True)
    insper_id = fields.Many2one('res.users', string="Inspector")
    tenant_id    = fields.Many2one('res.partner', string="Tenant Present")
    overall      = fields.Selection([('excellent','Excellent'),('good','Good'),
                                      ('fair','Fair'),('poor','Poor')], default='good')
    item_ids     = fields.One2many('estate.inspection.item', 'inspection_id', string="Checklist")
    signed_tenant   = fields.Boolean("Signed by Tenant")
    signed_landlord = fields.Boolean("Signed by Landlord")   currency_id  = fields.Many2one('res.currency', default=lambda s: s.env.ref('base.KES'))
    deduction    = fields.Monetary("Total Deduction (KES)", currency_field='currency_id')
    notes        = fields.Text("Notes")

    def action_generate_checklist(self):
        self.ensure_one()
        items = [
            ('Walls & Ceilings','Condition, cracks, paint'),
            ('Floors','Tiles, carpet, condition'),
            ('Windows & Doors','Locks, glass, hinges'),
            ('Kitchen','Sink, cabinetiances'),
            ('Bathrooms','Plumbing, fixtures, tiles'),
            ('Electrical','Sockets, switches, lights'),
            ('Plumbing','Water pressure, drainage'),
            ('Compound','Cleanliness, condition'),
            ('Security','Gate, locks, CCTV'),
            ('Keys','All keys returned/issued'),
        ]
        for room, desc in items:
            self.env['estate.inspection.item'].create({
                'inspection_id':self.id,'room':room,
                'description':desc,'condition':'good',
            })

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name','New')=='New':
                v['name'] = self.env['ir.sequence'].next_by_code('estate.inspection') or 'New'
        return super().create(vals_list)


class EstateInspectionItem(models.Model):
    _name    = 'estate.inspection.item'
    _description = 'Inspection Checklist Item'
    _order   = 'sequence, room'

    inspection_id = fields.Many2one('estate.ition', ondelete='cascade', required=True)
    sequence      = fields.Integer(default=10)
    room          = fields.Char("Area", required=True)
    description   = fields.Text("Observations")
    condition     = fields.Selection([
        ('excellent','⭐ Excellent'),('good','✅ Good'),
        ('fair','⚠️ Fair'),('poor','❌ Poor'),('na','N/A'),
    ], default='good')
    currency_id   = fields.Many2one(related='inspection_id.currency_id')
    deduction     = fields.Monetary("Deduction (KES)", currenield='currency_id')
