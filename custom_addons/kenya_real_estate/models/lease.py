from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class EstateLease(models.Model):
    _name        = 'estate.lease'
    _description = 'Property Lease / Tenancy Agreement'
    _inherit     = ['mail.thread', 'mail.activity.mixin']
    _order       = 'date_start desc'

    # ── Identity ──────────────────────────────────────
    name             = fields.Char("Lease Ref", readonly=True,
                                   copy=False, default='New')
    property_id      = fields.Many2one('estate.property', string="Property",
                                       required=True, ondelete='restrict',
                                       tracking=True)
    unit_id          = fields.Many2one('estate.unit', string="Unit",
                                       ondelete='set null', tracking=True)
    tenant_id        = fields.Many2one('res.partner', string="Tenant",
                                       required=True, tracking=True)
    parent_lease_id  = fields.Many2one('estate.lease', string="Renewed From",
                                       ondelete='set null')
    renewal_ids      = fields.One2many('estate.lease', 'parent_lease_id',
                                       string="Renewals")

    # ── Lease Terms ───────────────────────────────────
    date_start       = fields.Date("Start Date",  required=True)
    date_end         = fields.Date("End Date",    required=True)
    notice_period    = fields.Integer("Notice Period (days)", default=30)
    notice_given     = fields.Boolean("Notice Given", tracking=True)
    notice_date      = fields.Date("Notice Date")
    break_clause     = fields.Boolean("Break Clause Allowed",
                                      help="Tenant can exit before end date with penalty")
    break_clause_months = fields.Integer("Break After (months)", default=6)
    subletting_allowed = fields.Boolean("Subletting Allowed", default=False)
    subletting_ref   = fields.Char("Subletting Reference")

    # ── Financials ────────────────────────────────────
    currency_id      = fields.Many2one('res.currency',
                                       default=lambda s: s.env.ref('base.KES'))
    monthly_rent     = fields.Monetary("Monthly Rent (KES)",
                                       currency_field='currency_id',
                                       related='property_id.monthly_rent',
                                       readonly=False, store=True)
    service_charge   = fields.Monetary("Service Charge (KES/mo)",
                                       currency_field='currency_id')
    deposit          = fields.Monetary("Security Deposit (KES)",
                                       currency_field='currency_id')
    deposit_paid     = fields.Boolean("Deposit Paid", tracking=True)
    deposit_mpesa    = fields.Char("Deposit M-Pesa Receipt")

    # ── KRA Tax ───────────────────────────────────────
    apply_wht        = fields.Boolean("Apply Withholding Tax",
                                      default=True,
                                      help="KRA WHT: 5% residential / 10% commercial")
    wht_rate         = fields.Float("WHT Rate (%)",
                                    compute='_compute_wht_rate', store=True)
    wht_amount       = fields.Monetary("WHT Amount (KES/mo)",
                                       currency_field='currency_id',
                                       compute='_compute_wht_rate', store=True)
    landlord_payout  = fields.Monetary("Landlord Payout (KES/mo)",
                                       currency_field='currency_id',
                                       compute='_compute_wht_rate', store=True)

    # ── Escalation ────────────────────────────────────
    escalation_rate  = fields.Float("Annual Escalation (%)", default=10.0)
    next_review_date = fields.Date("Next Rent Review Date")
    auto_escalate    = fields.Boolean("Auto-Apply Escalation on Review Date",
                                      default=False)
    escalation_history = fields.Text("Escalation History", readonly=True)

    # ── Penalties ─────────────────────────────────────
    penalty_rate     = fields.Float("Late Payment Penalty (%)", default=5.0)
    grace_days       = fields.Integer("Grace Period (days)", default=5)

    # ── Status ────────────────────────────────────────
    status = fields.Selection([
        ('draft',     'Draft'),
        ('active',    'Active'),
        ('expired',   'Expired'),
        ('renewed',   'Renewed'),
        ('cancelled', 'Cancelled'),
        ('surrendered','Surrendered'),
    ], default='draft', tracking=True)

    # ── Relations ─────────────────────────────────────
    payment_ids      = fields.One2many('account.move', 'lease_id',
                                       string="Invoices")
    notes            = fields.Text("Notes / Special Conditions")

    # ── Computed ──────────────────────────────────────
    payment_count    = fields.Integer(compute='_compute_financials', store=True)
    total_invoiced   = fields.Monetary(compute='_compute_financials',
                                       currency_field='currency_id', store=True)
    total_paid       = fields.Monetary(compute='_compute_financials',
                                       currency_field='currency_id', store=True)
    total_outstanding = fields.Monetary(compute='_compute_financials',
                                        currency_field='currency_id', store=True)
    months_outstanding = fields.Integer(compute='_compute_financials', store=True,
                                        string="Months in Arrears")
    days_to_expiry   = fields.Integer(compute='_compute_expiry', store=True)
    is_expiring_soon = fields.Boolean(compute='_compute_expiry', store=True)
    duration_months  = fields.Integer(compute='_compute_duration', store=True)
    total_lease_value = fields.Monetary(compute='_compute_duration',
                                        currency_field='currency_id', store=True)

    # ═══════════════ COMPUTE METHODS ════════════════ #


    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'Lease reference must be unique.'),
        ('rent_positive', 'CHECK(monthly_rent >= 0)', 'Monthly rent cannot be negative.'),
        ('deposit_positive', 'CHECK(deposit >= 0)', 'Deposit cannot be negative.'),
        ('penalty_rate_valid', 'CHECK(penalty_rate >= 0 AND penalty_rate <= 100)', 'Penalty rate must be between 0 and 100%.'),
    ]

    @api.depends('property_id.property_type', 'monthly_rent', 'apply_wht')
    def _compute_wht_rate(self):
        for rec in self:
            if rec.apply_wht:
                rate = 10.0 if rec.property_id.property_type == 'commercial' else 5.0
            else:
                rate = 0.0
            rec.wht_rate       = rate
            rec.wht_amount     = rec.monthly_rent * rate / 100
            rec.landlord_payout = rec.monthly_rent - rec.wht_amount

    @api.depends(
        'payment_ids.payment_state',
        'payment_ids.amount_total',
        'payment_ids.amount_residual',
        'payment_ids.move_type',
    )
    def _compute_financials(self):
        for rec in self:
            rent_invs  = rec.payment_ids.filtered(
                lambda i: i.move_type == 'out_invoice'
                and not (i.ref or '').startswith('PEN/')
            )
            paid_invs  = rent_invs.filtered(lambda i: i.payment_state == 'paid')
            unpaid     = rent_invs.filtered(lambda i: i.payment_state != 'paid')

            rec.payment_count      = len(rent_invs)
            rec.total_invoiced     = sum(rent_invs.mapped('amount_total'))
            rec.total_paid         = sum(paid_invs.mapped('amount_total'))
            rec.total_outstanding  = sum(unpaid.mapped('amount_residual'))
            months_arr = (rec.total_outstanding / rec.monthly_rent) if rec.monthly_rent else 0
            rec.months_outstanding = int(months_arr)

    @api.depends('date_end', 'status')
    def _compute_expiry(self):
        today = fields.Date.today()
        for rec in self:
            if rec.date_end and rec.status == 'active':
                delta                = (rec.date_end - today).days
                rec.days_to_expiry   = delta
                rec.is_expiring_soon = 0 <= delta <= 30
            else:
                rec.days_to_expiry   = 0
                rec.is_expiring_soon = False

    @api.depends('date_start', 'date_end', 'monthly_rent', 'service_charge')
    def _compute_duration(self):
        for rec in self:
            if rec.date_start and rec.date_end:
                diff                  = relativedelta(rec.date_end, rec.date_start)
                months                = diff.years * 12 + diff.months
                rec.duration_months   = months
                rec.total_lease_value = months * (rec.monthly_rent + rec.service_charge)
            else:
                rec.duration_months   = 0
                rec.total_lease_value = 0

    # ═══════════════ CONSTRAINTS ════════════════════ #

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_end <= rec.date_start:
                raise ValidationError("End date must be after start date.")

    @api.constrains('property_id', 'unit_id', 'date_start', 'date_end', 'status')
    def _check_no_overlap(self):
        for rec in self:
            if rec.status not in ('active', 'draft'):
                continue
            domain = [
                ('status', 'in', ('active', 'draft')),
                ('id', '!=', rec.id),
                ('date_start', '<', rec.date_end),
                ('date_end',   '>', rec.date_start),
            ]
            if rec.unit_id:
                domain.append(('unit_id', '=', rec.unit_id.id))
            else:
                domain.append(('property_id', '=', rec.property_id.id))

            overlap = self.search(domain, limit=1)
            if overlap:
                raise ValidationError(
                    f"Overlapping lease found: {overlap.name} "
                    f"({overlap.date_start} → {overlap.date_end})"
                )

    # ═══════════════ WORKFLOW ACTIONS ═══════════════ #

    def action_activate(self):
        for rec in self:
            if not rec.deposit_paid and rec.deposit:
                raise UserError(
                    _("Cannot activate lease — security deposit has not been paid.\n"
                      "Mark deposit as paid first.")
                )
            rec.write({'status': 'active'})
            if rec.unit_id:
                rec.unit_id.write({'status': 'leased', 'tenant_id': rec.tenant_id.id})
            rec.property_id.write({'status': 'leased'})
            # Set next review date
            if rec.escalation_rate and not rec.next_review_date:
                rec.next_review_date = rec.date_start + relativedelta(years=1)
            rec.message_post(
                body=_(f"✅ Lease activated. Tenant: {rec.tenant_id.name}. "
                       f"Monthly Rent: KES {rec.monthly_rent:,.0f}. "
                       f"Term: {rec.date_start} → {rec.date_end}.")
            )

    def action_cancel(self):
        for rec in self:
            rec.write({'status': 'cancelled'})
            if rec.unit_id:
                rec.unit_id.write({'status': 'vacant', 'tenant_id': False})
            # Only free property if no other active leases
            other_active = self.search([
                ('property_id', '=', rec.property_id.id),
                ('status', '=', 'active'),
                ('id', '!=', rec.id),
            ])
            if not other_active:
                rec.property_id.write({'status': 'available'})
            rec.message_post(body=_("❌ Lease cancelled."))

    def action_expire(self):
        for rec in self:
            rec.write({'status': 'expired'})
            if rec.unit_id:
                rec.unit_id.write({'status': 'vacant', 'tenant_id': False})
            rec.property_id.write({'status': 'available'})
            rec.message_post(body=_("⏰ Lease expired."))

    def action_surrender(self):
        """Early lease termination / surrender."""
        for rec in self:
            rec.write({'status': 'surrendered'})
            if rec.unit_id:
                rec.unit_id.write({'status': 'vacant', 'tenant_id': False})
            rec.property_id.write({'status': 'available'})
            rec.message_post(
                body=_(f"🏳️ Lease surrendered early on {fields.Date.today()}.")
            )

    def action_renew(self):
        self.ensure_one()
        new_start = self.date_end + relativedelta(days=1)
        # Apply escalation to new rent
        escalated_rent = self.monthly_rent * (1 + self.escalation_rate / 100)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Renew Lease'),
            'res_model': 'estate.lease.renewal.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_lease_id':      self.id,
                'default_tenant_id':     self.tenant_id.id,
                'default_property_id':   self.property_id.id,
                'default_monthly_rent':  escalated_rent,
                'default_new_start':     new_start,
                'default_new_end':       new_start + relativedelta(years=1),
                'default_deposit':       self.deposit,
            }
        }

    def action_apply_escalation(self):
        """Manually apply rent escalation."""
        self.ensure_one()
        if not self.escalation_rate:
            raise UserError(_("No escalation rate set on this lease."))
        old_rent    = self.monthly_rent
        new_rent    = old_rent * (1 + self.escalation_rate / 100)
        history     = self.escalation_history or ''
        history    += (f"\n{fields.Date.today()}: "
                       f"KES {old_rent:,.0f} → KES {new_rent:,.0f} "
                       f"({self.escalation_rate}% increase)")
        self.write({
            'monthly_rent':      new_rent,
            'next_review_date':  (self.next_review_date or fields.Date.today())
                                  + relativedelta(years=1),
            'escalation_history': history.strip(),
        })
        self.message_post(
            body=_(f"📈 Rent escalated {self.escalation_rate}%: "
                   f"KES {old_rent:,.0f} → KES {new_rent:,.0f}")
        )

    def action_generate_rent_invoice(self):
        """Generate single rent invoice for this month."""
        self.ensure_one()
        if self.status != 'active':
            raise UserError(_("Can only generate invoices for active leases."))
        today = fields.Date.today()
        lines = [(0, 0, {
            'name': f"Rent — {self.property_id.name} ({today.strftime('%B %Y')})",
            'quantity':   1,
            'price_unit': self.monthly_rent,
        })]
        if self.service_charge:
            lines.append((0, 0, {
                'name': f"Service Charge — {today.strftime('%B %Y')}",
                'quantity':   1,
                'price_unit': self.service_charge,
            }))
        if self.apply_wht and self.wht_amount:
            lines.append((0, 0, {
                'name': f"WHT {self.wht_rate}% (KRA — deducted from landlord)",
                'quantity':   1,
                'price_unit': -self.wht_amount,
            }))
        inv = self.env['account.move'].create({
            'move_type':        'out_invoice',
            'partner_id':       self.tenant_id.id,
            'lease_id':         self.id,
            'invoice_date':     today,
            'invoice_date_due': today + timedelta(days=self.grace_days or 5),
            'invoice_line_ids': lines,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': inv.id,
            'view_mode': 'form',
        }

    def action_open_invoices(self):
        self.ensure_one()
        return {
            'type':      'ir.actions.act_window',
            'name':      'Invoices',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain':    [('lease_id', '=', self.id)],
            'context':   {'default_lease_id': self.id},
        }

    def action_send_reminder(self):
        """Send outstanding balance reminder to tenant."""
        self.ensure_one()
        if not self.total_outstanding:
            raise UserError(_("No outstanding balance on this lease."))
        self.message_post(
            body=_(
                f"📢 Payment Reminder sent to {self.tenant_id.name}.\n"
                f"Outstanding Balance: KES {self.total_outstanding:,.0f}\n"
                f"Months in Arrears: {self.months_outstanding}\n"
                f"Please clear your balance immediately to avoid penalties."
            ),
            partner_ids=[self.tenant_id.id],
            subtype_xmlid='mail.mt_comment',
        )

    # ═══════════════ SCHEDULED ACTIONS (CRONS) ══════ #

    @api.model
    def _cron_auto_generate_monthly_invoices(self):
        """Run on 1st of each month — generate rent invoices for all active leases."""
        today   = fields.Date.today()
        # Only run on 1st of month
        if today.day != 1:
            return
        active  = self.search([('status', '=', 'active')])
        created = 0
        for lease in active:
            # Check not already invoiced this month
            already = lease.payment_ids.filtered(
                lambda i: i.move_type == 'out_invoice'
                and i.invoice_date
                and i.invoice_date.month == today.month
                and i.invoice_date.year == today.year
                and not (i.ref or '').startswith('PEN/')
            )
            if already:
                continue
            try:
                lease.action_generate_rent_invoice()
                created += 1
            except Exception as e:
                _logger.error("Failed to auto-invoice lease %s: %s", lease.name, e)
        _logger.info("Auto-generated %d monthly rent invoices.", created)

    @api.model
    def _cron_expire_leases(self):
        """Auto-expire leases past end date."""
        today   = fields.Date.today()
        expired = self.search([
            ('status', '=', 'active'),
            ('date_end', '<', today),
        ])
        for lease in expired:
            lease.action_expire()
        _logger.info("Auto-expired %d leases.", len(expired))

    @api.model
    def _cron_expiry_reminders(self):
        """Send expiry reminders at 60, 30, 7 days."""
        today = fields.Date.today()
        for days in (60, 30, 7):
            target = today + relativedelta(days=days)
            leases = self.search([
                ('status', '=', 'active'),
                ('date_end', '=', target),
            ])
            for lease in leases:
                lease.message_post(
                    body=_(
                        f"⚠️ Lease expires in {days} days ({lease.date_end}).\n"
                        f"Tenant: {lease.tenant_id.name}\n"
                        f"Monthly Rent: KES {lease.monthly_rent:,.0f}\n"
                        f"Please arrange renewal or notice."
                    ),
                    partner_ids=[
                        lease.tenant_id.id,
                        lease.property_id.landlord_id.id,
                    ],
                    subtype_xmlid='mail.mt_note',
                )
        _logger.info("Expiry reminders sent.")

    @api.model
    def _cron_late_payment_penalties(self):
        """Auto-generate penalty invoices for overdue rent."""
        today         = fields.Date.today()
        active_leases = self.search([('status', '=', 'active')])
        created       = 0
        for lease in active_leases:
            if not lease.penalty_rate:
                continue
            grace    = lease.grace_days or 5
            overdue  = lease.payment_ids.filtered(
                lambda i: i.move_type == 'out_invoice'
                and i.payment_state not in ('paid', 'reversed')
                and i.invoice_date_due
                and i.invoice_date_due < today - timedelta(days=grace)
                and not (i.ref or '').startswith('PEN/')
            )
            for inv in overdue:
                # Check if penalty already issued for this invoice
                already = lease.payment_ids.filtered(
                    lambda p: (p.ref or '').startswith(f'PEN/{inv.name}')
                )
                if already:
                    continue
                days_late = (today - inv.invoice_date_due).days
                penalty   = inv.amount_residual * lease.penalty_rate / 100
                if penalty < 100:
                    continue
                self.env['account.move'].create({
                    'move_type':  'out_invoice',
                    'partner_id': lease.tenant_id.id,
                    'lease_id':   lease.id,
                    'invoice_date': today,
                    'ref': f"PEN/{inv.name}",
                    'invoice_line_ids': [(0, 0, {
                        'name': (
                            f"Late Payment Penalty — {inv.name} "
                            f"({days_late} days @ {lease.penalty_rate}%)"
                        ),
                        'quantity':   1,
                        'price_unit': penalty,
                    })]
                })
                lease.message_post(
                    body=_(
                        f"💸 Late penalty KES {penalty:,.0f} generated "
                        f"for {inv.name} ({days_late} days overdue)."
                    )
                )
                created += 1
        _logger.info("Generated %d late payment penalties.", created)

    @api.model
    def _cron_rent_escalation(self):
        """Auto-apply rent escalation on review date."""
        today = fields.Date.today()
        leases = self.search([
            ('status', '=', 'active'),
            ('auto_escalate', '=', True),
            ('next_review_date', '=', today),
        ])
        for lease in leases:
            lease.action_apply_escalation()
        _logger.info("Auto-escalated %d lease rents.", len(leases))

    @api.model
    def _cron_arrears_reminders(self):
        """Daily: send reminders to tenants with 1+ months arrears."""
        today  = fields.Date.today()
        # Only run on Mondays
        if today.weekday() != 0:
            return
        leases = self.search([
            ('status', '=', 'active'),
            ('months_outstanding', '>', 0),
        ])
        for lease in leases:
            lease.action_send_reminder()
        _logger.info("Sent arrears reminders to %d tenants.", len(leases))

    # ═══════════════ CRUD ═══════════════════════════ #

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('estate.lease') or 'New'
                )
        return super().create(vals_list)
