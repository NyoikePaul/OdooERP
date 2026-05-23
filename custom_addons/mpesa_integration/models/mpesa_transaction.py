from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class MpesaTransaction(models.Model):
    _name        = 'mpesa.transaction'
    _description = 'M-Pesa Transaction Log'
    _order       = 'create_date desc'
    _rec_name    = 'receipt_number'
    _inherit     = ['mail.thread']

    # ── Identity ──────────────────────────────────────
    receipt_number  = fields.Char("M-Pesa Receipt",       readonly=True, index=True, tracking=True)
    checkout_id     = fields.Char("Checkout Request ID",   readonly=True, index=True)
    merchant_id     = fields.Char("Merchant Request ID",   readonly=True)
    transaction_id  = fields.Char("Daraja Transaction ID", readonly=True, index=True)

    # ── Transaction Details ───────────────────────────
    transaction_type = fields.Selection([
        ('stk',    'STK Push (Customer)'),
        ('c2b',    'C2B Paybill/Till'),
        ('b2c',    'B2C (Business Payout)'),
        ('reversal','Reversal'),
    ], string="Type", default='stk', index=True)

    phone           = fields.Char("Phone Number")
    partner_id      = fields.Many2one('res.partner', string="Partner", ondelete='set null')
    amount          = fields.Monetary("Amount", currency_field='currency_id')
    currency_id     = fields.Many2one('res.currency',
                                      default=lambda s: s.env.ref('base.KES'))
    result_code     = fields.Integer("Result Code")
    result_desc     = fields.Char("Result Description")

    # ── Status ────────────────────────────────────────
    status = fields.Selection([
        ('pending',   'Pending'),
        ('success',   'Success'),
        ('failed',    'Failed'),
        ('cancelled', 'Cancelled'),
        ('reversed',  'Reversed'),
    ], default='pending', index=True, tracking=True)

    # ── Reconciliation ────────────────────────────────
    invoice_id       = fields.Many2one('account.move',    string="Invoice",         ondelete='set null')
    payment_id       = fields.Many2one('account.payment', string="Payment",         ondelete='set null')
    reconciled       = fields.Boolean("Reconciled", default=False)
    reconciled_date  = fields.Datetime("Reconciled At")

    # ── Raw Data ──────────────────────────────────────
    raw_payload      = fields.Text("Raw Callback Payload")
    create_date      = fields.Datetime("Received At", readonly=True)
    notes            = fields.Text("Notes")

    # ── Computed ──────────────────────────────────────
    can_reconcile    = fields.Boolean(compute='_compute_can_reconcile')
    can_reverse      = fields.Boolean(compute='_compute_can_reverse')

    @api.depends('status', 'reconciled', 'invoice_id')
    def _compute_can_reconcile(self):
        for rec in self:
            rec.can_reconcile = (
                rec.status == 'success'
                and not rec.reconciled
                and not rec.invoice_id
            )

    @api.depends('status', 'receipt_number')
    def _compute_can_reverse(self):
        for rec in self:
            rec.can_reverse = (
                rec.status == 'success'
                and bool(rec.receipt_number)
            )

    # ── Name ──────────────────────────────────────────
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec.receipt_number or f'TXN-{rec.id}'

    # ── Auto-link partner from phone ──────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('phone') and not vals.get('partner_id'):
                partner = self.env['res.partner'].search(
                    [('phone', 'like', vals['phone'][-9:])], limit=1
                )
                if partner:
                    vals['partner_id'] = partner.id
        return super().create(vals_list)

    # ── Actions ───────────────────────────────────────
    def action_reconcile_invoice(self):
        """Open wizard to link this transaction to an invoice."""
        self.ensure_one()
        if not self.can_reconcile:
            raise UserError(_("This transaction cannot be reconciled."))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reconcile M-Pesa Transaction'),
            'res_model': 'mpesa.reconcile.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_transaction_id': self.id,
                'default_amount': self.amount,
                'default_partner_id': self.partner_id.id,
            }
        }

    def action_mark_reconciled(self, invoice_id=None, payment_id=None):
        self.write({
            'reconciled':      True,
            'reconciled_date': fields.Datetime.now(),
            'invoice_id':      invoice_id,
            'payment_id':      payment_id,
            'status':          'success',
        })
        self.message_post(body=_("Transaction reconciled manually."))

    def action_query_status(self):
        """Query Daraja for current transaction status."""
        self.ensure_one()
        if not self.checkout_id:
            raise UserError(_("No Checkout Request ID — cannot query status."))
        provider = self.env['payment.provider'].search(
            [('code', '=', 'mpesa')], limit=1
        )
        if not provider:
            raise UserError(_("M-Pesa payment provider not configured."))
        try:
            mixin = self.env['mpesa.api.mixin']
            token = provider._mpesa_get_token()
            result = mixin._stk_query(
                token=token,
                shortcode=provider.mpesa_shortcode,
                passkey=provider.mpesa_passkey,
                checkout_request_id=self.checkout_id,
                sandbox=provider.mpesa_sandbox,
            )
            result_code = int(result.get('ResultCode', -1))
            result_desc = result.get('ResultDesc', '')
            if result_code == 0:
                self.write({'status': 'success', 'result_desc': result_desc})
                self.message_post(body=_("Status query: PAID ✅"))
            else:
                self.write({'result_desc': result_desc})
                self.message_post(body=_(f"Status query: {result_desc}"))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('M-Pesa Status'),
                    'message': result_desc,
                    'type': 'success' if result_code == 0 else 'warning',
                }
            }
        except Exception as e:
            raise UserError(str(e)) from e

    def action_cancel(self):
        self.write({'status': 'cancelled'})
        self.message_post(body=_("Transaction manually cancelled."))

    # ── Scheduled: clean up stale pending transactions ─
    @api.model
    def _cron_cleanup_pending(self):
        """Mark transactions pending >2 hours as failed."""
        from datetime import timedelta
        cutoff = fields.Datetime.now() - timedelta(hours=2)
        stale = self.search([
            ('status', '=', 'pending'),
            ('create_date', '<', cutoff),
        ])
        stale.write({'status': 'failed', 'result_desc': 'Timed out'})
        _logger.info("Cleaned up %d stale pending M-Pesa transactions", len(stale))
