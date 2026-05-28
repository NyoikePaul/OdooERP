"""
Generator Management — Kenya Critical Feature
Most apartment blocks and commercial buildings have standby generators.
Fuel costs are shared among tenants via service charges or direct billing.
"""
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class EstateGenerator(models.Model):
    _name        = 'estate.generator'
    _description = 'Standby Generator'
    _inherit     = ['mail.thread']

    name          = fields.Char("Generator Name", required=True)
    building_id   = fields.Many2one('estate.building', string="Building")
    property_id   = fields.Many2one('estate.property', string="Property")
    make_model    = fields.Char("Make / Model", placeholder="e.g. Cummins 100KVA")
    serial_number = fields.Char("Serial Number")
    capacity_kva  = fields.Float("Capacity (KVA)")
    fuel_type     = fields.Selection([
        ('diesel', 'Diesel'),
        ('petrol', 'Petrol'),
        ('gas',    'LPG Gas'),
    ], default='diesel')
    fuel_consumption_per_hour = fields.Float("Fuel Consumption (L/hr)", default=8.0)

    currency_id     = fields.Many2one('res.currency',
                                       default=lambda s: s.env.ref('base.KES'))
    fuel_price_per_litre = fields.Monetary("Fuel Price/Litre (KES)",
                                            currency_field='currency_id', default=165.0)
    last_service_date = fields.Date("Last Service Date")
    next_service_date = fields.Date("Next Service Date")
    service_interval_hours = fields.Integer("Service Every (hours)", default=250)

    log_ids          = fields.One2many('estate.generator.log', 'generator_id',
                                       string="Usage Logs")
    active           = fields.Boolean(default=True)

    total_hours_ytd  = fields.Float(compute='_compute_ytd', store=True, string="Hours YTD")
    total_fuel_ytd   = fields.Float(compute='_compute_ytd', store=True, string="Fuel Used YTD (L)")
    total_cost_ytd   = fields.Monetary(compute='_compute_ytd', store=True,
                                        currency_field='currency_id', string="Cost YTD (KES)")

    @api.depends('log_ids.hours_run', 'log_ids.fuel_used', 'log_ids.cost', 'log_ids.date')
    def _compute_ytd(self):
        from datetime import date
        year_start = date.today().replace(month=1, day=1)
        for rec in self:
            ytd_logs = rec.log_ids.filtered(lambda l: l.date >= year_start)
            rec.total_hours_ytd = sum(ytd_logs.mapped('hours_run'))
            rec.total_fuel_ytd  = sum(ytd_logs.mapped('fuel_used'))
            rec.total_cost_ytd  = sum(ytd_logs.mapped('cost'))


class EstateGeneratorLog(models.Model):
    _name        = 'estate.generator.log'
    _description = 'Generator Usage Log'
    _order       = 'date desc'

    generator_id = fields.Many2one('estate.generator', ondelete='cascade', required=True)
    date         = fields.Date("Date", required=True, default=fields.Date.today)
    hours_run    = fields.Float("Hours Run", required=True)
    fuel_used    = fields.Float("Fuel Used (L)", compute='_compute_cost', store=True)
    fuel_added   = fields.Float("Fuel Added (L)")
    cost         = fields.Monetary("Cost (KES)", currency_field='currency_id',
                                    compute='_compute_cost', store=True)
    currency_id  = fields.Many2one(related='generator_id.currency_id')
    notes        = fields.Char("Notes")

    @api.depends('hours_run', 'generator_id.fuel_consumption_per_hour',
                 'generator_id.fuel_price_per_litre')
    def _compute_cost(self):
        for rec in self:
            consumed    = rec.hours_run * rec.generator_id.fuel_consumption_per_hour
            rec.fuel_used = consumed
            rec.cost      = consumed * rec.generator_id.fuel_price_per_litre

    def action_bill_tenants(self):
        """Apportion generator cost among active leases in building."""
        self.ensure_one()
        building   = self.generator_id.building_id
        if not building:
            raise UserError(_("Generator must be linked to a building to bill tenants."))
        active_units = building.unit_ids.filtered(lambda u: u.status == 'leased')
        if not active_units:
            raise UserError(_("No active leased units in this building."))
        share = self.cost / len(active_units)
        invoices = []
        for unit in active_units:
            if not unit.tenant_id:
                continue
            lease = self.env['estate.lease'].search([
                ('unit_id', '=', unit.id),
                ('status', '=', 'active'),
            ], limit=1)
            if not lease:
                continue
            inv = self.env['account.move'].create({
                'move_type':    'out_invoice',
                'partner_id':   unit.tenant_id.id,
                'lease_id':     lease.id,
                'invoice_date': self.date,
                'invoice_line_ids': [(0, 0, {
                    'name': (f"Generator Fuel Cost — {self.date.strftime('%d %b %Y')} — "
                             f"{self.generator_id.name} — {self.hours_run:.1f} hrs "
                             f"({len(active_units)} units)"),
                    'quantity':   1,
                    'price_unit': share,
                })]
            })
            invoices.append(inv.id)
        return {
            'type':      'ir.actions.act_window',
            'name':      'Generator Bills',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain':    [('id', 'in', invoices)],
        }
