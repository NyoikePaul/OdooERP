"""
Estate Installment Line (Milestone)
====================================
One line = one payment milestone on the plan.
e.g. Booking Deposit 10%, Foundation 20%, Roofing 30%, Handover 40%
"""
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta
import logging
_logger = logging.getLogger(__name__)


class EstateInstallmentLine(models.Model):
    _name        = 'estate.installment.line'
    _description = 'Installment Milestone'
    _order       = 'sequence, due_date'

    plan_id      = fields.Many2one('estate.installment.plan', ondelete='cascade', required=True)
    sequence     = fields.Integer('Seq', default=10)
    name         = fields.Char('Milestone', required=True)
    milestone_type = fields.Selection([
        ('booking',      'Booking Deposit'),
        ('foundation',   'Foundation'),
        ('slab',         'Slab / Floor'),
        ('walling',      'Walling'),
        ('roofing',      'Roofing'),
        ('finishing',    'Finishing'),
        ('handover',     'Handover Balance'),
        ('custom',       'Custom Milestone'),
    ], string='Type', default='custom', required=True)

    percentage      = fields.Float('% of Total', required=True)
    amount          = fields.Monetary('Amount (KES)', currency_field='currency_id', compute='_compute_amount', store=True)
    currency_id     = fields.Many2one(related='plan_id.currency_id')
    due_date        = fields.Date('Due Date')
    grace_days      = fields.Integer('Grace Days', default=7)

    state           = fields.Selection([
        ('draft',   'Not Started'),
        ('pending', 'Pending'),
        ('due',     'Due'),
        ('invoiced','Invoiced'),
        ('paid',    'Paid'),
        ('overdue', 'Overdue'),
    ], default='draft', string='Status', compute='_compute_state', store=True)

    invoice_id      = fields.Many2one('account.move', string='Invoice', readonly=True)
    amount_invoiced = fields.Monetary('Invoiced', currency_field='currency_id', compute='_compute_amounts', store=True)
    amount_paid     = fields.Monetary('Paid', currency_field='currency_id', compute='_compute_amounts', store=True)
    amount_due      = fields.Monetary('Outstanding', currency_field='currency_id', compute='_compute_amounts', store=True)

    notes           = fields.Char('Notes')

    @api.depends('plan_id.net_price', 'percentage')
    def _compute_amount(self):
        for l in self:
            l.amount = l.plan_id.net_price * l.percentage / 100 if l.plan_id else 0.0

    @api.depends('invoice_id', 'invoice_id.payment_state', 'invoice_id.amount_total',
                 'invoice_id.amount_residual')
    def _compute_amounts(self):
        for l in self:
            inv = l.invoice_id
            if inv:
                l.amount_invoiced = inv.amount_total
                l.amount_paid     = inv.amount_total - inv.amount_residual
                l.amount_due      = inv.amount_residual
            else:
                l.amount_invoiced = l.amount_paid = l.amount_due = 0.0

    @api.depends('due_date', 'grace_days', 'invoice_id', 'invoice_id.payment_state', 'plan_id.status')
    def _compute_state(self):
        today = fields.Date.today()
        for l in self:
            if l.plan_id.status == 'draft':
                l.state = 'draft'
                continue
            inv = l.invoice_id
            if inv and inv.payment_state == 'paid':
                l.state = 'paid'
            elif inv:
                deadline = l.due_date + timedelta(days=l.grace_days) if l.due_date else None
                l.state = 'overdue' if (deadline and today > deadline) else 'invoiced'
            elif l.due_date and today > l.due_date + timedelta(days=l.grace_days):
                l.state = 'overdue'
            elif l.due_date and today >= l.due_date:
                l.state = 'due'
            else:
                l.state = 'pending'

    def _create_invoice(self):
        """Create an Odoo invoice for this milestone."""
        self.ensure_one()
        if self.invoice_id:
            raise UserError(_('Invoice already exists for milestone: %s') % self.name)
        plan = self.plan_id
        move = self.env['account.move'].create({
            'move_type':       'out_invoice',
            'partner_id':      plan.partner_id.id,
            'invoice_date':    fields.Date.today(),
            'invoice_date_due': self.due_date,
            'ref':             f'{plan.name} — {self.name}',
            'invoice_line_ids': [(0, 0, {
                'name':        f'{plan.property_id.name}: {self.name} ({self.percentage:.0f}%)',
                'quantity':    1,
                'price_unit':  self.amount,
            })],
        })
        self.invoice_id = move
        _logger.info('Created invoice %s for milestone %s', move.name, self.name)
        return move

    def action_create_invoice(self):
        inv = self._create_invoice()
        return {
            'type':      'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id':    inv.id,
            'view_mode': 'form',
        }

    def action_view_invoice(self):
        self.ensure_one()
        return {
            'type':      'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id':    self.invoice_id.id,
            'view_mode': 'form',
        }
