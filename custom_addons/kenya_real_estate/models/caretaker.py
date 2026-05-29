from odoo import models, fields, api, _
from odoo.exceptions import UserError


class EstateCaretaker(models.Model):
    _name        = 'estate.caretaker'
    _description = 'Building Caretaker / Facility Manager'
    _inherit     = ['mail.thread', 'mail.activity.mixin']

    name         = fields.Char("Full Name", required=True)
    id_number    = fields.Char("National ID", required=True)
    phone        = fields.Char("M-Pesa Phone", required=True)
    email        = fields.Char("Email")
    partner_id   = fields.Many2one('res.partner', string="Contact")
    currency_id  = fields.Many2one('res.currency', default=lambda s: s.env.ref('base.KES'))
    monthly_salary   = fields.Monetary("Salary (KES)", currency_field='currency_id')
    house_allowance  = fields.Monetary("House Allowance (KES)", currency_field='currency_id')
    free_unit_id     = fields.Many2one('estate.unit', string="Free Housing Unit")
    building_ids     = fields.Many2many('estate.building', string="Manages Buildings")
    property_ids     = fields.Many2many('estate.property', string="Manages Properties")
    date_joined  = fields.Date("Date Joined")
    nhif_no      = fields.Char("NHIF Number")
    nssf_no      = fields.Char("NSSF Number")
    kra_pin      = fields.Char("KRA PIN")
    active       = fields.Boolean(default=True)
    notes        = fields.Text()

    _sql_constraints = [('id_number_unique','UNIQUE(id_number)','National ID must be unique.')]

    def action_pay_salary(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_("Link a Contact Record first."))
        total = self.monthly_salary + self.house_allowance
        bill  = self.env['account.move'].create({
            'move_type':'in_invoice','partner_id':self.partner_id.id,
            'invoice_date':fields.Date.today(),
            'invoice_line_ids':[(0,0,{
                'name':f"Caretaker Salary — {self.name} — {fields.Date.today().strftime('%B %Y')}",
                'quantity':1,'price_unit':self.monthly_salary,
            }),(0,0,{
                'name':f"House Allowance — {self.name}",
                'quantity':1,'price_unit':self.house_allowance,
            })]
        })
        return {'type':'ir.actions.act_window','res_model':'account.move','res_id':bill.id,'view_mode':'form'}
