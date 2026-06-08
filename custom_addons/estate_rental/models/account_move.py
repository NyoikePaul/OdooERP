from odoo import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    lease_id = fields.Many2one('estate.lease', string="Lease",
                                ondelete='set null', index=True,
                                copy=False)

    sale_id = fields.Many2one('estate.property.sale', string='Sale', ondelete='set null', index=True, copy=False)
