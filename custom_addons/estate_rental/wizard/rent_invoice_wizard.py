from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta


class EstateRentInvoiceWizard(models.TransientModel):
    _name        = 'estate.rent.invoice.wizard'
    _description = 'Generate Rent Invoices'

    invoice_date = fields.Date("Invoice Date", required=True, default=fields.Date.today)
    due_days     = fields.Integer("Due in (days)", default=5)
    lease_ids    = fields.Many2many('estate.lease', string="Leases",
                                    domain=[('status','=','active')])
    include_service_charge = fields.Boolean("Include Service Charges", default=True)
    notes        = fields.Text("Notes on Invoice")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_leases = self.env['estate.lease'].search([('status','=','active')])
        res['lease_ids'] = [(6,0, active_leases.ids)]
        return res

    def action_generate(self):
        self.ensure_one()
        if not self.lease_ids:
            raise UserError(_("No active leases selected."))
        invoices = []
        for lease in self.lease_ids:
            lines = [(0,0,{
                'name':f"Rent — {lease.property_id.name} ({self.invoice_date.strftime('%B %Y')})",
                'quantity':1,'price_unit':lease.monthly_rent,
            })]
            if self.include_service_charge and lease.service_charge:
                lines.append((0,0,{
                    'name':f"Service Charge — {self.invoice_date.strftime('%B %Y')}",
                    'quantity':1,'price_unit':lease.service_charge,
                }))
            inv = self.env['account.move'].create({
                'move_type':'out_invoice','partner_id':lease.tenant_id.id,
                'lease_id':lease.id,'invoice_date':self.invoice_date,
                'invoice_date_due':self.invoice_date + timedelta(days=self.due_days),
                'narration':self.notes or False,
                'invoice_line_ids':lines,
            })
            invoices.append(inv.id)
        return {'type':'ir.actions.act_window','name':_(f"Rent Invoices — {self.invoice_date.strftime('%B %Y')}"),
                'res_model':'account.move','view_mode':'list,form','domain':[('id','in',invoices)]}
