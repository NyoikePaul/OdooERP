# M-Pesa Integration — Transaction Log

> Persistent audit trail for every M-Pesa transaction

## What it does
Records every Safaricom callback in `mpesa.transaction` — a searchable,
filterable log of all M-Pesa activity across your Odoo instance.

## Model: `mpesa.transaction`

| Field | Description |
|---|---|
| `receipt_number` | Safaricom M-Pesa receipt (e.g. `RGQ12XYZ`) |
| `phone` | Payer phone number |
| `amount` | Amount paid in KES |
| `checkout_id` | STK Push checkout request ID |
| `status` | pending / success / failed / cancelled |
| `invoice_id` | Linked Odoo invoice (if reconciled) |
| `raw_payload` | Full JSON from Safaricom (for debugging) |

## Access
**Menu:** M-Pesa → Transactions

Managers can view all transactions. Regular users have read-only access.
