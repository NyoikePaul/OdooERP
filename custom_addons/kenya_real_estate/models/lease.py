from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class EstateLease(models.Model):
    _name = 'estate.lease'
    _description = 'Property Lease / Tenancy Agreement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc'

    # ── Identity ──────────────────────────────────────
    name        = fields.Char("Lease Ref", readonly=True, copy=False, default='New')
    property_id = fields.Many2one('estate.property', string="Property",
                                  required=True, ondelete='restrict', tracking=True)
    tenant_id   = fields.Many2one('res.partner', string="Tenant",
                                  required=True, tracking=True)

    # ── Dates ─────────────────────────────────────────
    date_start      = fields.Date("Start Date",  required=True)
    date_end        = fields.Date("End Date",    required=True)
    notice_period   = fields.Integer("Notice Period (days)", default=30)
    notice_given    = fields.Boolean("Notice Given", tracking=True)
    notice_date     = fields.Date("Notice Date")

    # ── Financials ────────────────────────────────────
    monthly_rent = fields.Monetary("Monthly Rent (KES)", currency_field='currency_id',
                                   related='property_id.monthly_rent', readonly=False, store=True)
    currency_id  = fields.Many2one('res.currency', default=lambda s: s.env.ref('base.KES'))
    deposit      = fields.Monetary("Security Deposit (KES)", currency_field='currency_id')
    deposit_paid = fields.Boolean("Deposit Paid", tracking=True)
    penalty_rate = fields.Float("Late Payment Penalty (%)", default=5.0)

    # ── Status ────────────────────────────────────────
    status = fields.Selection([
        ('draft',    'Draft'),
        ('active',   'Active'),
        ('expired',  'Expired'),
        ('renewed',  'Renewed'),
        ('cancelled','Cancelled'),
    ], default='draft', tracking=True)

    # ── Relations ─────────────────────────────────────
    payment_ids    = fields.One2many('account.move', 'lease_id', string="Rent Invoices")
    renewal_ids    = fields.One2many('estate.lease', 'parent_lease_id', string="Renewals")
    parent_lease_id = fields.Many2one('estate.lease', string="Renewed From", ondelete='set null')
    notes          = fields.Text("Notes")

    # ── Computed ──────────────────────────────────────
    payment_count       = fields.Integer(compute='_compute_financials', store=True)
    total_paid          = fields.Monetary(compute='_compute_financials',
                                          currency_field='currency_id', store=True)
    total_outstanding   = fields.Monetary(compute='_compute_financials',
                                          currency_field='currency_id', store=True)
    days_to_expiry      = fields.Integer(compute='_compute_expiry', store=True)
    is_expiring_soon    = fields.Boolean(compute='_compute_expiry', store=True)
    duration_months     = fields.Integer(compute='_compute_duration', store=True)

    # ── Compute Methods ───────────────────────────────
    @api.depends('payment_ids', 'payment_ids.payment_state', 'payment_ids.amount_total')
    def _compute_financials(self):
        for rec in self:
            invoices = rec.payment_ids.filtered(lambda i: i.move_type == 'out_invoice')
            rec.payment_count     = len(invoices)
            rec.total_paid        = sum(i.amount_total for i in invoices
                                        if i.payment_state == 'paid')
            rec.total_outstanding = sum(i.amount_residual for i in invoices
                                        if i.payment_state != 'paid')

    @api.depends('date_end', 'status')
    def _compute_expiry(self):
        today = fields.Date.today()
        for rec in self:
            if rec.date_end and rec.status == 'active':
                delta = (rec.date_end - today).days
                rec.days_to_expiry   = delta
                rec.is_expiring_soon = 0 <= delta <= 30
            else:
                rec.days_to_expiry   = 0
                rec.is_expiring_soon = False

    @api.depends('date_start', 'date_end')
    def _compute_duration(self):
        for rec in self:
            if rec.date_start and rec.date_end:
                diff = relativedelta(rec.date_end, rec.date_start)
                rec.duration_months = diff.years * 12 + diff.months
            else:
                rec.duration_months = 0

    # ── Constraints ───────────────────────────────────
    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_end <= rec.date_start:
                raise ValidationError("End date must be after start date.")

    @api.constrains('property_id', 'date_start', 'date_end', 'status')
    def _check_no_overlap(self):
        for rec in self:
            if rec.status not in ('active', 'draft'):
                continue
            overlap = self.search([
                ('property_id', '=', rec.property_id.id),
                ('status', 'in', ('active', 'draft')),
                ('id', '!=', rec.id),
                ('date_start', '<', rec.date_end),
                ('date_end',   '>',  rec.date_start),
            ])
            if overlap:
                raise ValidationError(
                    f"Property '{rec.property_id.name}' already has an overlapping "
                    f"lease: {overlap[0].name}"
                )

    # ── Actions ───────────────────────────────────────
    def action_activate(self):
        for rec in self:
            rec.write({'status': 'active'})
            rec.property_id.write({'status': 'leased'})
            rec.message_post(body=f"Lease activated. Tenant: {rec.tenant_id.name}")

    def action_cancel(self):
        for rec in self:
            rec.write({'status': 'cancelled'})
            active_leases = self.search([
                ('property_id', '=', rec.property_id.id),
                ('status', '=', 'active'),
                ('id', '!=', rec.id),
            ])
            if not active_leases:
                rec.property_id.write({'status': 'available'})

    def action_expire(self):
        for rec in self:
            rec.write({'status': 'expired'})
            rec.property_id.write({'status': 'available'})
            rec.message_post(body="Lease expired.")

    def action_generate_rent_invoice(self):
        self.ensure_one()
        invoice = self.env['account.move'].create({
            'move_type':      'out_invoice',
            'partner_id':     self.tenant_id.id,
            'lease_id':       self.id,
            'invoice_date':   fields.Date.today(),
            'invoice_date_due': fields.Date.today() + relativedelta(days=5),
            'invoice_line_ids': [(0, 0, {
                'name': (f'Rent — {self.property_id.name} '
                         f'({fields.Date.today().strftime("%B %Y")})'),
                'quantity': 1,
                'price_unit': self.monthly_rent,
            })]
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
        }

    def action_renew(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Renew Lease',
            'res_model': 'estate.lease.renewal.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_lease_id':   self.id,
                'default_tenant_id':  self.tenant_id.id,
                'default_property_id': self.property_id.id,
                'default_monthly_rent': self.monthly_rent,
                'default_new_start': self.date_end + relativedelta(days=1),
                'default_new_end': self.date_end + relativedelta(years=1),
            }
        }

    # ── Scheduled Actions ─────────────────────────────
    @api.model
    def _cron_expire_leases(self):
        """Auto-expire leases past their end date."""
        today = fields.Date.today()
        expired = self.search([
            ('status', '=', 'active'),
            ('date_end', '<', today),
        ])
        for lease in expired:
            lease.action_expire()
            lease.message_post(
                body=f"Lease auto-expired on {today}. Property set to available."
            )
        _logger.info("Auto-expired %d leases.", len(expired))

    @api.model
    def _cron_expiry_reminders(self):
        """Send reminders for leases expiring in 30 and 7 days."""
        today = fields.Date.today()
        for days in (30, 7):
            target_date = today + relativedelta(days=days)
            leases = self.search([
                ('status', '=', 'active'),
                ('date_end', '=', target_date),
            ])
            for lease in leases:
                lease.message_post(
                    body=(
                        f"⚠️ Lease Expiry Reminder: This lease expires in {days} days "
                        f"on {lease.date_end}. "
                        f"Tenant: {lease.tenant_id.name}. "
                        f"Monthly Rent: KES {lease.monthly_rent:,.0f}."
                    ),
                    subtype_xmlid='mail.mt_note',
                    partner_ids=[lease.tenant_id.id, lease.property_id.landlord_id.id],
                )
        _logger.info("Expiry reminders sent.")

    def action_open_invoices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Rent Invoices',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('lease_id', '=', self.id)],
            'context': {'default_lease_id': self.id},
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('estate.lease') or 'New'
        return super().create(vals_list)
