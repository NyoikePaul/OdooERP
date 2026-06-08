from odoo import models, fields, api, _
from odoo.exceptions import UserError


class EstateTenantScreening(models.Model):
    _name        = 'estate.tenant.screening'
    _description = 'Tenant Screening Application'
    _inherit     = ['mail.thread', 'mail.activity.mixin']
    _order       = 'create_date desc'

    name           = fields.Char("Application Ref", readonly=True, copy=False, default='New')
    property_id    = fields.Many2one('estate.property', required=True)
    unit_id        = fields.Many2one('estate.unit')
    applicant_id   = fields.Many2one('res.partner', required=True, tracking=True)
    desired_date   = fields.Date("Desired Move-In")
    currency_id    = fields.Many2one('res.currency', default=lambda s: s.env.ref('base.KES'))
    employment_type = fields.Selection([
        ('employed','Employed'),('self','Self-Employed'),
        ('business','Business Owner'),('student','Student'),('retired','Retired'),
    ], default='employed')
    employer       = fields.Char("Employer / Business")
    monthly_income = fields.Monetary("Monthly Net Income", currency_field='currency_id')
    income_ratio   = fields.Float("Income/Rent Ratio", compute='_compute_score', store=True)
    hr_contact     = fields.Char("HR Contact")
    employer_verified = fields.Boolean("Employer Verified")
    has_id         = fields.Boolean("National ID / Passport")
    has_payslips   = fields.Boolean("3-Month Bank Statements")
    has_ref_letter = fields.Boolean("Previous Landlord Reference")
    has_intro      = fields.Boolean("Employer Introduction Letter")
    has_kra_pin    = fields.Boolean("KRA PIN")
    kra_pin        = fields.Char("KRA PIN Number")
    prev_landlord  = fields.Char("Previous Landlord Name")
    prev_phone     = fields.Char("Previous Landlord Phone")
    prev_ref       = fields.Selection([
        ('excellent','Excellent'),('good','Good'),('fair','Fair'),
        ('poor','Poor'),('unknown','Not Verified'),
    ], default='unknown')
    score          = fields.Integer("Screening Score /100", compute='_compute_score', store=True)
    recommendation = fields.Selection([('approve','Approve'),('review','Review'),('reject','Reject')],
                                       compute='_compute_score', store=True)
    status         = fields.Selection([
        ('new','New'),('screening','Under Review'),
        ('approved','Approved'),('rejected','Rejected'),('converted','Converted'),
    ], default='new', tracking=True)
    notes          = fields.Text()

    @api.depends('monthly_income','property_id.monthly_rent',
                 'has_id','has_payslips','has_ref_letter','has_intro','has_kra_pin',
                 'employer_verified','prev_ref')
    def _compute_score(self):
        ref_scores = {'excellent':15,'good':10,'fair':5,'poor':-20,'unknown':0}
        for r in self:
            rent = r.property_id.monthly_rent or 1
            ratio = r.monthly_income / rent
            r.income_ratio = ratio
            s  = 0
            s += 20 if r.has_id else 0
            s += 20 if r.has_payslips else 0
            s += 15 if r.has_ref_letter else 0
            s += 10 if r.has_intro else 0
            s += 5  if r.has_kra_pin else 0
            s += 10 if r.employer_verified else 0
            s += (20 if ratio >= 4 else 15 if ratio >= 3 else 5 if ratio >= 2 else 0)
            s += ref_scores.get(r.prev_ref, 0)
            s  = max(0, min(100, s))
            r.score          = s
            r.recommendation = ('approve' if s>=70 else 'review' if s>=50 else 'reject')

    def action_approve(self):
        self.write({'status':'approved'})
        self.message_post(body=_(f"Approved. Score: {self.score}/100. Income ratio: {self.income_ratio:.1f}x"))

    def action_reject(self):
        self.write({'status':'rejected'})

    def action_convert(self):
        self.ensure_one()
        if self.status != 'approved':
            raise UserError(_("Approve the application first."))
        lease = self.env['estate.lease'].create({
            'property_id': self.property_id.id,
            'unit_id':     self.unit_id.id if self.unit_id else False,
            'tenant_id':   self.applicant_id.id,
            'date_start':  self.desired_date or fields.Date.today(),
        })
        self.write({'status':'converted'})
        return {'type':'ir.actions.act_window','res_model':'estate.lease','res_id':lease.id,'view_mode':'form'}

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name','New')=='New':
                v['name'] = self.env['ir.sequence'].next_by_code('estate.tenant.screening') or 'New'
        return super().create(vals_list)
