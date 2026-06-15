"""
Generate Installment Plan Wizard
=================================
Quick-generate a standard Kenya off-plan schedule from templates.
"""
from odoo import models, fields, api, _
from odoo.exceptions import UserError


TEMPLATES = {
    'standard': [
        ('booking',    'Booking Deposit',  10),
        ('foundation', 'Foundation',       20),
        ('slab',       'Slab / Floor',     20),
        ('roofing',    'Roofing',          30),
        ('handover',   'Handover Balance', 20),
    ],
    'affordable': [
        ('booking',    'Booking Deposit',  5),
        ('foundation', 'Foundation',       15),
        ('walling',    'Walling',          20),
        ('roofing',    'Roofing',          30),
        ('finishing',  'Finishing',        20),
        ('handover',   'Handover Balance', 10),
    ],
    'luxury': [
        ('booking',    'Booking Deposit',  20),
        ('foundation', 'Foundation',       20),
        ('slab',       'Slab / Floor',     15),
        ('roofing',    'Roofing',          25),
        ('handover',   'Handover Balance', 20),
    ],
    'rental_deposit': [
        ('booking',    'Security Deposit', 100),
    ],
}


class GenerateInstallmentWizard(models.TransientModel):
    _name        = 'estate.generate.installment.wizard'
    _description = 'Generate Installment Plan'

    property_id  = fields.Many2one('estate.property', string='Property', required=True)
    partner_id   = fields.Many2one('res.partner', string='Buyer', required=True)
    total_price  = fields.Monetary('Total Sale Price (KES)', currency_field='currency_id', required=True)
    currency_id  = fields.Many2one('res.currency', default=lambda s: s.env.ref('base.KES'))
    discount_pct = fields.Float('Discount (%)', default=0)
    date_handover= fields.Date('Expected Handover Date')
    template     = fields.Selection([
        ('standard',       'Standard (10-20-20-30-20)'),
        ('affordable',     'Affordable Housing (5-15-20-30-20-10)'),
        ('luxury',         'Luxury (20-20-15-25-20)'),
        ('rental_deposit', 'Rental Security Deposit (100%)'),
        ('custom',         'Custom — I will add milestones manually'),
    ], string='Payment Schedule Template', default='standard', required=True)

    def action_generate(self):
        self.ensure_one()
        if self.template == 'custom':
            plan = self.env['estate.installment.plan'].create({
                'property_id':  self.property_id.id,
                'partner_id':   self.partner_id.id,
                'total_price':  self.total_price,
                'discount_pct': self.discount_pct,
                'date_handover':self.date_handover,
            })
        else:
            milestones = TEMPLATES[self.template]
            lines = []
            for seq, (mtype, mname, pct) in enumerate(milestones, start=10):
                lines.append((0, 0, {
                    'sequence':       seq * 10,
                    'name':           mname,
                    'milestone_type': mtype,
                    'percentage':     pct,
                }))
            plan = self.env['estate.installment.plan'].create({
                'property_id':   self.property_id.id,
                'partner_id':    self.partner_id.id,
                'total_price':   self.total_price,
                'discount_pct':  self.discount_pct,
                'date_handover': self.date_handover,
                'line_ids':      lines,
            })
        return {
            'type':      'ir.actions.act_window',
            'res_model': 'estate.installment.plan',
            'res_id':    plan.id,
            'view_mode': 'form',
        }
