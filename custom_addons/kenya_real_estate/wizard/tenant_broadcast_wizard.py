from odoo import models, fields, api, _
from odoo.exceptions import UserError


class TenantBroadcastWizard(models.TransientModel):
    _name        = 'estate.tenant.broadcast.wizard'
    _description = 'Broadcast Message to Tenants'

    scope       = fields.Selection([
        ('all',      'All Active Tenants'),
        ('building', 'Building Tenants'),
        ('county',   'County Tenants'),
        ('arrears',  'Tenants in Arrears Only'),
    ], default='all', required=True)
    building_id = fields.Many2one('estate.building', string="Building")
    county      = fields.Char("County")
    subject     = fields.Char("Subject", required=True)
    body        = fields.Html("Message Body", required=True)
    send_email  = fields.Boolean("Send via Email", default=True)
    tenant_count = fields.Integer(compute='_compute_count')

    @api.depends('scope', 'building_id', 'county')
    def _compute_count(self):
        for rec in self:
            rec.tenant_count = len(rec._get_leases())

    def _get_leases(self):
        domain = [('status', '=', 'active')]
        if self.scope == 'building' and self.building_id:
            domain.append(('unit_id.building_id', '=', self.building_id.id))
        elif self.scope == 'county' and self.county:
            domain.append(('property_id.county', 'ilike', self.county))
        elif self.scope == 'arrears':
            domain.append(('months_outstanding', '>', 0))
        return self.env['estate.lease'].search(domain)

    def action_broadcast(self):
        leases = self._get_leases()
        if not leases:
            raise UserError(_("No tenants found for the selected criteria."))
        for lease in leases:
            subtype = 'mail.mt_comment' if self.send_email else 'mail.mt_note'
            lease.message_post(
                subject=self.subject,
                body=self.body,
                partner_ids=[lease.tenant_id.id],
                subtype_xmlid=subtype,
            )
        return {
            'type': 'ir.actions.client',
            'tag':  'display_notification',
            'params': {
                'title':   _('Broadcast Sent'),
                'message': _(f'{len(leases)} tenants notified.'),
                'type':    'success',
            }
        }
