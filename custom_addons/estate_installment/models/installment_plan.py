"""
Estate Installment Plan
=======================
Off-plan property payment schedule.
One plan per property sale. Lines = milestones.
"""
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class EstateInstallmentPlan(models.Model):
    _name        = 'estate.installment.plan'
    _description = 'Property Installment Plan'
    _inherit     = ['mail.thread', 'mail.activity.mixin']
    _order       = 'date_created desc'
    _rec_name    = 'name'

    name         = fields.Char('Plan Ref', readonly=True, copy=False, default='New')
    property_id  = fields.Many2one('estate.property', string='Property', required=True, tracking=True)
    partner_id   = fields.Many2one('res.partner', string='Buyer', required=True, tracking=True)
    sale_id      = fields.Many2one('estate.property.sale', string='Sale Record')
    currency_id  = fields.Many2one('res.currency', default=lambda s: s.env.ref('base.KES'))

    total_price      = fields.Monetary('Total Sale Price (KES)', currency_field='currency_id', required=True, tracking=True)
    discount_pct     = fields.Float('Discount (%)', default=0)
    net_price        = fields.Monetary('Net Price (KES)', currency_field='currency_id', compute='_compute_totals', store=True)
    total_scheduled  = fields.Monetary('Total Scheduled', currency_field='currency_id', compute='_compute_totals', store=True)
    total_invoiced   = fields.Monetary('Total Invoiced', currency_field='currency_id', compute='_compute_totals', store=True)
    total_paid       = fields.Monetary('Total Paid', currency_field='currency_id', compute='_compute_totals', store=True)
    total_overdue    = fields.Monetary('Total Overdue', currency_field='currency_id', compute='_compute_totals', store=True)
    balance_remaining= fields.Monetary('Balance Remaining', currency_field='currency_id', compute='_compute_totals', store=True)
    collection_rate  = fields.Float('Collection Rate (%)', compute='_compute_totals', store=True)
    completion_pct   = fields.Float('Plan Completion (%)', compute='_compute_totals', store=True)

    date_created = fields.Date('Plan Date', default=fields.Date.today, required=True)
    date_handover= fields.Date('Expected Handover', tracking=True)
    status       = fields.Selection([
        ('draft',     'Draft'),
        ('active',    'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], default='draft', tracking=True, string='Status')

    line_ids     = fields.One2many('estate.installment.line', 'plan_id', string='Milestones')
    notes        = fields.Text('Notes')

    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'Plan reference must be unique.'),
    ]

    @api.depends('total_price', 'discount_pct', 'line_ids.amount',
                 'line_ids.amount_invoiced', 'line_ids.amount_paid',
                 'line_ids.state', 'line_ids.due_date')
    def _compute_totals(self):
        today = fields.Date.today()
        for p in self:
            p.net_price       = p.total_price * (1 - p.discount_pct / 100)
            lines             = p.line_ids
            p.total_scheduled = sum(lines.mapped('amount'))
            p.total_invoiced  = sum(lines.mapped('amount_invoiced'))
            p.total_paid      = sum(lines.mapped('amount_paid'))
            p.total_overdue   = sum(
                l.amount - l.amount_paid
                for l in lines
                if l.due_date and l.due_date < today and l.state not in ('paid',)
            )
            p.balance_remaining = p.net_price - p.total_paid
            p.collection_rate   = round(p.total_paid / p.net_price * 100, 1) if p.net_price else 0.0
            done = sum(1 for l in lines if l.state == 'paid')
            p.completion_pct = round(done / len(lines) * 100, 1) if lines else 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name', 'New') == 'New':
                v['name'] = self.env['ir.sequence'].next_by_code('estate.installment.plan') or 'New'
        return super().create(vals_list)

    def action_activate(self):
        for p in self:
            if not p.line_ids:
                raise UserError(_('Add at least one milestone before activating.'))
            total = sum(p.line_ids.mapped('percentage'))
            if abs(total - 100.0) > 0.01:
                raise UserError(_('Milestone percentages must sum to 100%%. Currently: %.1f%%') % total)
            p.status = 'active'
            p.message_post(body=_('Installment plan activated.'))

    def action_complete(self):
        for p in self:
            p.status = 'completed'
            p.message_post(body=_('Installment plan marked completed.'))

    def action_cancel(self):
        for p in self:
            p.status = 'cancelled'
            p.message_post(body=_('Installment plan cancelled.'))

    def action_generate_invoices(self):
        """Generate invoices for all due/uninvoiced milestones."""
        self.ensure_one()
        invoiced = 0
        for line in self.line_ids.filtered(lambda l: l.state in ('pending', 'due') and not l.invoice_id):
            line._create_invoice()
            invoiced += 1
        if invoiced:
            self.message_post(body=_('%d invoice(s) generated.') % invoiced)
        return {'type': 'ir.actions.act_window_close'}
