from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)


class EstateMaintenanceRequest(models.Model):
    _name        = 'estate.maintenance.request'
    _description = 'Maint Request'
    _inherit     = ['mail.thread', 'mail.activity.mixin']
    _order       = 'priority desc, date_reported desc'

    name         = fields.Char("Issue / Title", required=True, tracking=True)
    ref          = fields.Char("Request Ref", readonly=True, copy=False, default='New')
    property_id  = fields.Many2one('estate.property', required=True, index=True, ondelete='restrict')
    unit_id      = fields.Many2one('estate.unit', string="Unit")
    lease_id     = fields.Many2one('estate.lease', strig="Reported by Lease")
    reported_by  = fields.Many2one('res.partner', string="Reported By")
    assigned_to  = fields.Many2one('res.users',   string="Assigned To")

    category     = fields.Selection([
        ('plumbing','Plumbing'),('electrical','Electrical'),
        ('structural','Structural'),('painting','Painting'),
        ('security','Security/Gate'),('cleaning','Cleaning'),
        ('hvac','HVAC/AC'),('roof','Roof'),('other','Other'),
    ], required=True, default='other')

    priority     = fSelection([('0','Normal'),('1','Medium'),('2','High'),('3','Critical')],
                                     default='0', tracking=True)
    status       = fields.Selection([
        ('new','New'),('in_progress','In Progress'),
        ('waiting_parts','Waiting Parts'),('done','Done'),('cancelled','Cancelled'),
    ], default='new', tracking=True)

    currency_id    = fields.Many2one('res.currency', default=lambda s: s.env.ref('base.KES'))
    estimated_cost = fields.Monetary("Estimated Cost (KES)", curre_field='currency_id')
    actual_cost    = fields.Monetary("Actual Cost (KES)",    currency_field='currency_id')
    description    = fields.Text("Description")
    date_reported  = fields.Date("Date Reported", default=fields.Date.today, required=True)
    date_resolved  = fields.Date("Date Resolved")
    active         = fields.Boolean(default=True)

    _sql_constraints = [('ref_unique','UNIQUE(ref)','Ref must be unique.')]

    def action_start(self):
        self.write({'status':'in_progress'})

    defction_done(self):
        self.write({'status':'done','date_resolved':fields.Date.today()})

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('ref','New')=='New':
                v['ref'] = self.env['ir.sequence'].next_by_code('estate.maintenance') or 'New'
        return super().create(vals_list)
