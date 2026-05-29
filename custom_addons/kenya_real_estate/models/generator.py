from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class EstateGenerator(models.Model):
    _name        = 'estate.generator'
    _description = 'Standby Generator'
    _inherit     = ['mail.thread']

    name               = fields.Char("Generator Name", required=True)
    building_id        = fields.Many2one('estate.building')
    property_id        = fields.Many2one('estate.property')
    make_model         = fields.Char("Make / Model")
    capacity_kva       = fields.Float("Capacity (KVA)")
    fuel_type          = fields.Selection([('diesel','Diesel'),('petrol','Petrol')], default='diesel')
    fuel_litres_per_hr = fields.Float("Litres/Hour", default=8.0)
    currency_id        = fields.Many2one('res.currency', default=lambda s: s.env.ref('base.KES'))
    fuel_price_litre   = fields.Monetary("Fuel Price/Litre (KES)", currency_field='currency_id', default=165.0)
    next_service_date  = fields.Date("Next Service Date")
    log_ids            = fields.One2many('estate.generator.log', 'generator_id', string="Usage Logs")
    active             = fields.Boolean(default=True)
    total_cost_ytd     = fields.Monetary("Cost YTD (KES)", currency_field='currency_id',
                                          compute='_compute_ytd', store=True)

    @api.depends('log_ids.cost', 'log_ids.date')
    def _compute_ytd(self):
        from datetime import date
        yr = date.today().replace(month=1,day=1)
        for r in self:
            r.total_cost_ytd = sum(r.log_ids.filtered(lambda l: l.date >= yr).mapped('cost'))


class EstateGeneratorLog(models.Model):
    _name        = 'estate.generator.log'
    _description = 'Generator Usage Log'
    _order       = 'date desc'

    generator_id  = fields.Many2one('estate.generator', ondelete='cascade', required=True)
    date          = fields.Date("Date", default=fields.Date.today, required=True)
    hours_run     = fields.Float("Hours Run", required=True)
    fuel_used     = fields.Float("Fuel Used (L)", compute='_compute', store=True)
    fuel_added    = fields.Float("Fuel Added (L)")
    currency_id   = fields.Many2one(related='generator_id.currency_id')
    cost          = fields.Monetary("Cost (KES)", currency_field='currency_id', compute='_compute', store=True)
    notes         = fields.Char()

    @api.depends('hours_run','generator_id.fuel_litres_per_hr','generator_id.fuel_price_litre')
    def _compute(self):
        for r in self:
            r.fuel_used = r.hours_run * r.generator_id.fuel_litres_per_hr
            r.cost      = r.fuel_used * r.generator_id.fuel_price_litre

    def action_bill_tenants(self):
        self.ensure_one()
        building = self.generator_id.building_id
        if not building:
            raise UserError(_("Generator must be linked to a building."))
        active_units = building.unit_ids.filtered(lambda u: u.status == 'leased')
        if not active_units:
            raise UserError(_("No leased units in this building."))
        share = self.cost / len(active_units)
        invoices = []
        for unit in active_units:
            lease = self.env['estate.lease'].search([
                ('unit_id','=',unit.id),('status','=','active')], limit=1)
            if not lease:
                continue
            inv = self.env['account.move'].create({
                'move_type':'out_invoice','partner_id':unit.tenant_id.id,
                'lease_id':lease.id,'invoice_date':self.date,
                'invoice_line_ids':[(0,0,{
                    'name':f"Generator Fuel — {self.date.strftime('%d %b %Y')} — {self.hours_run:.1f}hrs ({len(active_units)} units)",
                    'quantity':1,'price_unit':share,
                })]
            })
            invoices.append(inv.id)
        return {'type':'ir.actions.act_window','name':'Generator Bills',
                'res_model':'account.move','view_mode':'list,form','domain':[('id','in',invoices)]}
