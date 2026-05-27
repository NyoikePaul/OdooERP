from odoo import models, fields, api, _


class EstateLeaseTemplate(models.Model):
    _name        = 'estate.lease.template'
    _description = 'Lease Template'
    _order       = 'name'

    name             = fields.Char("Template Name", required=True)
    property_type    = fields.Selection([
        ('residential', 'Residential'),
        ('commercial',  'Commercial'),
        ('industrial',  'Industrial'),
    ], string="Applicable To", default='residential')
    duration_months  = fields.Integer("Default Duration (months)", default=12)
    notice_period    = fields.Integer("Notice Period (days)", default=30)
    penalty_rate     = fields.Float("Late Payment Penalty (%)", default=5.0)
    grace_days       = fields.Integer("Grace Period (days)", default=5)
    escalation_rate  = fields.Float("Annual Escalation (%)", default=10.0)
    auto_escalate    = fields.Boolean("Auto-Apply Escalation", default=True)
    apply_wht        = fields.Boolean("Apply WHT (KRA)", default=True)
    break_clause     = fields.Boolean("Break Clause Allowed", default=False)
    subletting_allowed = fields.Boolean("Subletting Allowed", default=False)
    special_conditions = fields.Text("Standard Special Conditions")
    active           = fields.Boolean(default=True)

    def apply_to_lease(self, lease):
        """Apply this template to an existing lease record."""
        from dateutil.relativedelta import relativedelta
        vals = {
            'notice_period':    self.notice_period,
            'penalty_rate':     self.penalty_rate,
            'grace_days':       self.grace_days,
            'escalation_rate':  self.escalation_rate,
            'auto_escalate':    self.auto_escalate,
            'apply_wht':        self.apply_wht,
            'break_clause':     self.break_clause,
            'subletting_allowed': self.subletting_allowed,
            'notes':            self.special_conditions,
        }
        if lease.date_start and self.duration_months:
            vals['date_end'] = (
                lease.date_start + relativedelta(months=self.duration_months)
            )
        lease.write(vals)
        lease.message_post(
            body=_(f"Lease template '{self.name}' applied.")
        )
