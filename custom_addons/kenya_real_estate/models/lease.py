from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
from datetime import timedelta, date
import logging

_logger = logging.getLogger(__name__)


class EstateLease(models.Model):
    _name        = 'estate.lease'
    _description = 'Property Lease / Tenancy Agreement'
    _inherit     = ['mail.thread', 'mail.activity.mixin']
    _order       = 'date_start desc'
    _rec_name    = 'name'

    # ── Identity ─────────────────────────────────────────
    name            = fields.Char("Lease Ref",  readonly=True,y=False, default='New', index=True)
    property_id     = fields.Many2one('estate.property', required=True, ondelete='restrict',
                                       tracking=True, index=True)
    unit_id         = fields.Many2one('estate.unit',     ondelete='set null', tracking=True)
    tenant_id       = fields.Many2one('res.partner',     required=True, tracking=True, index=True)
    parent_lease_id = fields.Many2one('estate.lease',    string="Renewed From", ondelete='set null')
    renewal_ids     = fine2many('estate.lease',    'parent_lease_id', string="Renewals")
    renewal_count   = fields.Integer(compute='_compute_renewal_count')

    # ── Dates ────────────────────────────────────────────
    date_start      = fields.Date("Start Date",  required=True)
    date_end        = fields.Date("End Date",    required=True)
    notice_period   = fields.Integer("Notice Period (days)", default=30)
    notice_given    = Boolean("Notice Given", tracking=True)
    notice_date     = fields.Date("Notice Date")

    # ── Special Clauses ──────────────────────────────────
    break_clause          = fields.Boolean("Break Clause")
    break_after_months    = fields.Integer("Break After (months)", default=6)
    subletting_allowed    = fields.Boolean("Subletting Allowed", default=False)
    subletting_approved   = fields.Boolean("Subletting Approved", default=alse)

    # ── Financials ───────────────────────────────────────
    currency_id     = fields.Many2one('res.currency', default=lambda s: s.env.ref('base.KES'))
    monthly_rent    = fields.Monetary("Monthly Rent (KES)", currency_field='currency_id', tracking=True)
    service_charge  = fields.Monetary("Service Charge (KES/mo)", currency_field='currency_id')
    deposit         = fields.Monetary("Security Deposit (KES)", currency_field='currency_id')
    deposit_paid    = fields.Boolean("Deposit Paid", tracking=True)
    deposit_receipt = fields.Char("Deposit M-Pesa Receipt")

    # ── KRA Tax ──────────────────────────────────────────
    apply_wht       = fields.Boolean("Apply KRA WHT", default=True,
                                      help="5% residential / 10% commercial per Section 35 KITA")
    wht_rate        = fields.Float("WHT Rate (%)", compute='_compute_wht', store=True)
    wht_amount      = fields.Monetary("WHT Amount (KES/mo)", currency_field='currency_id',
                                       compute='_compute_wht', store=True)
    net_rent        = fields.Monetary("Net Rent after WHT", currency_field='currency_id',
                                       compute='_compute_wht', store=True)
    landlord_payout = fields.Monetary("Landlord Payout (KES/mo)", currency_field='currency_id',
                                    ompute='_compute_wht', store=True)

    # ── Escalation ───────────────────────────────────────
    escalation_rate   = fields.Float("Annual Escalation (%)", default=10.0)
    next_review_date  = fields.Date("Next Rent Review Date")
    auto_escalate     = fields.Boolean("Auto-Apply on Review Date", default=False)
    escalation_history= fields.Text("Escalation History", readonly=True)

    # ── Late Payment ────�────────────────────────────
    penalty_rate      = fields.Float("Late Penalty (%)", default=5.0)
    grace_days        = fields.Integer("Grace Days", default=5)

    # ── Status ───────────────────────────────────────────
    status = fields.Selection([
        ('draft',      'Draft'),
        ('active',     'Active'),
        ('expired',    'Expired'),
        ('renewed',    'Renewed'),
        ('cancelled',  'Cancelled'),
        ('surrendered','Surrendered'),
    ], default='draft', tracking=True, index=True)

    # ── Relations ────────────────────────────────────────
    payment_ids = fields.One2many('account.move', 'lease_id', string="Invoices")
    notes       = fields.Text("Notes / Special Conditions")

    # ── Computed ──────────────�──────────────────────
    payment_count      = fields.Integer(compute='_compute_financials', store=True)
    total_invoiced     = fields.Monetary(compute='_compute_financials', currency_field='currency_id', store=True)
    total_paid         = fields.Monetary(compute='_compute_financials', currency_field='currency_id', store=True)
    total_outstanding  = fields.Monetary(compute='_compute_financials', currency_field='currency_id', store=True)
    months_arrears    = fields.Integer(compute='_compute_financials', store=True, string="Months in Arrears")
    days_to_expiry     = fields.Integer(compute='_compute_expiry',     store=True)
    is_expiring_soon   = fields.Boolean(compute='_compute_expiry',     store=True)
    duration_months    = fields.Integer(compute='_compute_duration',   store=True)
    total_lease_value  = fields.Monetary(compute='_compute_duration',  currency_field='currency_id', store=True)

    _sql_constraints = [
        ('name_unique',    'UNIQUEame)',          'Lease reference must be unique.'),
        ('rent_positive',  'CHECK(monthly_rent>=0)', 'Rent cannot be negative.'),
        ('deposit_positive','CHECK(deposit>=0)',     'Deposit cannot be negative.'),
    ]

    # ═══ COMPUTE ════════════════════════════════════════

    def _compute_renewal_count(self):
        for r in self:
            r.renewal_count = len(r.renewal_ids)

    @api.depends('property_idperty_type', 'monthly_rent', 'apply_wht')
    def _compute_wht(self):
        for r in self:
            if r.apply_wht:
                rate = 10.0 if r.property_id.property_type == 'commercial' else 5.0
            else:
                rate = 0.0
            r.wht_rate      = rate
            r.wht_amount    = r.monthly_rent * rate / 100
            r.net_rent      = r.monthly_rent - r.wht_amount
            r.landlord_payout = r.monthly_rent - r.wht_amount

    @api.depends('payment_ids.payment_state','ment_ids.amount_total',
                 'payment_ids.amount_residual','payment_ids.move_type','monthly_rent')
    def _compute_financials(self):
        for r in self:
            invs  = r.payment_ids.filtered(
                lambda i: i.move_type=='out_invoice' and not (i.ref or '').startswith('PEN/'))
            paid  = invs.filtered(lambda i: i.payment_state=='paid')
            unpaid= invs.filtered(lambda i: i.payment_state not in ('paid','reversed'))
            r.payment_count     = len(invs)
            r.total_invoiced    = sum(invs.mapped('amount_total'))
            r.total_paid        = sum(paid.mapped('amount_total'))
            r.total_outstanding = sum(unpaid.mapped('amount_residual'))
            r.months_arrears    = int(r.total_outstanding / r.monthly_rent) if r.monthly_rent else 0

    @api.depends('date_end', 'status')
    def _compute_expiry(self):
        today = fields.Date.today()
        for r in self:
            if r.date_end and r.status == 'active':
                delta = (r.date_end - today).days
                r.days_to_expiry   = delta
                r.is_expiring_soon = 0 <= delta <= 30
            else:
                r.days_to_expiry   = 0
                r.is_expiring_soon = False

    @api.depends('date_start','date_end','monthly_rent','service_charge')
    def _compute_duration(self):
        for r in self:
            if r.date_start and r.date_end:
                d = relativedelta(r.date_end, r.date_start)
                months = d.years * 12 + d.months
            r.duration_months  = months
                r.total_lease_value= months * (r.monthly_rent + r.service_charge)
            else:
                r.duration_months  = 0
                r.total_lease_value= 0

    # ═══ CONSTRAINTS ════════════════════════════════════

    @api.constrains('date_start','date_end')
    def _check_dates(self):
        for r in self:
            if r.date_end <= r.date_start:
                raise VtionError(_("Lease end date must be after start date."))

    @api.constrains('property_id','unit_id','date_start','date_end','status')
    def _check_no_overlap(self):
        for r in self:
            if r.status not in ('active','draft'):
                continue
            domain = [('status','in',('active','draft')),
                      ('id','!=',r.id),
                      ('date_start','<',r.date_end),
                      ('date_end','>',r.date_start)]
            if r.unit_id:
              omain.append(('unit_id','=',r.unit_id.id))
            else:
                domain.append(('property_id','=',r.property_id.id))
            overlap = self.search(domain, limit=1)
            if overlap:
                raise ValidationError(
                    _(f"Overlapping lease exists: {overlap.name} ({overlap.date_start} – {overlap.date_end})")
                )

    # ═══ WORKFLOW ═════════════════════════════════════�    def action_activate(self):
        for r in self:
            if r.deposit and not r.deposit_paid:
                raise UserError(_("Security deposit must be marked as paid before activation."))
            r.write({'status':'active'})
            if r.unit_id:
                r.unit_id.write({'status':'leased','tenant_id':r.tenant_id.id})
            r.property_id.write({'status':'leased'})
            if not r.next_review_date and r.escalation_rate:
                r.next_review_date = r.date_start +relativedelta(years=1)
            r.message_post(body=_(
                f"✅ Lease activated. Tenant: {r.tenant_id.name}. "
                f"Rent: KES {r.monthly_rent:,.0f}/mo. Term: {r.date_start} → {r.date_end}."
            ))

    def _free_property(self):
        """Free property/unit if no other active leases."""
        if self.unit_id:
            self.unit_id.write({'status':'vacant','tenant_id':False})
        others = self.search([
            ('property_id','=',self.property_id.id),
       ('status','=','active'),('id','!=',self.id)
        ])
        if not others:
            self.property_id.write({'status':'available'})

    def action_cancel(self):
        for r in self:
            r.write({'status':'cancelled'})
            r._free_property()
            r.message_post(body=_("❌ Lease cancelled."))

    def action_expire(self):
        for r in self:
            r.write({'status':'expired'})
            r._free_property()
            r.message_post(body=_("⏰ Lease expired."))

   def action_surrender(self):
        for r in self:
            r.write({'status':'surrendered'})
            r._free_property()
            r.message_post(body=_(f"🏳️ Lease surrendered on {fields.Date.today()}."))

    def action_apply_escalation(self):
        self.ensure_one()
        if not self.escalation_rate:
            raise UserError(_("No escalation rate set on this lease."))
        old  = self.monthly_rent
        new  = old * (1 + self.escalation_rate / 100)
        hist = (self.escalation_history or '') + (
            f"\n{fields.Date.today()}: KES {old:,.0f} → KES {new:,.0f} ({self.escalation_rate}%)")
        self.write({
            'monthly_rent':       new,
            'next_review_date':   (self.next_review_date or fields.Date.today()) + relativedelta(years=1),
            'escalation_history': hist.strip(),
        })
        self.message_post(body=_(f"📈 Rent escalated {self.escalation_rate}%: KES {old:,.0f} → KES {new:,.0f}"))

    def action_renew(self):
        self.ense_one()
        new_start    = self.date_end + relativedelta(days=1)
        new_rent     = self.monthly_rent * (1 + self.escalation_rate / 100)
        return {
            'type':'ir.actions.act_window','name':_('Renew Lease'),
            'res_model':'estate.lease.renewal.wizard','view_mode':'form','target':'new',
            'context':{
                'default_lease_id':    self.id,
                'default_property_id': self.property_id.id,
                'default_tenant_id':   self.tenant_id.id,
          'default_new_start':   new_start,
                'default_new_end':     new_start + relativedelta(years=1),
                'default_monthly_rent':new_rent,
                'default_deposit':     self.deposit,
            }
        }

    def action_generate_invoice(self):
        self.ensure_one()
        if self.status != 'active':
            raise UserError(_("Can only invoice active leases."))
        today = fields.Date.today()
        lines = [(0,0,{
            'name':f"Rent — {self.proper_id.name} ({today.strftime('%B %Y')})",
            'quantity':1,'price_unit':self.monthly_rent,
        })]
        if self.service_charge:
            lines.append((0,0,{
                'name':f"Service Charge — {today.strftime('%B %Y')}",
                'quantity':1,'price_unit':self.service_charge,
            }))
        inv = self.env['account.move'].create({
            'move_type':        'out_invoice',
            'partner_id':       self.tenant_id.id,
            'lease_id':         self.id,
        'invoice_date':     today,
            'invoice_date_due': today + timedelta(days=self.grace_days or 5),
            'invoice_line_ids': lines,
        })
        return {'type':'ir.actions.act_window','res_model':'account.move','res_id':inv.id,'view_mode':'form'}

    def action_open_invoices(self):
        self.ensure_one()
        return {'type':'ir.actions.act_window','name':'Invoices','res_model':'account.move',
                'view_mode':'list,form','domain':[('lease_id','=',self.id)]}

    deaction_send_reminder(self):
        self.ensure_one()
        self.message_post(
            body=_(f"📢 Payment Reminder — Outstanding: KES {self.total_outstanding:,.0f} "
                   f"({self.months_arrears} month(s) in arrears)."),
            partner_ids=[self.tenant_id.id], subtype_xmlid='mail.mt_comment')

    # ═══ SCHEDULED CRONS ════════════════════════════════

    @api.model
    def _cron_auto_monthly_invoices(self):      today = fields.Date.today()
        if today.day != 1:
            return
        active = self.search([('status','=','active')])
        n = 0
        for lease in active:
            already = lease.payment_ids.filtered(
                lambda i: i.move_type=='out_invoice' and i.invoice_date
                and i.invoice_date.month==today.month and i.invoice_date.year==today.year
                and not (i.ref or '').startswith('PEN/'))
            if already:
                continue
            tr               lease.action_generate_invoice()
                n += 1
            except Exception as e:
                _logger.error("Auto-invoice failed for %s: %s", lease.name, e)
        _logger.info("Auto-generated %d monthly rent invoices.", n)

    @api.model
    def _cron_expire_leases(self):
        today   = fields.Date.today()
        expired = self.search([('status','=','active'),('date_end','<',today)])
        for l in expired:
            l.action_expire()
        _logger.info("Auto-expired ses.", len(expired))

    @api.model
    def _cron_expiry_reminders(self):
        today = fields.Date.today()
        for days in (60, 30, 7):
            target = today + relativedelta(days=days)
            leases = self.search([('status','=','active'),('date_end','=',target)])
            for l in leases:
                l.message_post(
                    body=_(f"⚠️ Lease expires in {days} days ({l.date_end}). "
                           f"Tenant: {l.tenant_id.name}. Rent: KES {l.monthly_rent:,.0"),
                    partner_ids=[l.tenant_id.id, l.property_id.landlord_id.id],
                    subtype_xmlid='mail.mt_note')

    @api.model
    def _cron_late_payment_penalties(self):
        today  = fields.Date.today()
        active = self.search([('status','=','active')])
        n = 0
        for lease in active:
            if not lease.penalty_rate:
                continue
            grace   = lease.grace_days or 5
            overdue = lease.payment_ids.filtered(
                lambda i i.move_type=='out_invoice'
                and i.payment_state not in ('paid','reversed')
                and i.invoice_date_due
                and i.invoice_date_due < today - timedelta(days=grace)
                and not (i.ref or '').startswith('PEN/'))
            for inv in overdue:
                existing = lease.payment_ids.filtered(
                    lambda p: (p.ref or '').startswith(f'PEN/{inv.name}'))
                if existing:
                    continue
                days_late = (today - inv.invoice_date_due).days
                penalty   = inv.amount_residual * lease.penalty_rate / 100
                if penalty < 100:
                    continue
                self.env['account.move'].create({
                    'move_type':'out_invoice','partner_id':lease.tenant_id.id,
                    'lease_id':lease.id,'invoice_date':today,'ref':f'PEN/{inv.name}',
                    'invoice_line_ids':[(0,0,{
                        'name':f"Late Penalty — {inv.name} ({days_late}d @ {lease.penalty_rate}%)",
                        'quantity':1,'price_unit':penalty,
                    })]
                })
                n += 1
        _logger.info("Generated %d late payment penalties.", n)

    @api.model
    def _cron_rent_escalation(self):
        today  = fields.Date.today()
        leases = self.search([
            ('status','=','active'),
            ('auto_escalate','=',True),
            ('next_review_date','=',today),
        ])
        for l in leases:
            l.actiopply_escalation()

    @api.model
    def _cron_arrears_reminders(self):
        today = fields.Date.today()
        if today.weekday() != 0:
            return
        leases = self.search([('status','=','active'),('months_arrears','>',0)])
        for l in leases:
            l.action_send_reminder()
        _logger.info("Sent arrears reminders to %d tenants.", len(leases))

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name','New') == 'New':
                v['name'] = self.env['ir.sequence'].next_by_code('estate.lease') or 'New'
        return super().create(vals_list)
