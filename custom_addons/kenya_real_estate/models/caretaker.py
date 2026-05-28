"""
Estate Caretaker / Facility Manager
Kenya-specific: most apartment blocks have a live-in caretaker
who collects rent, handles day-to-day issues, and manages access.
"""
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class EstateCaretaker(models.Model):
    _name        = 'estate.caretaker'
    _description = 'Caretaker / Facility Manager'
    _inherit     = ['mail.thread', 'mail.activity.mixin']

    name             = fields.Char("Full Name", required=True, tracking=True)
    id_number        = fields.Char("National ID / Passport", required=True)
    phone            = fields.Char("Phone (M-Pesa)", required=True)
    email            = fields.Char("Email")
    partner_id       = fields.Many2one('res.partner', string="Contact Record")

    currency_id      = fields.Many2one('res.currency',
                                       default=lambda s: s.env.ref('base.KES'))
    monthly_salary   = fields.Monetary("Monthly Salary (KES)", currency_field='currency_id')
    house_allowance  = fields.Monetary("House Allowance (KES)", currency_field='currency_id')
    # Caretaker often gets free housing — track which unit
    free_unit_id     = fields.Many2one('estate.unit', string="Free Housing Unit")

    building_ids     = fields.Many2many('estate.building', string="Manages Buildings")
    property_ids     = fields.Many2many('estate.property', string="Manages Properties")

    date_joined      = fields.Date("Date Joined")
    date_left        = fields.Date("Date Left")
    active           = fields.Boolean(default=True, tracking=True)

    # NHIF / NSSF compliance
    nhif_number      = fields.Char("NHIF Number")
    nssf_number      = fields.Char("NSSF Number")
    kra_pin          = fields.Char("KRA PIN")

    responsibilities = fields.Text("Responsibilities",
                                   default="1. Collect rent receipts from tenants\n"
                                           "2. Report maintenance issues immediately\n"
                                           "3. Manage tenant move-in/out\n"
                                           "4. Maintain compound cleanliness\n"
                                           "5. Record all visitors\n"
                                           "6. Ensure generator fuel is adequate")
    notes            = fields.Text("Notes")

    _sql_constraints = [
        ('id_number_unique', 'UNIQUE(id_number)', 'National ID must be unique.'),
    ]

    def action_pay_salary(self):
        """Create vendor bill for caretaker salary."""
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_("Please link a Contact Record before generating payment."))
        from odoo import fields as F
        total = self.monthly_salary + self.house_allowance
        bill  = self.env['account.move'].create({
            'move_type':  'in_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': F.Date.today(),
            'invoice_line_ids': [
                (0, 0, {
                    'name': f"Caretaker Salary — {self.name} — {F.Date.today().strftime('%B %Y')}",
                    'quantity': 1,
                    'price_unit': self.monthly_salary,
                }),
                (0, 0, {
                    'name': f"House Allowance — {self.name}",
                    'quantity': 1,
                    'price_unit': self.house_allowance,
                }),
            ]
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': bill.id,
            'view_mode': 'form',
        }
