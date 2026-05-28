from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class EstateInsurance(models.Model):
    _name        = 'estate.insurance'
    _description = 'Property Insurance Policy'
    _inherit     = ['mail.thread', 'mail.activity.mixin']
    _order       = 'expiry_date'

    name           = fields.Char("Policy Ref", readonly=True, default='New', copy=False)
    property_id    = fields.Many2one('estate.property', string="Property",
                                     required=True, ondelete='cascade', tracking=True)
    insurer        = fields.Char("Insurer", required=True)
    policy_number  = fields.Char("Policy Number", required=True, tracking=True)
    policy_type    = fields.Selection([
        ('fire',          'Fire & Perils'),
        ('comprehensive', 'Comprehensive'),
        ('liability',     'Public Liability'),
        ('contents',      'Contents'),
        ('flood',         'Flood Cover'),
        ('earthquake',    'Earthquake'),
    ], required=True, default='comprehensive', tracking=True)
    currency_id    = fields.Many2one('res.currency',
                                     default=lambda s: s.env.ref('base.KES'))
    premium        = fields.Monetary("Annual Premium (KES)", currency_field='currency_id',
                                     tracking=True)
    sum_insured    = fields.Monetary("Sum Insured (KES)", currency_field='currency_id')
    start_date     = fields.Date("Start Date", required=True)
    expiry_date    = fields.Date("Expiry Date", required=True, tracking=True)
    days_to_expiry = fields.Integer(compute='_compute_status', store=True)
    is_expired     = fields.Boolean(compute='_compute_status', store=True)
    expiring_soon  = fields.Boolean(compute='_compute_status', store=True)
    active         = fields.Boolean(default=True)
    notes          = fields.Text("Notes")

    _sql_constraints = [
        ('policy_number_unique', 'UNIQUE(policy_number)',
         'Policy number must be unique.'),
        ('premium_positive', 'CHECK(premium >= 0)',
         'Premium cannot be negative.'),
    ]

    @api.depends('expiry_date')
    def _compute_status(self):
        today = fields.Date.today()
        for rec in self:
            if rec.expiry_date:
                delta              = (rec.expiry_date - today).days
                rec.days_to_expiry = delta
                rec.is_expired     = delta < 0
                rec.expiring_soon  = 0 <= delta <= 30
            else:
                rec.days_to_expiry = 0
                rec.is_expired     = False
                rec.expiring_soon  = False

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name', 'New') == 'New':
                v['name'] = self.env['ir.sequence'].next_by_code('estate.insurance') or 'New'
        return super().create(vals_list)

    @api.model
    def _cron_insurance_reminders(self):
        today  = fields.Date.today()
        target = today + relativedelta(days=30)
        records = self.search([
            ('expiry_date', '<=', target),
            ('expiry_date', '>=', today),
            ('active', '=', True),
        ])
        for ins in records:
            ins.message_post(
                body=_(f"Insurance Reminder: Policy {ins.policy_number} "
                       f"({ins.insurer}) expires {ins.expiry_date} "
                       f"in {ins.days_to_expiry} days. Please renew."),
                partner_ids=[ins.property_id.landlord_id.id],
                subtype_xmlid='mail.mt_note',
            )
        _logger.info("Insurance reminders sent for %d policies.", len(records))
