from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta


class RentPaymentWizard(models.TransientModel):
    _name = 'estate.rent.payment.wizard'
    _description = 'Generate Bulk Rent Invoices'

    lease_ids = fields.Many2many(
        'estate.lease', string="Leases",
        default=lambda self: self._default_leases(),
        domain=[('status', '=', 'active')]
    )
    invoice_date = fields.Date("Invoice Date", default=fields.Date.today)
    due_date     = fields.Date("Due Date",
        default=lambda s: fields.Date.today() + relativedelta(days=5))
    send_email   = fields.Boolean("Send Invoice by Email", default=False)
    note         = fields.Text("Notes on Invoice")

    def _default_leases(self):
        return self.env['estate.lease'].search([('status', '=', 'active')])

    def action_generate_invoices(self):
        if not self.lease_ids:
            raise UserError(_("Please select at least one active lease."))

        invoices = self.env['account.move']
        for lease in self.lease_ids:
            inv = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': lease.tenant_id.id,
                'lease_id': lease.id,
                'invoice_date': self.invoice_date,
                'invoice_date_due': self.due_date,
                'narration': self.note or f'Rent for {lease.property_id.name}',
                'invoice_line_ids': [(0, 0, {
                    'name': f'Monthly Rent — {lease.property_id.name} '
                            f'({self.invoice_date.strftime("%B %Y")})',
                    'quantity': 1,
                    'price_unit': lease.monthly_rent,
                })]
            })
            invoices |= inv

        if self.send_email:
            for inv in invoices:
                inv.action_send_and_print()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Rent Invoices Generated'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', invoices.ids)],
        }
