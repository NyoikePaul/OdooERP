from odoo import models, fields, api, _
from odoo.exceptions import UserError


class TenantBroadcastWizard(models.TransientModel):
    _name        = 'estate.tenant.broadcast.wizard'
    _description = 'Send Message to All Tenants'

    scope = fields.Selection([
        ('all',      'All Active Tenants'),
        ('building', 'Specific Building'),
        ('county',   'Specific County'),
    ], string="Recipients", default='all', required=True)

    building_id = fields.Many2one('estate.building', string="Building",
                                  invisible="scope != 'building'")
    county      = fields.Char("County", invisible="scope != 'county'")
    subject     = fields.Char("Subject", required=True)
    body        = fields.Html("Message", required=True)

    tenant_count = fields.Integer(compute='_compute_tenant_count')

    @api.depends('scope', 'building_id', 'county')
    def _compute_tenant_count(self):
        for rec in self:
            rec.tenant_count = len(rec._get_leases())

    def _get_leases(self):
        domain = [('status', '=', 'active')]
        if self.scope == 'building' and self.building_id:
            domain.append(('unit_id.building_id', '=', self.building_id.id))
        elif self.scope == 'county' and self.county:
            domain.append(('property_id.county', 'ilike', self.county))
        return self.env['estate.lease'].search(domain)

    def action_broadcast(self):
        self.ensure_one()
        leases = self._get_leases()
        if not leases:
            raise UserError(_("No active tenants found for the selected scope."))
        sent = 0
        for lease in leases:
            lease.message_post(
                subject=self.subject,
                body=self.body,
                partner_ids=[lease.tenant_id.id],
                subtype_xmlid='mail.mt_comment',
            )
            sent += 1
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title':   _('Broadcast Sent'),
                'message': _(f'Message sent to {sent} tenants successfully.'),
                'type':    'success',
            }
        }
