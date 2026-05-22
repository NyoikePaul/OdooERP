from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta


class EstateLeaseRenewalWizard(models.TransientModel):
    _name = 'estate.lease.renewal.wizard'
    _description = 'Lease Renewal Wizard'

    lease_id      = fields.Many2one('estate.lease', string="Current Lease", required=True)
    property_id   = fields.Many2one('estate.property', string="Property", required=True)
    tenant_id     = fields.Many2one('res.partner', string="Tenant", required=True)
    new_start     = fields.Date("New Start Date", required=True)
    new_end       = fields.Date("New End Date",   required=True)
    monthly_rent  = fields.Monetary("New Monthly Rent (KES)", currency_field='currency_id')
    currency_id   = fields.Many2one('res.currency', default=lambda s: s.env.ref('base.KES'))
    deposit       = fields.Monetary("Security Deposit (KES)", currency_field='currency_id')
    notes         = fields.Text("Renewal Notes")

    @api.onchange('new_start')
    def _onchange_new_start(self):
        if self.new_start:
            self.new_end = self.new_start + relativedelta(years=1)

    def action_renew(self):
        self.ensure_one()
        if self.new_end <= self.new_start:
            raise UserError(_("End date must be after start date."))

        # Mark original lease as renewed
        self.lease_id.write({'status': 'renewed'})

        # Create new lease
        new_lease = self.env['estate.lease'].create({
            'property_id':     self.property_id.id,
            'tenant_id':       self.tenant_id.id,
            'date_start':      self.new_start,
            'date_end':        self.new_end,
            'monthly_rent':    self.monthly_rent,
            'deposit':         self.deposit,
            'parent_lease_id': self.lease_id.id,
            'notes':           self.notes,
            'status':          'active',
        })
        self.property_id.write({'status': 'leased'})

        self.lease_id.message_post(
            body=f"Lease renewed. New lease: {new_lease.name}"
        )

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'estate.lease',
            'res_id': new_lease.id,
            'view_mode': 'form',
            'target': 'current',
        }
