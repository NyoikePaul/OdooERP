# -*- coding: utf-8 -*-
import requests
import json
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    etims_status = fields.Selection([
        ('unsubmitted', 'Not Sent'),
        ('pending', 'Pending Gateway Acknowledgement'),
        ('sent', 'Transmitted & Certified'),
        ('failed', 'Validation Error / Rejected')
    ], default='unsubmitted', string='eTIMS Status', copy=False, tracking=True)
    
    etims_receipt_number = fields.Char(string='KRA Internal Number', copy=False, readonly=True)
    etims_signature = fields.Char(string='SDG Device Signature', copy=False, readonly=True)
    etims_error_log = fields.Text(string='Compliance Rejection Log', copy=False, readonly=True)

    def action_post(self):
        """Intercept Odoo pipeline validation execution to fire eTIMS serialization arrays"""
        res = super(AccountMove, self).action_post()
        for move in self:
            if move.move_type in ['out_invoice', 'out_refund']:
                move._push_invoice_to_etims()
        return res

    def _push_invoice_to_etims(self):
        """Assembles structural JSON payload matching KRA automated middleware frameworks"""
        self.ensure_one()
        
        # Pull parameters dynamically from configuration records
        gateway_url = self.env['ir.config_parameter'].sudo().get_param('etims.api.url', 'https://api.etims-sandbox.kra.go.ke/v1/invoices')
        api_token = self.env['ir.config_parameter'].sudo().get_param('etims.api.token', 'MOCK_TOKEN_STRING')
        
        company_pin = self.env.company.vat or 'A000000000X'
        customer_pin = self.partner_id.vat or 'P000000000X'

        # Structure payload mapping matrix
        payload = {
            "invoiceNumber": self.name,
            "traderPin": company_pin,
            "customerPin": customer_pin,
            "customerName": self.partner_id.name,
            "invoiceDate": self.invoice_date.strftime('%Y%m%d') if self.invoice_date else fields.Date.context_today(self).strftime('%Y%m%d'),
            "paymentType": "01",  # Standard Cash/Bank code representation
            "lines": []
        }

        for line in self.invoice_line_ids.filtered(lambda l: not l.display_type):
            # Resolve complex item configurations to exact KRA Tax Categories (A=16%, B=0%, C=Exempt)
            kra_tax_code = "A"
            if line.tax_ids:
                tax = line.tax_ids[0]
                if tax.amount == 0:
                    kra_tax_code = "B" if tax.description and "ZERO" in tax.description.upper() else "C"

            payload["lines"].append({
                "itemCode": line.product_id.barcode or f"RE-ASSET-{line.id}",
                "itemName": line.name,
                "quantity": line.quantity,
                "unitPrice": line.price_unit,
                "taxCategory": kra_tax_code,
                "totalAmount": line.price_subtotal
            })

        try:
            self.write({'etims_status': 'pending'})
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f"Bearer {api_token}"
            }
            
            # Explicit network timeouts protect standard workflow loops from remote API degradation hangs
            response = requests.post(gateway_url, json=payload, headers=headers, timeout=12)
            
            if response.status_code in [200, 201]:
                res_data = response.json()
                if res_data.get('resultCode') == '000':  # KRA engine success acknowledgment state literal
                    self.write({
                        'etims_status': 'sent',
                        'etims_receipt_number': res_data.get('invoiceNumberKRA'),
                        'etims_signature': res_data.get('sdgSignature'),
                        'etims_error_log': False
                    })
                else:
                    self.write({
                        'etims_status': 'failed',
                        'etims_error_log': f"KRA Code [{res_data.get('resultCode')}]: {res_data.get('resultMessage')}"
                    })
            else:
                self.write({
                    'etims_status': 'failed',
                    'etims_error_log': f"Gateway HTTP Exception Code {response.status_code}: {response.text}"
                })
        except Exception as e:
            self.write({
                'etims_status': 'failed',
                'etims_error_log': f"Asynchronous marshalling exception trace: {str(e)}"
            })
