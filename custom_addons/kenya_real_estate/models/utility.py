from odoo import models, fields, api, _
from odoo.exceptions import UserError


class EstateUtilityMeter(models.Model):
    _name        = 'estate.utity.meter'
    _description = 'Utility Meter'
    _order       = 'property_id, utility_type'

    property_id  = fields.Many2one('estate.property', ondelete='cascade')
    unit_id      = fields.Many2one('estate.unit')
    utility_type = fields.Selection([
        ('water','Water'),('electricity','Electricity (KPLC)'),
        ('gas','Gas'),('internet','Internet'),
    ], required=True, default='water')
    meter_number = fields.Char("Meter Number")
    currency_id  = fields.Many2one('res.currency', default=lambda s: s.env.ref('base.KES'))
    tariff_rate  = fields.Float("Rate per Unit (KES)", default=70.0)
    reading_ids  = fields.One2many('estate.utility.reading', 'meter_id', string="Readings")
    active       = fields.Boolean(default=True)


class EstateUtilityReading(models.Model):
    _name        = 'estate.utility.reading'
    _description = 'Utility Reading'
    _order       = 'reading_date desc'

    meter_id     = fields.Many2one('estate.utility.meter', ondelete='cascade', required=True)
    lease_id= fields.Many2one('estate.lease')
    reading_date = fields.Date("Date", default=fields.Date.today, required=True)
    previous     = fields.Float("Previous Reading")
    current      = fields.Float("Current Reading", required=True)
    consumed     = fields.Float("Units Consumed", compute='_compute', store=True)
    currency_id  = fields.Many2one(related='meter_id.currency_id')
    amount       = fields.Monetary("Amount (KES)", currency_field='currency_id', compute='_compute', store=True)
    invoiced     s.Boolean("Invoiced", default=False)
    invoice_id   = fields.Many2one('account.move')

    @api.depends('previous','current','meter_id.tariff_rate')
    def _compute(self):
        for r in self:
            consumed = max(r.current - r.previous, 0)
            r.consumed = consumed
            r.amount   = consumed * r.meter_id.tariff_rate

    def action_create_invoice(self):
        self.ensure_one()
        if not self.lease_id:
            raise UserError(_("Link a lease before invoicing."))
        v = self.env['account.move'].create({
            'move_type':'out_invoice','partner_id':self.lease_id.tenant_id.id,
            'lease_id':self.lease_id.id,'invoice_date':self.reading_date,
            'invoice_line_ids':[(0,0,{
                'name':f"{self.meter_id.utility_type.title()} Bill — {self.reading_date.strftime('%B %Y')} — {self.consumed:.1f} units",
                'quantity':1,'price_unit':self.amount,
            })]
        })
        self.write({'invoiced':True,'invoice_id':inv.id})
     return {'type':'ir.actions.act_window','res_model':'account.move','res_id':inv.id,'view_mode':'form'}
