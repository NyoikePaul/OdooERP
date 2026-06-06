from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class MpesaTransaction(models.Model):
    _name = 'mpesa.transaction'
    _description = 'M-Pesa Transaction'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'

    name = fields.Char("Transaction Ref", readonly=True, copy=False, default='New', index=True)
    transaction_type = fields.Selection([
        ('stk_push',    'STK Push (Lipa na M-Pesa)'),
        ('c2b_paybill', 'C2B Paybill/Till'),
        ('b2c',         'B2C Business Payment'),
        ('reversal',    'Reversal'),
    ], required=True, default='c2b_paybill', tracking=True)

    # Transaction IDs
    mpesa_receipt       = fields.Char("M-Pesa Receipt No.", index=True, tracking=True)
    checkout_request_id = fields.Char("Checkout Request ID", index=True)
    merchant_request_id = fields.Char("Merchant Request ID")
    daraja_txn_id       = fields.Char("Daraja Transaction ID")

    # Party details
    phone          = fields.Char("Phone Number", tracking=True)
    partner_id     = fields.Many2one('res.partner', string="Partner/Tenant", tracking=True)
    account_ref    = fields.Char("Account Reference")

    # Financials
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.ref('base.KES'))
    amount      = fields.Monetary("Amount (KES)", currency_field='currency_id', tracking=True)

    # Status
    status = fields.Selection([
        ('pending',   'Pending'),
        ('success',   'Success'),
        ('failed',    'Failed'),
        ('cancelled', 'Cancelled'),
        ('reversed',  'Reversed'),
        ('timeout',   'Timeout'),
    ], default='pending', tracking=True, index=True)

    result_code = fields.Integer("Result Code")
    result_desc = fields.Char("Result Description")

    # Reconciliation
    reconciled      = fields.Boolean("Reconciled", tracking=True)
    reconciled_at   = fields.Datetime("Reconciled At")
    invoice_id      = fields.Many2one('account.move', string="Invoice", ondelete='set null')
    payment_id      = fields.Many2one('account.payment', string="Payment", ondelete='set null')
    lease_id        = fields.Many2one('estate.lease', string="Lease", ondelete='set null')

    # Timestamps
    transaction_date = fields.Datetime("Transaction Date", default=fields.Datetime.now)
    callback_data    = fields.Text("Raw Callback Data")

    # Stats
    days_outstanding = fields.Integer(compute='_compute_days', store=True)

    _sql_constraints = [
        ('receipt_unique', 'UNIQUE(mpesa_receipt)',
         'M-Pesa receipt number must be unique.'),
    ]

    @api.depends('transaction_date', 'reconciled')
    def _compute_days(self):
        now = fields.Datetime.now()
        for r in self:
            if not r.reconciled and r.transaction_date:
                r.days_outstanding = (now - r.transaction_date).days
            else:
                r.days_outstanding = 0

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name', 'New') == 'New':
                v['name'] = self.env['ir.sequence'].next_by_code('mpesa.transaction') or 'New'
        return super().create(vals_list)

    def action_query_status(self):
        """Query Daraja for transaction status."""
        self.ensure_one()
        if not self.checkout_request_id and not self.daraja_txn_id:
            raise UserError(_("No transaction ID to query."))
        try:
            connector = self.env['mpesa.connector']
            if self.transaction_type == 'stk_push' and self.checkout_request_id:
                result = connector.stk_query(self.checkout_request_id)
            else:
                result = connector.transaction_status(self.daraja_txn_id or self.mpesa_receipt)
            self.message_post(body=_("Status query result: %s") % result)
            if result.get('ResultCode') == 0:
                self.write({'status': 'success'})
        except Exception as e:
            raise UserError(_("Status query failed: %s") % e)

    def action_reconcile(self):
        """Auto-match transaction to open invoice by amount and partner."""
        self.ensure_one()
        if self.reconciled:
            raise UserError(_("Already reconciled."))
        if not self.partner_id:
            raise UserError(_("Set a partner before reconciling."))

        domain = [
            ('move_type', '=', 'out_invoice'),
            ('payment_state', '!=', 'paid'),
            ('partner_id', '=', self.partner_id.id),
            ('amount_residual', '=', self.amount),
        ]
        invoice = self.env['account.move'].search(domain, limit=1)
        if not invoice:
            # Try fuzzy match within 10%
            domain_fuzzy = [
                ('move_type', '=', 'out_invoice'),
                ('payment_state', '!=', 'paid'),
                ('partner_id', '=', self.partner_id.id),
                ('amount_residual', '>=', self.amount * 0.9),
                ('amount_residual', '<=', self.amount * 1.1),
            ]
            invoice = self.env['account.move'].search(domain_fuzzy, limit=1)

        if not invoice:
            self.message_post(body=_(
                "No matching invoice found for KES %.0f for %s." % (
                    self.amount, self.partner_id.name)))
            return {'type': 'ir.actions.client', 'tag': 'display_notification',
                    'params': {'title': _('No Match'), 'type': 'warning',
                               'message': _('No open invoice found matching KES %.0f') % self.amount}}

        self.write({
            'reconciled': True,
            'reconciled_at': fields.Datetime.now(),
            'invoice_id': invoice.id,
        })
        invoice.message_post(body=_(
            "Payment received via M-Pesa: %s — KES %.0f. Receipt: %s" % (
                self.name, self.amount, self.mpesa_receipt or 'N/A')))
        self.message_post(body=_(
            "Reconciled to invoice %s (KES %.0f)" % (invoice.name, invoice.amount_residual)))

        return {'type': 'ir.actions.act_window', 'res_model': 'account.move',
                'res_id': invoice.id, 'view_mode': 'form'}

    def action_reverse(self):
        """Request M-Pesa reversal."""
        self.ensure_one()
        if not self.mpesa_receipt:
            raise UserError(_("No M-Pesa receipt number to reverse."))
        try:
            connector = self.env['mpesa.connector']
            result = connector.reversal(self.mpesa_receipt, self.amount,
                                         f"Reversal of {self.name}")
            self.write({'status': 'reversed'})
            self.message_post(body=_("Reversal initiated: %s") % result)
        except Exception as e:
            raise UserError(_("Reversal failed: %s") % e)

    def action_mark_failed(self):
        self.write({'status': 'failed'})

    @api.model
    def _cron_auto_reconcile(self):
        """Auto-reconcile unmatched successful transactions."""
        unreconciled = self.search([
            ('status', '=', 'success'),
            ('reconciled', '=', False),
            ('partner_id', '!=', False),
        ])
        for txn in unreconciled:
            try:
                txn.action_reconcile()
            except Exception as e:
                _logger.error("Auto-reconcile failed for %s: %s", txn.name, e)
        _logger.info("Auto-reconciled %d M-Pesa transactions.", len(unreconciled))

    @api.model
    def _cron_cleanup_pending(self):
        """Mark old pending transactions as timeout after 24 hours."""
        from datetime import timedelta
        cutoff = fields.Datetime.now() - timedelta(hours=24)
        old_pending = self.search([
            ('status', '=', 'pending'),
            ('transaction_date', '<', cutoff),
        ])
        old_pending.write({'status': 'timeout'})
        _logger.info("Marked %d transactions as timeout.", len(old_pending))

    def action_open_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            return
        return {'type': 'ir.actions.act_window', 'res_model': 'account.move',
                'res_id': self.invoice_id.id, 'view_mode': 'form'}
