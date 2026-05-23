from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('mpesa', 'M-Pesa Kenya')],
        ondelete={'mpesa': 'set default'}
    )

    # ── Daraja Credentials ────────────────────────────
    mpesa_consumer_key    = fields.Char("Consumer Key",       groups="base.group_system")
    mpesa_consumer_secret = fields.Char("Consumer Secret",    groups="base.group_system")
    mpesa_shortcode       = fields.Char("Business Shortcode")
    mpesa_passkey         = fields.Char("Lipa Na M-Pesa Passkey", groups="base.group_system")
    mpesa_callback_url    = fields.Char("Callback URL",
                                        default="/payment/mpesa/callback")
    mpesa_sandbox         = fields.Boolean("Use Sandbox / Test Mode", default=True)

    # ── B2C / Advanced ───────────────────────────────
    mpesa_initiator_name  = fields.Char("Initiator Name",
                                        help="For B2C/reversal/balance queries")
    mpesa_security_cred   = fields.Char("Security Credential",
                                        groups="base.group_system",
                                        help="Encrypted initiator password from Daraja portal")
    mpesa_b2c_shortcode   = fields.Char("B2C Shortcode",
                                        help="Leave blank if same as business shortcode")

    # ── Token Status ──────────────────────────────────
    mpesa_token_status    = fields.Char("Token Status", readonly=True)

    # ── Helpers ───────────────────────────────────────
    def _mpesa_get_token(self):
        self.ensure_one()
        if self.code != 'mpesa':
            raise UserError(_("Provider is not M-Pesa"))
        mixin = self.env['mpesa.api.mixin']
        return mixin._get_access_token(
            self.mpesa_consumer_key,
            self.mpesa_consumer_secret,
            sandbox=self.mpesa_sandbox,
        )

    def _mpesa_get_callback_url(self, path='/payment/mpesa/callback'):
        base = self.get_base_url()
        return base.rstrip('/') + path

    # ── Actions ───────────────────────────────────────
    def action_test_mpesa_connection(self):
        self.ensure_one()
        if not self.mpesa_consumer_key or not self.mpesa_consumer_secret:
            raise UserError(_("Please enter Consumer Key and Secret first."))
        try:
            token = self._mpesa_get_token()
            self.mpesa_token_status = 'Connected ✅'
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title':   _('M-Pesa Connected'),
                    'message': _('Daraja credentials are valid ✅ Token obtained successfully.'),
                    'type':    'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            self.mpesa_token_status = f'Failed ❌'
            raise UserError(str(e)) from e

    def action_register_c2b_urls(self):
        self.ensure_one()
        try:
            mixin = self.env['mpesa.api.mixin']
            token = self._mpesa_get_token()
            result = mixin._c2b_register_urls(
                token=token,
                shortcode=self.mpesa_shortcode,
                confirmation_url=self._mpesa_get_callback_url('/payment/mpesa/c2b/confirm'),
                validation_url=self._mpesa_get_callback_url('/payment/mpesa/c2b/validate'),
                sandbox=self.mpesa_sandbox,
            )
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title':   _('C2B URLs Registered'),
                    'message': str(result),
                    'type':    'success',
                }
            }
        except Exception as e:
            raise UserError(str(e)) from e

    def action_initiate_stk_push(self):
        """Open STK Push wizard."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Initiate STK Push'),
            'res_model': 'mpesa.stk.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_provider_id': self.id},
        }
