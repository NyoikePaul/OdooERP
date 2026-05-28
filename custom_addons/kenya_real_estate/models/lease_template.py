from odoo import models, fields, api, _


class EstateLeaseTemplate(models.Model):
    _name        = 'estate.lease.template'
    _description = 'Lease Template — Quick Onboarding'
    _order       = 'name'

    name             = fields.Char("Template Name", required=True)
    property_type    = fields.Selection([
        ('residential', 'Residential'),
        ('commercial',  'Commercial'),
        ('industrial',  'Industrial'),
    ], default='residential')
    duration_months  = fields.Integer("Duration (months)", default=12)
    notice_period    = fields.Integer("Notice Period (days)", default=30)
    penalty_rate     = fields.Float("Late Penalty (%)", default=5.0)
    grace_days       = fields.Integer("Grace Period (days)", default=5)
    escalation_rate  = fields.Float("Escalation (%/year)", default=10.0)
    auto_escalate    = fields.Boolean("Auto Escalate", default=True)
    apply_wht        = fields.Boolean("Apply KRA WHT", default=True)
    break_clause     = fields.Boolean("Break Clause", default=False)
    subletting       = fields.Boolean("Subletting Allowed", default=False)
    conditions       = fields.Text("Standard Special Conditions")
    active           = fields.Boolean(default=True)

    def apply_to_lease(self, lease):
        from dateutil.relativedelta import relativedelta
        vals = {
            'notice_period':   self.notice_period,
            'penalty_rate':    self.penalty_rate,
            'grace_days':      self.grace_days,
            'escalation_rate': self.escalation_rate,
            'auto_escalate':   self.auto_escalate,
            'apply_wht':       self.apply_wht,
            'break_clause':    self.break_clause,
            'subletting_allowed': self.subletting,
            'notes':           self.conditions,
        }
        if lease.date_start and self.duration_months:
            vals['date_end'] = lease.date_start + relativedelta(months=self.duration_months)
        lease.write(vals)
        lease.message_post(body=_(f"Template '{self.name}' applied."))
