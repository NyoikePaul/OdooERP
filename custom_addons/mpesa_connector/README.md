# M-Pesa Connector Core

> Daraja 2.0 API kernel — reusable mixin for any Odoo module

## What it does
Provides `mpesa.api.mixin` — an abstract model with ready-to-use methods
for any module that needs to call Safaricom's Daraja API.

## Available Methods

```python
# Get OAuth2 access token
token = self._get_access_token(consumer_key, consumer_secret, sandbox=False)

# Initiate STK Push
result = self._stk_push(
    token, shortcode, passkey, phone,
    amount, callback_url, account_ref, sandbox=False
)
```

## Usage in your module
```python
class MyModel(models.Model):
    _name = 'my.model'
    _inherit = ['mpesa.api.mixin']

    def pay_with_mpesa(self):
        token = self._get_access_token(key, secret)
        self._stk_push(token, shortcode, passkey, phone, amount, url, ref)
```

## Sandbox vs Production
| Environment | Base URL |
|---|---|
| Sandbox | https://sandbox.safaricom.co.ke |
| Production | https://api.safaricom.co.ke |

Pass `sandbox=True` during development. Set to `False` in production.
