"""
Formal Demand Notice & Eviction Workflow — Kenya
Under the Landlord & Tenant Act (Cap 301) and Distress for Rent Act (Cap 293),
landlords must follow a legal process before evicting a tenant.

Workflow:
1. Verbal reminder → 2. Written demand notice (7 days) →
3. Formal 30-day notice → 4. BPRT filing (commercial) →
5. Court summons → 6. Eviction order
"""
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class EstateDemandNotice(models.Model):
    _name        = 'estate.demand.notice'
    _description = 'Demand Notice / Eviction Workflow'
    _inherit     = ['mail.thread', 'mail.activity.mixin']
    _order       = 'issue_date desc'

    name         = fields.Char("Notice Ref", readonly=True, default='New', copy=False)
    lease_id     = fields.Many2one('estate.lease', string="Lease",
                                   required=True, ondelete='restrict', tracking=True)
    property_id  = fields.Many2one(related='lease_id.property_id', store=True)
    tenant_id    = fields.Many2one(related='lease_id.tenant_id', store=True)

    notice_type  = fields.Selection([
        ('arrears',       'Rent Arrears Demand'),
        ('breach',        'Lease Breach Notice'),
        ('vacate_30',     '30-Day Vacate Notice'),
        ('vacate_7',      '7-Day Vacate Notice (Urgent)'),
        ('bprt',          'BPRT Filing (Commercial)'),
        ('court',         'Court Summons'),
    ], required=True, default='arrears', tracking=True)

    currency_id  = fields.Many2one('res.currency',
                                   default=lambda s: s.env.ref('base.KES'))
    arrears_amount = fields.Monetary("Arrears Amount (KES)", currency_field='currency_id')
    months_arrears = fields.Integer("Months in Arrears")
    issue_date     = fields.Date("Issue Date", required=True, default=fields.Date.today)
    response_deadline = fields.Date("Response Deadline", compute='_compute_deadline', store=True)
    served_by      = fields.Selection([
        ('hand',    'Hand Delivered'),
        ('post',    'Registered Post'),
        ('email',   'Email'),
        ('bailiff', 'Bailiff'),
    ], default='hand')
    served_date    = fields.Date("Date Served")
    witness_name   = fields.Char("Witness Name")

    status = fields.Selection([
        ('draft',       'Draft'),
        ('issued',      'Issued'),
        ('responded',   'Tenant Responded'),
        ('resolved',    'Resolved — Arrears Paid'),
        ('escalated',   'Escalated to Court/BPRT'),
        ('evicted',     'Eviction Executed'),
        ('withdrawn',   'Withdrawn'),
    ], default='draft', tracking=True)

    notes        = fields.Text("Notes / Legal References")
    legal_ref    = fields.Char("Legal Reference / Case Number")

    @api.depends('issue_date', 'notice_type')
    def _compute_deadline(self):
        days_map = {
            'arrears':   7,
            'breach':    14,
            'vacate_30': 30,
            'vacate_7':  7,
            'bprt':      21,
            'court':     30,
        }
        for rec in self:
            if rec.issue_date and rec.notice_type:
                days = days_map.get(rec.notice_type, 14)
                rec.response_deadline = rec.issue_date + relativedelta(days=days)

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name', 'New') == 'New':
                v['name'] = self.env['ir.sequence'].next_by_code('estate.demand.notice') or 'New'
        return super().create(vals_list)

    def action_issue(self):
        self.write({'status': 'issued', 'served_date': fields.Date.today()})
        self.message_post(
            body=_(f"Notice issued to {self.tenant_id.name} via {self.served_by}. "
                   f"Response deadline: {self.response_deadline}."),
            partner_ids=[self.tenant_id.id],
            subtype_xmlid='mail.mt_comment',
        )

    def action_mark_resolved(self):
        self.write({'status': 'resolved'})
        self.message_post(body=_("Notice resolved — tenant has settled arrears."))

    def action_escalate(self):
        self.write({'status': 'escalated'})
        self.message_post(
            body=_(f"Escalated to {'BPRT' if self.lease_id.property_id.property_type == 'commercial' else 'court'} "
                   f"on {fields.Date.today()}.")
        )

    def action_execute_eviction(self):
        self.ensure_one()
        self.write({'status': 'evicted'})
        self.lease_id.action_surrender()
        self.message_post(body=_("Eviction executed. Lease surrendered."))

    def action_withdraw(self):
        self.write({'status': 'withdrawn'})

    @api.model
    def _cron_overdue_notice_alerts(self):
        """Alert on demand notices past their deadline with no response."""
        today   = fields.Date.today()
        overdue = self.search([
            ('status', '=', 'issued'),
            ('response_deadline', '<', today),
        ])
        for notice in overdue:
            notice.message_post(
                body=_(f"Demand notice {notice.name} is OVERDUE. "
                       f"Deadline was {notice.response_deadline}. "
                       f"Consider escalating to BPRT/court."),
                subtype_xmlid='mail.mt_note',
            )
        _logger.info("Alerted on %d overdue demand notices.", len(overdue))
