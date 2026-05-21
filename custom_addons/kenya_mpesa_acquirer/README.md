# Kenya M-Pesa Payment Acquirer

> Production-ready M-Pesa Daraja 2.0 payment provider for Odoo 18

## What it does
Integrates Safaricom's **Daraja API** directly into Odoo's payment flow —
customers pay via STK Push (phone prompt), and payments auto-reconcile
against invoices, sales orders, and POS sessions.

## Payment Flow## Configuration
1. Install the module
2. Go to **Accounting → Configuration → Payment Providers → M-Pesa Kenya**
3. Enter your Daraja credentials:

| Field | Where to get it |
|---|---|
| Consumer Key | developer.safaricom.co.ke → App |
| Consumer Secret | developer.safaricom.co.ke → App |
| Business Shortcode | Your paybill or till number |
| Lipa Na M-Pesa Passkey | Safaricom Business portal |

4. Set Callback URL: `https://yourdomain.com/payment/mpesa/callback`
5. Toggle **Use Sandbox** OFF for production
6. Click **Test Connection** to verify credentials ✅

## Depends on
- `mpesa_connector` (Daraja API kernel)
- `payment` (Odoo payment provider framework)

## Webhook Security
The callback endpoint is public (`auth='public'`) as required by Safaricom.
All payloads are validated and logged. Failed callbacks return `ResultCode: 0`
to prevent Safaricom retries while the error is handled internally.
