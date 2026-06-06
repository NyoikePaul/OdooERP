"""
Kenya-specific partner fields:
- KRA PIN (validated format A000000000B)
- ID Number / Passport
- M-Pesa phone primary
- Tenant lease history smart button
"""
import re
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartnerKenya(models.Model):
    _inherit = 'res.partner'

    kra_pin          = fields.Char("KRA PIN", size=11, tracking=True)
    id_number        = fields.Char("National ID / Passport")
    nhif_number      = fields.Char("NHIF Number")
    nssf_number      = fields.Char("NSSF Number")
    is_tenant        = fields.Boolean("Is Tenant", default=False)
    is_landlord      = fields.Boolean("Is Landlord", default=False)
    mpesa_phone      = fields.Char("Primary M-Pesa Phone",
                                   help="Phone number registered on M-Pesa for rent payment")

    # Lease stats
    lease_ids        = fields.One2many('estate.lease', 'tenant_id', string="Leases")
    active_lease_count = fields.Integer(compute='_compute_lease_stats', string="Active Leases")
    total_arrears    = fields.Monetary(compute='_compute_lease_stats', string="Total Arrears",
                                       currency_field='currency_id')
    currency_id      = fields.Many2one('res.currency',
                                       default=lambda s: s.env.ref('base.KES'))

    def _compute_lease_stats(self):
        for r in self:
            active = r.lease_ids.filtered(lambda l: l.status == 'active')
            r.active_lease_count = len(active)
            r.total_arrears = sum(active.mapped('total_outstanding'))

    def action_open_leases(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('Leases'),
            'res_model': 'estate.lease', 'view_mode': 'list,form',
            'domain': [('tenant_id', '=', self.id)],
        }

    def action_open_mpesa_txns(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('M-Pesa Transactions'),
            'res_model': 'mpesa.transaction', 'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
        }

    @api.constrains('kra_pin')
    def _validate_kra_pin(self):
        for r in self:
            if r.kra_pin:
                pin = r.kra_pin.upper().strip()
                if not re.match(r'^[A-Z]\d{9}[A-Z]$', pin):
                    raise ValidationError(
                        _("Invalid KRA PIN '%s'. Format must be: A000000000B "
                          "(letter, 9 digits, letter)") % r.kra_pin)
                r.kra_pin = pin
