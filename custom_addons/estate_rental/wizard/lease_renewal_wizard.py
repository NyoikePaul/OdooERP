from odoo import models, fields, api, _
from odoo.exceptions import UserError


class EstateLeaseRenewalWizard(models.TransientModel):
    _name        = 'estate.lease.renewal.wizard'
    _description = 'Renew Lease'

    lease_id     = fields.Many2one('estate.lease',   required=True, readonly=True)
    property_id  = fields.Many2one('estate.property', required=True, readonly=True)
    tenant_id    = fields.Many2one('res.partner',     required=True)
    new_start    = fields.Date("New Start Date", required=True)
    new_end      = fields.Date("New End Date",   required=True)
    currency_id  = fields.Many2one('res.currency', default=lambda s: s.env.ref('base.KES'))
    monthly_rent = fields.Monetary("New Monthly Rent", currency_field='currency_id', required=True)
    deposit      = fields.Monetary("Deposit (KES)",    currency_field='currency_id')
    escalation   = fields.Float("Escalation Applied (%)")
    notes        = fields.Text()

    def action_renew(self):
        self.ensure_one()
        if self.new_end <= self.new_start:
            raise UserError(_("End date must be after start date."))
        new_lease = self.env['estate.lease'].create({
            'property_id':    self.property_id.id,
            'unit_id':        self.lease_id.unit_id.id,
            'tenant_id':      self.tenant_id.id,
            'date_start':     self.new_start,
            'date_end':       self.new_end,
            'monthly_rent':   self.monthly_rent,
            'deposit':        self.deposit,
            'deposit_paid':   True,
            'parent_lease_id':self.lease_id.id,
            'penalty_rate':   self.lease_id.penalty_rate,
            'grace_days':     self.lease_id.grace_days,
            'escalation_rate':self.lease_id.escalation_rate,
            'apply_wht':      self.lease_id.apply_wht,
            'notes':          self.notes,
        })
        new_lease.action_activate()
        self.lease_id.write({'status':'renewed'})
        return {'type':'ir.actions.act_window','res_model':'estate.lease',
                'res_id':new_lease.id,'view_mode':'form'}
