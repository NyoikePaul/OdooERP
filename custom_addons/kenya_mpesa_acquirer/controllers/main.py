from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)


class MpesaController(http.Controller):

    # ── STK Push Callback ────────────────────────────
    @http.route('/payment/mpesa/callback', type='json',
                auth='public', methods=['POST'], csrf=False)
    def mpesa_stk_callback(self, **kw):
        """Safaricom STK Push result callback."""
        try:
            raw  = request.httprequest.data
            data = json.loads(raw)
            _logger.info("M-Pesa STK callback: %s", data)

            stk         = data.get('Body', {}).get('stkCallback', {})
            result_code = stk.get('ResultCode')
            checkout_id = stk.get('CheckoutRequestID', '')
            merchant_id = stk.get('MerchantRequestID', '')
            result_desc = stk.get('ResultDesc', '')

            tx_vals = {
                'checkout_id':      checkout_id,
                'merchant_id':      merchant_id,
                'result_code':      result_code,
                'result_desc':      result_desc,
                'raw_payload':      raw.decode('utf-8'),
                'status':           'success' if result_code == 0 else 'failed',
                'transaction_type': 'stk',
            }

            if result_code == 0:
                items = {
                    i['Name']: i.get('Value')
                    for i in stk.get('CallbackMetadata', {}).get('Item', [])
                }
                amount  = float(items.get('Amount', 0))
                receipt = items.get('MpesaReceiptNumber')
                phone   = str(items.get('PhoneNumber', ''))

                tx_vals.update({
                    'receipt_number': receipt,
                    'amount':         amount,
                    'phone':          phone,
                })
                _logger.info(
                    "M-Pesa STK SUCCESS | Receipt: %s | Amount: %.2f | Phone: %s",
                    receipt, amount, phone
                )

                # Find existing pending transaction by checkout_id
                existing = request.env['mpesa.transaction'].sudo().search(
                    [('checkout_id', '=', checkout_id), ('status', '=', 'pending')],
                    limit=1
                )
                if existing:
                    existing.sudo().write(tx_vals)
                    tx = existing
                else:
                    tx = request.env['mpesa.transaction'].sudo().create(tx_vals)

                # Reconcile against Odoo payment.transaction
                payment_tx = request.env['payment.transaction'].sudo().search(
                    [('provider_reference', '=', checkout_id)], limit=1
                )
                if payment_tx:
                    payment_tx.sudo()._set_done()
                    tx.sudo().write({'reconciled': True})
                    _logger.info("Auto-reconciled payment.transaction: %s",
                                 payment_tx.reference)
            else:
                _logger.warning(
                    "M-Pesa STK FAILED | CheckoutID: %s | Code: %s | Desc: %s",
                    checkout_id, result_code, result_desc
                )
                existing = request.env['mpesa.transaction'].sudo().search(
                    [('checkout_id', '=', checkout_id)], limit=1
                )
                if existing:
                    existing.sudo().write(tx_vals)
                else:
                    request.env['mpesa.transaction'].sudo().create(tx_vals)

        except Exception as e:
            _logger.exception("M-Pesa STK callback error: %s", e)

        return {"ResultCode": 0, "ResultDesc": "Accepted"}

    # ── C2B Validation ───────────────────────────────
    @http.route('/payment/mpesa/c2b/validate', type='json',
                auth='public', methods=['POST'], csrf=False)
    def mpesa_c2b_validate(self, **kw):
        """C2B validation endpoint — called before payment completes."""
        try:
            data = json.loads(request.httprequest.data)
            _logger.info("M-Pesa C2B validation: %s", data)
            # Accept all by default — add custom logic here
        except Exception as e:
            _logger.error("C2B validation error: %s", e)
        return {"ResultCode": 0, "ResultDesc": "Accepted"}

    # ── C2B Confirmation ─────────────────────────────
    @http.route('/payment/mpesa/c2b/confirm', type='json',
                auth='public', methods=['POST'], csrf=False)
    def mpesa_c2b_confirm(self, **kw):
        """C2B confirmation — payment completed."""
        try:
            raw  = request.httprequest.data
            data = json.loads(raw)
            _logger.info("M-Pesa C2B confirmation: %s", data)

            request.env['mpesa.transaction'].sudo().create({
                'receipt_number':   data.get('TransID'),
                'transaction_id':   data.get('TransID'),
                'phone':            str(data.get('MSISDN', '')),
                'amount':           float(data.get('TransAmount', 0)),
                'result_desc':      data.get('TransactionType', 'C2B'),
                'status':           'success',
                'transaction_type': 'c2b',
                'raw_payload':      raw.decode('utf-8'),
            })
        except Exception as e:
            _logger.exception("C2B confirmation error: %s", e)

        return {"ResultCode": 0, "ResultDesc": "Accepted"}

    # ── B2C Result ───────────────────────────────────
    @http.route('/payment/mpesa/b2c/result', type='json',
                auth='public', methods=['POST'], csrf=False)
    def mpesa_b2c_result(self, **kw):
        """B2C payment result callback."""
        try:
            raw  = request.httprequest.data
            data = json.loads(raw)
            _logger.info("M-Pesa B2C result: %s", data)

            result = data.get('Result', {})
            params = {
                p['Key']: p['Value']
                for p in result.get('ResultParameters', {}).get('ResultParameter', [])
            }
            request.env['mpesa.transaction'].sudo().create({
                'receipt_number':   params.get('TransactionReceipt'),
                'transaction_id':   result.get('TransactionID'),
                'phone':            str(params.get('ReceiverPartyPublicName', '')),
                'amount':           float(params.get('TransactionAmount', 0)),
                'status':           'success' if result.get('ResultCode') == 0 else 'failed',
                'result_code':      result.get('ResultCode', -1),
                'result_desc':      result.get('ResultDesc', ''),
                'transaction_type': 'b2c',
                'raw_payload':      raw.decode('utf-8'),
            })
        except Exception as e:
            _logger.exception("B2C result error: %s", e)
        return {"ResultCode": 0, "ResultDesc": "Accepted"}

    # ── STK Push API (from frontend) ──────────────────
    @http.route('/payment/mpesa/stk_push', type='json',
                auth='user', methods=['POST'])
    def stk_push(self, amount, phone, account_ref,
                 invoice_id=None, partner_id=None, **kw):
        """Initiate STK Push — callable from UI/POS."""
        provider = request.env['payment.provider'].sudo().search(
            [('code', '=', 'mpesa'), ('state', '!=', 'disabled')], limit=1
        )
        if not provider:
            return {'error': 'M-Pesa provider not configured'}

        try:
            mixin  = request.env['mpesa.api.mixin']
            token  = provider._mpesa_get_token()
            phone  = mixin._format_phone(phone)
            result = mixin._stk_push(
                token        = token,
                shortcode    = provider.mpesa_shortcode,
                passkey      = provider.mpesa_passkey,
                phone        = phone,
                amount       = amount,
                callback_url = provider._mpesa_get_callback_url(),
                account_ref  = account_ref,
                sandbox      = provider.mpesa_sandbox,
            )
            request.env['mpesa.transaction'].sudo().create({
                'checkout_id':      result.get('CheckoutRequestID'),
                'merchant_id':      result.get('MerchantRequestID'),
                'phone':            phone,
                'amount':           amount,
                'status':           'pending',
                'transaction_type': 'stk',
                'invoice_id':       invoice_id,
                'partner_id':       partner_id,
            })
            return {
                'success':     True,
                'checkout_id': result.get('CheckoutRequestID'),
                'message':     f'STK Push sent to {phone}',
            }
        except Exception as e:
            _logger.error("STK Push error: %s", e)
            return {'error': str(e)}
