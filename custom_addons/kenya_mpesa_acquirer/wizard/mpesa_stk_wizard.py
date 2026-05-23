from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MpesaStkWizard(models.TransientModel):
    _name        = 'mpesa.stk.wizard'
    _description = 'Initiate M-Pesa STK Push'

    provider_id  = fields.Many2one('payment.provider', string="Provider",
                                   domain=[('code','=','mpesa')], required=True)
    phone        = fields.Char("Phone Number", required=True,
)
    amount       = fields.Monetary("Amount (KES)", currency_field='currency_id',
                                   required=True)
    currency_id  = fields.Many2one('res.currency',
                                   default=lambda s: s.env.ref('base.KES'))
    account_ref  = fields.Char("Account Reference", required=True,
)
    invoice_id   = fields.Many2one('account.move', string="Invoice (optional)",
                                   domain=[('move_type','=','out_invoice'),
                                           ('payment_state','!=','paid')])
    partner_id   = fields.Many2one('res.partner', string="Customer")
    description  = fields.Char("Description", default="Payment")

    @api.onchange('invoice_id')
    def _onchange_invoice(self):
        if self.invoice_id:
            self.amount      = self.invoice_id.amount_residual
            self.account_ref = self.invoice_id.name
            self.partner_id  = self.invoice_id.partner_id
            if self.invoice_id.partner_id.phone:
                self.phone   = self.invoice_id.partner_id.phone

    def action_send_stk(self):
        self.ensure_one()
        provider = self.provider_id
        mixin    = self.env['mpesa.api.mixin']

        try:
            phone = mixin._format_phone(self.phone)
        except UserError as e:
            raise UserError(str(e)) from e

        try:
            token  = provider._mpesa_get_token()
            result = mixin._stk_push(
                token        = token,
                shortcode    = provider.mpesa_shortcode,
                passkey      = provider.mpesa_passkey,
                phone        = phone,
                amount       = self.amount,
                callback_url = provider._mpesa_get_callback_url(),
                account_ref  = self.account_ref,
                sandbox      = provider.mpesa_sandbox,
            )

            # Log pending transaction
            tx_vals = {
                'checkout_id':      result.get('CheckoutRequestID'),
                'merchant_id':      result.get('MerchantRequestID'),
                'phone':            phone,
                'amount':           self.amount,
                'status':           'pending',
                'transaction_type': 'stk',
                'partner_id':       self.partner_id.id if self.partner_id else False,
                'invoice_id':       self.invoice_id.id if self.invoice_id else False,
            }
            self.env['mpesa.transaction'].create(tx_vals)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title':   _('STK Push Sent!'),
                    'message': _(f'Payment request sent to {phone}. '
                                 f'Customer will receive a prompt on their phone.'),
                    'type':    'success',
                    'sticky': True,
                }
            }
        except Exception as e:
            raise UserError(str(e)) from e
