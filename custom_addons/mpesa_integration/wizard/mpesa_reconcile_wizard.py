from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MpesaReconcileWizard(models.TransientModel):
    _name        = 'mpesa.reconcile.wizard'
    _description = 'Reconcile M-Pesa Transaction to Invoice'

    transaction_id = fields.Many2one('mpesa.transaction', string="Transaction",
                                     required=True, readonly=True)
    receipt_number = fields.Char(related='transaction_id.receipt_number', readonly=True)
    amount         = fields.Monetary("Amount (KES)", currency_field='currency_id')
    currency_id    = fields.Many2one('res.currency',
                                     default=lambda s: s.env.ref('base.KES'))
    partner_id     = fields.Many2one('res.partner', string="Partner")
    invoice_id     = fields.Many2one('account.move', string="Invoice",
                                     domain="[('move_type','=','out_invoice'),('payment_state','!=','paid'),('partner_id','=',partner_id)]")
    create_payment = fields.Boolean("Create Payment Entry", default=True)
    notes          = fields.Text("Notes")

    @api.onchange('partner_id')
    def _onchange_partner(self):
        self.invoice_id = False

    def action_reconcile(self):
        self.ensure_one()
        tx = self.transaction_id

        if not self.invoice_id:
            raise UserError(_("Please select an invoice to reconcile against."))

        if self.create_payment:
            journal = self.env['account.journal'].search([
                ('type', '=', 'bank'),
                ('name', 'ilike', 'mpesa'),
            ], limit=1) or self.env['account.journal'].search([
                ('type', '=', 'bank')
            ], limit=1)

            payment = self.env['account.payment'].create({
                'payment_type':     'inbound',
                'partner_type':     'customer',
                'partner_id':       self.invoice_id.partner_id.id,
                'amount':           self.amount,
                'journal_id':       journal.id,
                'ref':              f"M-Pesa {tx.receipt_number}",
                'memo':             f"M-Pesa Receipt: {tx.receipt_number}",
            })
            payment.action_post()

            # Reconcile payment to invoice
            (self.invoice_id + payment.move_id).line_ids.filtered(
                lambda l: l.account_id == self.invoice_id.line_ids.filtered(
                    lambda x: x.account_id.account_type in ('asset_receivable',)
                ).account_id
            ).reconcile()

            tx.action_mark_reconciled(
                invoice_id=self.invoice_id.id,
                payment_id=payment.id
            )
        else:
            tx.action_mark_reconciled(invoice_id=self.invoice_id.id)

        tx.message_post(
            body=_(f"Reconciled to invoice {self.invoice_id.name}. "
                   f"Receipt: {tx.receipt_number}")
        )

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
        }
