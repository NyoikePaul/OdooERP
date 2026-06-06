"""
M-Pesa STK Push directly from Odoo invoices.
Kenya-specific: tenants pay rent by receiving an STK push on their phone.
"""
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class AccountMoveMpesa(models.Model):
    _inherit = 'account.move'

    mpesa_phone      = fields.Char("Tenant M-Pesa Phone", compute='_compute_mpesa_phone', store=True)
    mpesa_txn_ids    = fields.One2many('mpesa.transaction', 'invoice_id', string="M-Pesa Payments")
    mpesa_txn_count  = fields.Integer(compute='_compute_mpesa_count', string="M-Pesa Payments")
    mpesa_paid       = fields.Boolean(compute='_compute_mpesa_paid', string="Paid via M-Pesa", store=True)
    mpesa_receipt    = fields.Char("M-Pesa Receipt", compute='_compute_mpesa_paid', store=True)

    @api.depends('partner_id.phone', 'partner_id.mobile')
    def _compute_mpesa_phone(self):
        for r in self:
            r.mpesa_phone = r.partner_id.mobile or r.partner_id.phone or ''

    def _compute_mpesa_count(self):
        for r in self:
            r.mpesa_txn_count = len(r.mpesa_txn_ids)

    @api.depends('mpesa_txn_ids.status', 'mpesa_txn_ids.mpesa_receipt')
    def _compute_mpesa_paid(self):
        for r in self:
            paid = r.mpesa_txn_ids.filtered(lambda t: t.status == 'success')
            r.mpesa_paid    = bool(paid)
            r.mpesa_receipt = paid[:1].mpesa_receipt or ''

    def action_mpesa_stk_push(self):
        """Send STK Push to tenant's phone for this invoice."""
        self.ensure_one()
        if self.payment_state == 'paid':
            raise UserError(_("Invoice already paid."))
        phone = self.mpesa_phone
        if not phone:
            raise UserError(_(
                "No phone number on tenant %s. "
                "Add mobile number in Contacts first.") % self.partner_id.name)

        connector = self.env['mpesa.connector']
        ref = (self.name or 'INV')[:12]
        desc = ("Rent %s" % (self.invoice_date.strftime('%b %Y') if self.invoice_date else ''))[:13]

        result = connector.stk_push(
            phone=phone,
            amount=self.amount_residual,
            account_ref=ref,
            description=desc,
        )

        # Create transaction record
        txn = self.env['mpesa.transaction'].create({
            'transaction_type':   'stk_push',
            'phone':              phone,
            'partner_id':         self.partner_id.id,
            'amount':             self.amount_residual,
            'account_ref':        ref,
            'invoice_id':         self.id,
            'lease_id':           self.lease_id.id if self.lease_id else False,
            'checkout_request_id': result.get('checkout_request_id'),
            'merchant_request_id': result.get('merchant_request_id'),
            'status':             'pending',
        })

        self.message_post(
            body=_("STK Push sent to %s for KES %.0f. "
                   "Transaction: %s. Customer message: %s") % (
                phone, self.amount_residual, txn.name,
                result.get('customer_message', '')),
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('STK Push Sent'),
                'message': _('M-Pesa prompt sent to %s. KES %.0f.') % (phone, self.amount_residual),
                'type': 'success',
            }
        }

    def action_open_mpesa_txns(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('M-Pesa Payments'),
            'res_model': 'mpesa.transaction', 'view_mode': 'list,form',
            'domain': [('invoice_id', '=', self.id)],
        }
