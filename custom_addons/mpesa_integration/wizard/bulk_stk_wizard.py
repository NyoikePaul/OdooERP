"""
Bulk M-Pesa STK Push Wizard
Kenya rent day: send STK push to ALL tenants with outstanding rent on the 1st.
"""
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class MpesaBulkStkWizard(models.TransientModel):
    _name        = 'mpesa.bulk.stk.wizard'
    _description = 'Bulk M-Pesa STK Push — Rent Collection'

    description  = fields.Char("Description on Phone", default="Rent Payment", required=True)
    lease_ids    = fields.Many2many(
        'estate.lease', string="Leases",
        domain="[('status','=','active')]")
    invoice_domain = fields.Selection([
        ('all_outstanding', 'All Outstanding Invoices'),
        ('current_month',   'Current Month Only'),
        ('overdue_only',    'Overdue Only'),
    ], default='all_outstanding', required=True)
    dry_run      = fields.Boolean("Preview Only (No Push)", default=False)
    preview_ids  = fields.One2many('mpesa.bulk.stk.preview', 'wizard_id', string="Preview")
    total_amount = fields.Float("Total to Collect", compute='_compute_total')
    tenant_count = fields.Integer("Tenants", compute='_compute_total')

    @api.depends('preview_ids')
    def _compute_total(self):
        for r in self:
            r.total_amount = sum(r.preview_ids.mapped('amount'))
            r.tenant_count = len(r.preview_ids)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        leases = self.env['estate.lease'].search([('status','=','active')])
        res['lease_ids'] = [(6, 0, leases.ids)]
        return res

    def action_preview(self):
        self.ensure_one()
        self.preview_ids.unlink()
        from odoo import fields as F
        today = F.Date.today()
        previews = []
        for lease in self.lease_ids:
            if not lease.tenant_id.mobile and not lease.tenant_id.phone:
                continue
            domain = [
                ('lease_id', '=', lease.id),
                ('move_type', '=', 'out_invoice'),
                ('payment_state', 'not in', ('paid', 'reversed')),
            ]
            if self.invoice_domain == 'current_month':
                domain += [('invoice_date', '>=', today.replace(day=1))]
            elif self.invoice_domain == 'overdue_only':
                domain += [('invoice_date_due', '<', today)]
            invs = self.env['account.move'].search(domain)
            if not invs:
                continue
            for inv in invs:
                previews.append({
                    'wizard_id':  self.id,
                    'lease_id':   lease.id,
                    'partner_id': lease.tenant_id.id,
                    'phone':      lease.tenant_id.mobile or lease.tenant_id.phone,
                    'invoice_id': inv.id,
                    'amount':     inv.amount_residual,
                })
        self.env['mpesa.bulk.stk.preview'].create(previews)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mpesa.bulk.stk.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_send_all(self):
        self.ensure_one()
        if not self.preview_ids:
            raise UserError(_("Run Preview first."))
        if self.dry_run:
            return {'type': 'ir.actions.client', 'tag': 'display_notification',
                    'params': {'title': _('Preview Only'),
                               'message': _('%d pushes would be sent totalling KES %.0f') % (
                                   self.tenant_count, self.total_amount),
                               'type': 'info'}}
        sent = 0
        failed = 0
        for p in self.preview_ids:
            try:
                p.invoice_id.action_mpesa_stk_push()
                sent += 1
            except Exception as e:
                _logger.error("Bulk STK failed for %s: %s", p.partner_id.name, e)
                failed += 1
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': _('Bulk STK Push Complete'),
                           'message': _('%d sent, %d failed. Total KES %.0f') % (
                               sent, failed, self.total_amount),
                           'type': 'success' if not failed else 'warning'}}


class MpesaBulkStkPreview(models.TransientModel):
    _name = 'mpesa.bulk.stk.preview'
    _description = 'Bulk STK Preview Line'

    wizard_id   = fields.Many2one('mpesa.bulk.stk.wizard', ondelete='cascade')
    lease_id    = fields.Many2one('estate.lease',   string="Lease")
    partner_id  = fields.Many2one('res.partner',    string="Tenant")
    phone       = fields.Char("Phone")
    invoice_id  = fields.Many2one('account.move',   string="Invoice")
    amount      = fields.Float("Amount (KES)")
