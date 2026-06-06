"""
M-Pesa Daraja 2.0 — Enterprise Kenya Payment Connector
Handles: STK Push, C2B, B2C, Reversal, Balance, Transaction Status
"""
import requests
import base64
import json
import re
import logging
from datetime import datetime
from functools import wraps
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

DARAJA_BASE = {
    'sandbox': 'https://sandbox.safaricom.co.ke',
    'production': 'https://api.safaricom.co.ke',
}


def daraja_retry(max_retries=3):
    """Retry decorator for Daraja API calls."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.Timeout as e:
                    last_error = e
                    _logger.warning("Daraja timeout attempt %d/%d: %s", attempt, max_retries, e)
                except requests.exceptions.ConnectionError as e:
                    last_error = e
                    _logger.warning("Daraja connection error attempt %d/%d: %s", attempt, max_retries, e)
            raise UserError(_("Daraja API unavailable after %d attempts: %s") % (max_retries, last_error))
        return wrapper
    return decorator


def normalize_phone(phone):
    """Normalize phone to 2547XXXXXXXX format."""
    if not phone:
        raise ValidationError(_("Phone number is required."))
    phone = re.sub(r'\D', '', str(phone))
    if phone.startswith('0') and len(phone) == 10:
        phone = '254' + phone[1:]
    elif phone.startswith('7') and len(phone) == 9:
        phone = '254' + phone
    elif phone.startswith('+254'):
        phone = phone[1:]
    if not re.match(r'^2547\d{8}$', phone) and not re.match(r'^2541\d{8}$', phone):
        raise ValidationError(_("Invalid Kenya phone number: %s. Use 07XXXXXXXX or 2547XXXXXXXX format.") % phone)
    return phone


class MpesaConnector(models.AbstractModel):
    _name = 'mpesa.connector'
    _description = 'M-Pesa Daraja 2.0 API Connector'

    def _get_daraja_config(self):
        """Get active M-Pesa configuration from payment provider."""
        provider = self.env['payment.provider'].search(
            [('code', '=', 'mpesa'), ('state', 'in', ('enabled', 'test'))], limit=1)
        if not provider:
            raise UserError(_("No active M-Pesa payment provider configured. "
                               "Go to Invoicing > Configuration > Payment Providers."))
        return provider

    def _get_base_url(self, provider):
        env = 'production' if provider.state == 'enabled' else 'sandbox'
        return DARAJA_BASE[env]

    @daraja_retry(3)
    def _get_access_token(self, provider):
        """Get OAuth2 access token with 55-minute cache."""
        cache_key = f'mpesa_token_{provider.id}'
        cached = self.env['ir.config_parameter'].sudo().get_param(cache_key)
        expiry_key = f'mpesa_token_expiry_{provider.id}'
        expiry = self.env['ir.config_parameter'].sudo().get_param(expiry_key)

        now = datetime.now().timestamp()
        if cached and expiry and float(expiry) > now:
            return cached

        base_url = self._get_base_url(provider)
        consumer_key = provider.mpesa_consumer_key
        consumer_secret = provider.mpesa_consumer_secret

        if not consumer_key or not consumer_secret:
            raise UserError(_("M-Pesa Consumer Key and Secret are required."))

        credentials = base64.b64encode(
            f"{consumer_key}:{consumer_secret}".encode()).decode()

        resp = requests.get(
            f"{base_url}/oauth/v1/generate?grant_type=client_credentials",
            headers={'Authorization': f'Basic {credentials}'},
            timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
        token = data.get('access_token')
        if not token:
            raise UserError(_("Failed to get access token: %s") % data)

        # Cache for 55 minutes (token valid 60 min)
        self.env['ir.config_parameter'].sudo().set_param(cache_key, token)
        self.env['ir.config_parameter'].sudo().set_param(
            expiry_key, str(now + 3300))

        _logger.info("M-Pesa access token refreshed for provider %s", provider.name)
        return token

    def _get_headers(self, provider):
        token = self._get_access_token(provider)
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }

    def _generate_password(self, shortcode, passkey, timestamp):
        """Generate LipaNaMpesa online password."""
        raw = f"{shortcode}{passkey}{timestamp}"
        return base64.b64encode(raw.encode()).decode()

    @daraja_retry(3)
    def stk_push(self, phone, amount, account_ref, description, callback_url=None):
        """Initiate STK Push (Lipa na M-Pesa Online)."""
        provider = self._get_daraja_config()
        phone = normalize_phone(phone)
        base_url = self._get_base_url(provider)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        shortcode = provider.mpesa_shortcode
        passkey = provider.mpesa_passkey

        password = self._generate_password(shortcode, passkey, timestamp)
        callback = callback_url or provider.mpesa_callback_url or \
            f"{self.env['ir.config_parameter'].sudo().get_param('web.base.url')}/mpesa/stk/callback"

        payload = {
            'BusinessShortCode': shortcode,
            'Password': password,
            'Timestamp': timestamp,
            'TransactionType': 'CustomerPayBillOnline',
            'Amount': int(amount),
            'PartyA': phone,
            'PartyB': shortcode,
            'PhoneNumber': phone,
            'CallBackURL': callback,
            'AccountReference': str(account_ref)[:12],
            'TransactionDesc': str(description)[:13],
        }

        resp = requests.post(
            f"{base_url}/mpesa/stkpush/v1/processrequest",
            json=payload,
            headers=self._get_headers(provider),
            timeout=30
        )
        data = resp.json()
        _logger.info("STK Push response: %s", data)

        if data.get('ResponseCode') != '0':
            raise UserError(
                _("STK Push failed: %s") % data.get('errorMessage', data.get('ResponseDescription', str(data))))

        return {
            'merchant_request_id': data.get('MerchantRequestID'),
            'checkout_request_id': data.get('CheckoutRequestID'),
            'response_code': data.get('ResponseCode'),
            'customer_message': data.get('CustomerMessage'),
        }

    @daraja_retry(3)
    def stk_query(self, checkout_request_id):
        """Query STK Push status."""
        provider = self._get_daraja_config()
        base_url = self._get_base_url(provider)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        shortcode = provider.mpesa_shortcode
        password = self._generate_password(shortcode, provider.mpesa_passkey, timestamp)

        payload = {
            'BusinessShortCode': shortcode,
            'Password': password,
            'Timestamp': timestamp,
            'CheckoutRequestID': checkout_request_id,
        }
        resp = requests.post(
            f"{base_url}/mpesa/stkpushquery/v1/query",
            json=payload,
            headers=self._get_headers(provider),
            timeout=30
        )
        return resp.json()

    @daraja_retry(3)
    def register_c2b_urls(self, confirmation_url=None, validation_url=None):
        """Register C2B callback URLs."""
        provider = self._get_daraja_config()
        base_url = self._get_base_url(provider)
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        payload = {
            'ShortCode': provider.mpesa_shortcode,
            'ResponseType': 'Completed',
            'ConfirmationURL': confirmation_url or f"{base}/mpesa/c2b/confirmation",
            'ValidationURL': validation_url or f"{base}/mpesa/c2b/validation",
        }
        resp = requests.post(
            f"{base_url}/mpesa/c2b/v1/registerurl",
            json=payload,
            headers=self._get_headers(provider),
            timeout=30
        )
        data = resp.json()
        _logger.info("C2B URL registration: %s", data)
        return data

    @daraja_retry(3)
    def b2c_payment(self, phone, amount, occasion, remarks):
        """Send B2C payment (e.g. refunds, landlord payouts)."""
        provider = self._get_daraja_config()
        phone = normalize_phone(phone)
        base_url = self._get_base_url(provider)
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        payload = {
            'InitiatorName': provider.mpesa_initiator_name or 'testapi',
            'SecurityCredential': provider.mpesa_security_credential or '',
            'CommandID': 'BusinessPayment',
            'Amount': int(amount),
            'PartyA': provider.mpesa_shortcode,
            'PartyB': phone,
            'Remarks': str(remarks)[:100],
            'QueueTimeOutURL': f"{base}/mpesa/b2c/timeout",
            'ResultURL': f"{base}/mpesa/b2c/result",
            'Occasion': str(occasion)[:100],
        }
        resp = requests.post(
            f"{base_url}/mpesa/b2c/v1/paymentrequest",
            json=payload,
            headers=self._get_headers(provider),
            timeout=30
        )
        return resp.json()

    @daraja_retry(3)
    def account_balance(self):
        """Query M-Pesa account balance."""
        provider = self._get_daraja_config()
        base_url = self._get_base_url(provider)
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        payload = {
            'Initiator': provider.mpesa_initiator_name or 'testapi',
            'SecurityCredential': provider.mpesa_security_credential or '',
            'CommandID': 'AccountBalance',
            'PartyA': provider.mpesa_shortcode,
            'IdentifierType': '4',
            'Remarks': 'Balance Query',
            'QueueTimeOutURL': f"{base}/mpesa/balance/timeout",
            'ResultURL': f"{base}/mpesa/balance/result",
        }
        resp = requests.post(
            f"{base_url}/mpesa/accountbalance/v1/query",
            json=payload,
            headers=self._get_headers(provider),
            timeout=30
        )
        return resp.json()

    @daraja_retry(3)
    def transaction_status(self, transaction_id):
        """Query transaction status."""
        provider = self._get_daraja_config()
        base_url = self._get_base_url(provider)
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        payload = {
            'Initiator': provider.mpesa_initiator_name or 'testapi',
            'SecurityCredential': provider.mpesa_security_credential or '',
            'CommandID': 'TransactionStatusQuery',
            'TransactionID': transaction_id,
            'PartyA': provider.mpesa_shortcode,
            'IdentifierType': '4',
            'ResultURL': f"{base}/mpesa/status/result",
            'QueueTimeOutURL': f"{base}/mpesa/status/timeout",
            'Remarks': 'Status Query',
            'Occasion': '',
        }
        resp = requests.post(
            f"{base_url}/mpesa/transactionstatus/v1/query",
            json=payload,
            headers=self._get_headers(provider),
            timeout=30
        )
        return resp.json()

    @daraja_retry(3)
    def reversal(self, transaction_id, amount, remarks):
        """Reverse an M-Pesa transaction."""
        provider = self._get_daraja_config()
        base_url = self._get_base_url(provider)
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        payload = {
            'Initiator': provider.mpesa_initiator_name or 'testapi',
            'SecurityCredential': provider.mpesa_security_credential or '',
            'CommandID': 'TransactionReversal',
            'TransactionID': transaction_id,
            'Amount': int(amount),
            'ReceiverParty': provider.mpesa_shortcode,
            'RecieverIdentifierType': '4',
            'ResultURL': f"{base}/mpesa/reversal/result",
            'QueueTimeOutURL': f"{base}/mpesa/reversal/timeout",
            'Remarks': str(remarks)[:100],
            'Occasion': '',
        }
        resp = requests.post(
            f"{base_url}/mpesa/reversal/v1/request",
            json=payload,
            headers=self._get_headers(provider),
            timeout=30
        )
        return resp.json()
