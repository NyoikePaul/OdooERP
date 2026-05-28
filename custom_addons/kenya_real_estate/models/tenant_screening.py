"""
Tenant Screening — Kenya
Critical because Kenya has no formal credit bureau for most individuals.
Landlords rely on: employment letters, 3-month bank statements,
references from previous landlords, employer verification.
"""
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class EstateTenantScreening(models.Model):
    _name        = 'estate.tenant.screening'
    _description = 'Tenant Screening / Application'
    _inherit     = ['mail.thread', 'mail.activity.mixin']
    _order       = 'create_date desc'

    name         = fields.Char("Application Ref", readonly=True, default='New')
    property_id  = fields.Many2one('estate.property', string="Property", required=True)
    unit_id      = fields.Many2one('estate.unit', string="Unit")
    applicant_id = fields.Many2one('res.partner', string="Applicant", required=True, tracking=True)
    desired_date = fields.Date("Desired Move-In Date")

    # Employment / Income Verification
    employer_name     = fields.Char("Employer / Business Name")
    employment_type   = fields.Selection([
        ('employed',    'Formally Employed'),
        ('self',        'Self Employed'),
        ('business',    'Business Owner'),
        ('student',     'Student'),
        ('retired',     'Retired'),
    ], default='employed')
    monthly_income    = fields.Monetary("Monthly Net Income (KES)", currency_field='currency_id')
    currency_id       = fields.Many2one('res.currency',
                                        default=lambda s: s.env.ref('base.KES'))
    income_multiplier = fields.Float("Income/Rent Ratio", compute='_compute_ratio', store=True)
    hr_contact        = fields.Char("HR Contact / Phone")
    employer_verified = fields.Boolean("Employer Verified", tracking=True)

    # Documents Received
    has_id            = fields.Boolean("National ID / Passport")
    has_payslips      = fields.Boolean("3-Month Payslips / Bank Statements")
    has_ref_letter    = fields.Boolean("Previous Landlord Reference")
    has_intro_letter  = fields.Boolean("Introduction Letter (Employer)")
    has_kra_pin       = fields.Boolean("KRA PIN")
    kra_pin           = fields.Char("KRA PIN Number")

    # Scoring
    score            = fields.Integer("Screening Score", compute='_compute_score', store=True)
    recommendation   = fields.Selection([
        ('approve',  'Approve'),
        ('review',   'Needs Review'),
        ('reject',   'Reject'),
    ], compute='_compute_score', store=True)

    previous_landlord = fields.Char("Previous Landlord Name")
    prev_landlord_phone = fields.Char("Previous Landlord Phone")
    prev_landlord_ref  = fields.Selection([
        ('excellent', 'Excellent Tenant'),
        ('good',      'Good Tenant'),
        ('fair',      'Had Some Issues'),
        ('poor',      'Would Not Recommend'),
        ('unknown',   'Not Verified'),
    ], default='unknown')

    status = fields.Selection([
        ('new',       'New Application'),
        ('screening', 'Under Review'),
        ('approved',  'Approved'),
        ('rejected',  'Rejected'),
        ('converted', 'Converted to Lease'),
    ], default='new', tracking=True)

    notes = fields.Text("Notes")

    @api.depends('monthly_income', 'property_id.monthly_rent')
    def _compute_ratio(self):
        for rec in self:
            rent = rec.property_id.monthly_rent
            rec.income_multiplier = (rec.monthly_income / rent) if rent else 0

    @api.depends('has_id', 'has_payslips', 'has_ref_letter', 'has_intro_letter',
                 'has_kra_pin', 'employer_verified', 'income_multiplier',
                 'prev_landlord_ref')
    def _compute_score(self):
        for rec in self:
            score = 0
            if rec.has_id:            score += 20
            if rec.has_payslips:      score += 20
            if rec.has_ref_letter:    score += 15
            if rec.has_intro_letter:  score += 10
            if rec.has_kra_pin:       score += 5
            if rec.employer_verified: score += 10
            # Income ratio: should be at least 3x rent
            if rec.income_multiplier >= 4:   score += 20
            elif rec.income_multiplier >= 3: score += 15
            elif rec.income_multiplier >= 2: score += 5
            # Previous landlord reference
            ref_score = {'excellent': 15, 'good': 10, 'fair': 5, 'poor': -20, 'unknown': 0}
            score += ref_score.get(rec.prev_landlord_ref, 0)
            score = max(0, min(100, score))
            rec.score = score
            if score >= 70:   rec.recommendation = 'approve'
            elif score >= 50: rec.recommendation = 'review'
            else:             rec.recommendation = 'reject'

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name', 'New') == 'New':
                v['name'] = self.env['ir.sequence'].next_by_code('estate.tenant.screening') or 'New'
        return super().create(vals_list)

    def action_approve(self):
        self.write({'status': 'approved'})
        self.message_post(body=_(f"Application approved. Score: {self.score}/100. "
                                 f"Income ratio: {self.income_multiplier:.1f}x rent."))

    def action_reject(self):
        self.write({'status': 'rejected'})
        self.message_post(body=_(f"Application rejected. Score: {self.score}/100."))

    def action_convert_to_lease(self):
        """Create draft lease from approved application."""
        self.ensure_one()
        if self.status != 'approved':
            raise UserError(_("Approve the application first."))
        lease = self.env['estate.lease'].create({
            'property_id': self.property_id.id,
            'unit_id':     self.unit_id.id if self.unit_id else False,
            'tenant_id':   self.applicant_id.id,
            'date_start':  self.desired_date or fields.Date.today(),
        })
        self.write({'status': 'converted'})
        return {
            'type':      'ir.actions.act_window',
            'res_model': 'estate.lease',
            'res_id':    lease.id,
            'view_mode': 'form',
        }
