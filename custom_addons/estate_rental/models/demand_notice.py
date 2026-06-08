from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
import logging
_logger = logging.getLogger(__name__)


class EstateDemandNotice(models.Model):
    _name        = 'estate.demand.notice'
    _description = 'Demand Notice — Landlord & Tenant Act Cap 301'
    _inherit     = ['mail.thread', 'mail.activity.mixin']
    _order       = 'issue_date desc'

    name         = fields.Char("Notice Ref", readonly=True, copy=False, default='New')
    lease_id     = fields.Many2one('estate.lease', required=True, ondelete='restrict', tracking=True)
    property_id  = fields.Many2one(related='lease_id.property_id', store=True)
    tenant_id    = fields.Many2one(related='lease_id.tenant_id',   store=True)
    notice_type  = fields.Selection([
        ('arrears',   'Rent Arrears Demand (7 days)'),
        ('breach',    'Lease Breach Notice (14 days)'),
        ('vacate_30', '30-Day Vacate Notice'),
        ('vacate_7',  '7-Day Vacate Notice'),
        ('bprt',      'BPRT Filing (Commercial)'),
        ('court',     'Court Summons'),
    ], required=True, default='arrears', tracking=True)
    currency_id    = fields.Many2one('res.currency', default=lambda s: s.env.ref('base.KES'))
    arrears_amount = fields.Monetary("Arrears Amount", currency_field='currency_id')
    months_arrears = fields.Integer("Months in Arrears")
    issue_date     = fields.Date("Issue Date", required=True, default=fields.Date.today)
    deadline       = fields.Date("Response Deadline", compute='_compute_deadline', store=True)
    served_by      = fields.Selection([('hand','Hand Delivered'),('post','Post'),('email','Email'),('bailiff','Bailiff')], default='hand')
    witness        = fields.Char("Witness Name")
    status         = fields.Selection([
        ('draft','Draft'),('issued','Issued'),('resolved','Resolved'),
        ('escalated','Escalated'),('evicted','Evicted'),('withdrawn','Withdrawn'),
    ], default='draft', tracking=True)
    legal_ref      = fields.Char("Case/Legal Reference")
    notes          = fields.Text()

    @api.depends('issue_date','notice_type')
    def _compute_deadline(self):
        days = {'arrears':7,'breach':14,'vacate_30':30,'vacate_7':7,'bprt':21,'court':30}
        for r in self:
            if r.issue_date and r.notice_type:
                r.deadline = r.issue_date + relativedelta(days=days.get(r.notice_type,14))

    def action_issue(self):
        self.write({'status':'issued'})
        self.message_post(
            body=_(f"Notice issued to {self.tenant_id.name} via {self.served_by}. Deadline: {self.deadline}."),
            partner_ids=[self.tenant_id.id], subtype_xmlid='mail.mt_comment')

    def action_resolve(self):
        self.write({'status':'resolved'})
    def action_escalate(self):
        self.write({'status':'escalated'})
    def action_withdraw(self):
        self.write({'status':'withdrawn'})
    def action_evict(self):
        self.write({'status':'evicted'})
        self.lease_id.action_surrender()

    @api.model
    def _cron_overdue_notices(self):
        today   = fields.Date.today()
        overdue = self.search([('status','=','issued'),('deadline','<',today)])
        for n in overdue:
            n.message_post(body=_(f"Demand notice {n.name} OVERDUE since {n.deadline}. Consider escalating."),
                           subtype_xmlid='mail.mt_note')
        _logger.info("Alerted on %d overdue demand notices.", len(overdue))

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name','New')=='New':
                v['name'] = self.env['ir.sequence'].next_by_code('estate.demand.notice') or 'New'
        return super().create(vals_list)
