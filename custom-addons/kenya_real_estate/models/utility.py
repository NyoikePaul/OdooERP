from odoo import models, fields, api, _
from odoo.exceptions import UserError


class EstateUtilityMeter(models.Model):
    _name        = 'estate.utility.meter'
    _description = 'Utility Meter'
    _order       = 'property_id, utility_type'

    property_id  = fields.Many2one('estate.property', string="Property",
                                   ondelete='cascade')
    unit_id      = fields.Many2one('estate.unit', string="Unit")
    utility_type = fields.Selection([
        ('water',       'Water'),
        ('electricity', 'Electricity (KPLC)'),
        ('gas',         'Gas'),
        ('internet',    'Internet'),
    ], required=True, default='water')
    meter_number = fields.Char("Meter Number")
    tariff_rate  = fields.Float("Rate per Unit (KES)", default=70.0)
    currency_id  = fields.Many2one('res.currency', default=lambda s: s.env.ref('base.KES'))
    reading_ids  = fields.One2many('estate.utility.reading', 'meter_id', string="Readings")
    active       = fields.Boolean(default=True)


class EstateUtilityReading(models.Model):
    _name        = 'estate.utility.reading'
    _description = 'Utility Meter Reading'
    _order       = 'reading_date desc'

    meter_id     = fields.Many2one('estate.utility.meter', ondelete='cascade', required=True)
    lease_id     = fields.Many2one('estate.lease', string="Lease / Tenant")
    reading_date = fields.Date("Reading Date", default=fields.Date.today, required=True)
    previous     = fields.Float("Previous Reading")
    current      = fields.Float("Current Reading", required=True)
    consumed     = fields.Float("Units Consumed", compute='_compute_consumed', store=True)
    amount       = fields.Monetary("Amount (KES)", currency_field='currency_id',
                                   compute='_compute_consumed', store=True)
    currency_id  = fields.Many2one(related='meter_id.currency_id')
    invoiced     = fields.Boolean("Invoiced", default=False)
    invoice_id   = fields.Many2one('account.move', string="Invoice")
    notes        = fields.Char("Notes")

    @api.depends('previous', 'current', 'meter_id.tariff_rate')
    def _compute_consumed(self):
        for rec in self:
            consumed = max(rec.current - rec.previous, 0)
            rec.consumed = consumed
            rec.amount   = consumed * rec.meter_id.tariff_rate

    def action_create_invoice(self):
        self.ensure_one()
        if not self.lease_id:
            raise UserError(_("Please link a lease/tenant before invoicing."))
        inv = self.env['account.move'].create({
            'move_type':  'out_invoice',
            'partner_id': self.lease_id.tenant_id.id,
            'lease_id':   self.lease_id.id,
            'invoice_date': self.reading_date,
            'invoice_line_ids': [(0, 0, {
                'name': (f"{self.meter_id.utility_type.capitalize()} Bill — "
                         f"{self.reading_date.strftime('%B %Y')} — "
                         f"{self.consumed:.1f} units"),
                'quantity':   1,
                'price_unit': self.amount,
            })]
        })
        self.write({'invoiced': True, 'invoice_id': inv.id})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': inv.id,
            'view_mode': 'form',
        }
