import base64
import logging
import time
import re
import requests
from datetime import datetime
from functools import wraps
from odoo import models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

DARAJA_SANDBOX = "https://sandbox.safaricom.co.ke"
DARAJA_LIVE    = "https://api.safaricom.co.ke"

# Token cache: {(consumer_key, sandbox): (token, expiry_timestamp)}
_TOKEN_CACHE = {}


def _retry(max_attempts=3, delay=1.5):
    """Retry decorator with exponential backoff."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except (requests.Timeout, requests.ConnectionError) as e:
                    last_exc = e
                    wait = delay * (2 ** (attempt - 1))
                    _logger.warning(
                        "Daraja call failed (attempt %d/%d), retrying in %.1fs: %s",
                        attempt, max_attempts, wait, e
                    )
                    time.sleep(wait)
                except Exception:
                    raise
            raise UserError(f"Daraja API unreachable after {max_attempts} attempts: {last_exc}")
        return wrapper
    return decorator


class MpesaAPIMixin(models.AbstractModel):
    _name        = "mpesa.api.mixin"
    _description = "M-Pesa Daraja 2.0 Full API Mixin"

    # ── Helpers ──────────────────────────────────────

    def _daraja_url(self, sandbox=False):
        return DARAJA_SANDBOX if sandbox else DARAJA_LIVE

    @staticmethod
    def _format_phone(phone):
        """Normalize phone to Daraja format: 2547XXXXXXXX."""
        phone = re.sub(r'\D', '', str(phone))
        if phone.startswith('0'):
            phone = '254' + phone[1:]
        elif phone.startswith('+'):
            phone = phone[1:]
        if not phone.startswith('254'):
            phone = '254' + phone
        if len(phone) != 12:
            raise UserError(f"Invalid Kenyan phone number: {phone}")
        return phone

    @staticmethod
    def _timestamp():
        return datetime.now().strftime("%Y%m%d%H%M%S")

    @staticmethod
    def _stk_password(shortcode, passkey, timestamp):
        raw = f"{shortcode}{passkey}{timestamp}"
        return base64.b64encode(raw.encode()).decode()

    # ── Authentication ────────────────────────────────

    @_retry(max_attempts=3)
    def _get_access_token(self, consumer_key, consumer_secret, sandbox=False):
        """Get OAuth2 access token with 55-minute cache."""
        cache_key = (consumer_key, sandbox)
        cached = _TOKEN_CACHE.get(cache_key)
        if cached:
            token, expiry = cached
            if time.time() < expiry:
                _logger.debug("Using cached Daraja token")
                return token

        creds = base64.b64encode(
            f"{consumer_key}:{consumer_secret}".encode()
        ).decode()

        r = requests.get(
            f"{self._daraja_url(sandbox)}/oauth/v1/generate"
            "?grant_type=client_credentials",
            headers={"Authorization": f"Basic {creds}"},
            timeout=10,
        )
        r.raise_for_status()
        data  = r.json()
        token = data.get("access_token")
        if not token:
            raise UserError("Daraja returned no access token")

        expires_in = int(data.get("expires_in", 3600))
        _TOKEN_CACHE[cache_key] = (token, time.time() + expires_in - 300)
        _logger.info("New Daraja token obtained (expires in %ds)", expires_in)
        return token

    # ── STK Push ─────────────────────────────────────

    @_retry(max_attempts=2)
    def _stk_push(self, token, shortcode, passkey, phone,
                  amount, callback_url, account_ref,
                  transaction_type="CustomerPayBillOnline", sandbox=False):
        """Initiate Lipa Na M-Pesa Online (STK Push)."""
        phone = self._format_phone(phone)
        ts    = self._timestamp()
        pwd   = self._stk_password(shortcode, passkey, ts)

        payload = {
            "BusinessShortCode": shortcode,
            "Password":          pwd,
            "Timestamp":         ts,
            "TransactionType":   transaction_type,
            "Amount":            int(amount),
            "PartyA":            phone,
            "PartyB":            shortcode,
            "PhoneNumber":       phone,
            "CallBackURL":       callback_url,
            "AccountReference":  account_ref[:12],
            "TransactionDesc":   f"Pay {account_ref}"[:13],
        }
        r = requests.post(
            f"{self._daraja_url(sandbox)}/mpesa/stkpush/v1/processrequest",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        r.raise_for_status()
        result = r.json()
        if result.get("ResponseCode") not in ("0", 0):
            raise UserError(
                f"STK Push rejected: {result.get('ResponseDescription', 'Unknown error')}"
            )
        return result

    # ── STK Query ────────────────────────────────────

    @_retry(max_attempts=2)
    def _stk_query(self, token, shortcode, passkey, checkout_request_id, sandbox=False):
        """Query STK Push transaction status."""
        ts  = self._timestamp()
        pwd = self._stk_password(shortcode, passkey, ts)

        payload = {
            "BusinessShortCode":  shortcode,
            "Password":           pwd,
            "Timestamp":          ts,
            "CheckoutRequestID":  checkout_request_id,
        }
        r = requests.post(
            f"{self._daraja_url(sandbox)}/mpesa/stkpushquery/v1/query",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()

    # ── C2B ──────────────────────────────────────────

    @_retry(max_attempts=2)
    def _c2b_register_urls(self, token, shortcode,
                           confirmation_url, validation_url,
                           response_type="Completed", sandbox=False):
        """Register C2B callback URLs for paybill/till."""
        payload = {
            "ShortCode":        shortcode,
            "ResponseType":     response_type,
            "ConfirmationURL":  confirmation_url,
            "ValidationURL":    validation_url,
        }
        r = requests.post(
            f"{self._daraja_url(sandbox)}/mpesa/c2b/v1/registerurl",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()

    @_retry(max_attempts=2)
    def _c2b_simulate(self, token, shortcode, phone,
                      amount, bill_ref, sandbox=True):
        """Simulate C2B payment (sandbox only)."""
        if not sandbox:
            raise UserError("C2B simulation only available in sandbox mode.")
        phone = self._format_phone(phone)
        payload = {
            "ShortCode":   shortcode,
            "CommandID":   "CustomerPayBillOnline",
            "Amount":      int(amount),
            "Msisdn":      phone,
            "BillRefNumber": bill_ref,
        }
        r = requests.post(
            f"{self._daraja_url(sandbox)}/mpesa/c2b/v1/simulate",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()

    # ── B2C ──────────────────────────────────────────

    @_retry(max_attempts=2)
    def _b2c_payment(self, token, initiator_name, security_credential,
                     shortcode, phone, amount, occasion,
                     remarks="Payment", command_id="BusinessPayment",
                     result_url=None, timeout_url=None, sandbox=False):
        """B2C — pay vendor, employee salary, or customer refund."""
        phone = self._format_phone(phone)
        payload = {
            "InitiatorName":      initiator_name,
            "SecurityCredential": security_credential,
            "CommandID":          command_id,
            "Amount":             int(amount),
            "PartyA":             shortcode,
            "PartyB":             phone,
            "Remarks":            remarks[:100],
            "QueueTimeOutURL":    timeout_url or "",
            "ResultURL":          result_url or "",
            "Occasion":           occasion[:100],
        }
        r = requests.post(
            f"{self._daraja_url(sandbox)}/mpesa/b2c/v3/paymentrequest",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        r.raise_for_status()
        return r.json()

    # ── Transaction Status ────────────────────────────

    @_retry(max_attempts=2)
    def _transaction_status(self, token, initiator, security_credential,
                            transaction_id, shortcode,
                            result_url=None, timeout_url=None, sandbox=False):
        """Query transaction status by Mpesa TransactionID."""
        payload = {
            "Initiator":          initiator,
            "SecurityCredential": security_credential,
            "CommandID":          "TransactionStatusQuery",
            "TransactionID":      transaction_id,
            "PartyA":             shortcode,
            "IdentifierType":     "4",
            "ResultURL":          result_url or "",
            "QueueTimeOutURL":    timeout_url or "",
            "Remarks":            "Status query",
            "Occasion":           "Status",
        }
        r = requests.post(
            f"{self._daraja_url(sandbox)}/mpesa/transactionstatus/v1/query",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()

    # ── Reversal ─────────────────────────────────────

    @_retry(max_attempts=2)
    def _reversal(self, token, initiator, security_credential,
                  transaction_id, amount, shortcode,
                  result_url=None, timeout_url=None, sandbox=False):
        """Reverse an M-Pesa transaction."""
        payload = {
            "Initiator":              initiator,
            "SecurityCredential":     security_credential,
            "CommandID":              "TransactionReversal",
            "TransactionID":          transaction_id,
            "Amount":                 int(amount),
            "ReceiverParty":          shortcode,
            "ReceiverIdentifierType": "4",
            "ResultURL":              result_url or "",
            "QueueTimeOutURL":        timeout_url or "",
            "Remarks":                "Reversal",
            "Occasion":               "Reversal",
        }
        r = requests.post(
            f"{self._daraja_url(sandbox)}/mpesa/reversal/v1/request",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()

    # ── Account Balance ───────────────────────────────

    @_retry(max_attempts=2)
    def _account_balance(self, token, initiator, security_credential,
                         shortcode, result_url=None, timeout_url=None, sandbox=False):
        """Query M-Pesa account balance."""
        payload = {
            "Initiator":          initiator,
            "SecurityCredential": security_credential,
            "CommandID":          "AccountBalance",
            "PartyA":             shortcode,
            "IdentifierType":     "4",
            "Remarks":            "Balance query",
            "QueueTimeOutURL":    timeout_url or "",
            "ResultURL":          result_url or "",
        }
        r = requests.post(
            f"{self._daraja_url(sandbox)}/mpesa/accountbalance/v1/query",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()
