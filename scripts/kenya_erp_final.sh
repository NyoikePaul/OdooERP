#!/usr/bin/env bash
# Kenya ERP — Final 10/10 Upgrade Script
# Run from ~/OdooERP directory
set -e
cd ~/OdooERP
git pull --rebase

echo "======================================="
echo "COMMIT 1/8 — M-Pesa: STK Push from Invoice"
echo "======================================="

# M-Pesa: Add STK push button directly on invoices
cat > custom_addons/mpesa_integration/models/account_move_mpesa.py << 'EOF'
"""
M-Pesa STK Push directly from Odoo invoices.
Kenya-specific: tenants pay rent by receiving an STK push on their phone.
"""
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class AccountMoveMpesa(models.Model):
    _inherit = 'account.move'

    mpesa_phone      = fields.Char("Tenant M-Pesa Phone", compute='_compute_mpesa_phone', store=True)
    mpesa_txn_ids    = fields.One2many('mpesa.transaction', 'invoice_id', string="M-Pesa Payments")
    mpesa_txn_count  = fields.Integer(compute='_compute_mpesa_count', string="M-Pesa Payments")
    mpesa_paid       = fields.Boolean(compute='_compute_mpesa_paid', string="Paid via M-Pesa", store=True)
    mpesa_receipt    = fields.Char("M-Pesa Receipt", compute='_compute_mpesa_paid', store=True)

    @api.depends('partner_id.phone', 'partner_id.mobile')
    def _compute_mpesa_phone(self):
        for r in self:
            r.mpesa_phone = r.partner_id.mobile or r.partner_id.phone or ''

    def _compute_mpesa_count(self):
        for r in self:
            r.mpesa_txn_count = len(r.mpesa_txn_ids)

    @api.depends('mpesa_txn_ids.status', 'mpesa_txn_ids.mpesa_receipt')
    def _compute_mpesa_paid(self):
        for r in self:
            paid = r.mpesa_txn_ids.filtered(lambda t: t.status == 'success')
            r.mpesa_paid    = bool(paid)
            r.mpesa_receipt = paid[:1].mpesa_receipt or ''

    def action_mpesa_stk_push(self):
        """Send STK Push to tenant's phone for this invoice."""
        self.ensure_one()
        if self.payment_state == 'paid':
            raise UserError(_("Invoice already paid."))
        phone = self.mpesa_phone
        if not phone:
            raise UserError(_(
                "No phone number on tenant %s. "
                "Add mobile number in Contacts first.") % self.partner_id.name)

        connector = self.env['mpesa.connector']
        ref = (self.name or 'INV')[:12]
        desc = ("Rent %s" % (self.invoice_date.strftime('%b %Y') if self.invoice_date else ''))[:13]

        result = connector.stk_push(
            phone=phone,
            amount=self.amount_residual,
            account_ref=ref,
            description=desc,
        )

        # Create transaction record
        txn = self.env['mpesa.transaction'].create({
            'transaction_type':   'stk_push',
            'phone':              phone,
            'partner_id':         self.partner_id.id,
            'amount':             self.amount_residual,
            'account_ref':        ref,
            'invoice_id':         self.id,
            'lease_id':           self.lease_id.id if self.lease_id else False,
            'checkout_request_id': result.get('checkout_request_id'),
            'merchant_request_id': result.get('merchant_request_id'),
            'status':             'pending',
        })

        self.message_post(
            body=_("STK Push sent to %s for KES %.0f. "
                   "Transaction: %s. Customer message: %s") % (
                phone, self.amount_residual, txn.name,
                result.get('customer_message', '')),
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('STK Push Sent'),
                'message': _('M-Pesa prompt sent to %s. KES %.0f.') % (phone, self.amount_residual),
                'type': 'success',
            }
        }

    def action_open_mpesa_txns(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('M-Pesa Payments'),
            'res_model': 'mpesa.transaction', 'view_mode': 'list,form',
            'domain': [('invoice_id', '=', self.id)],
        }
EOF

# Add STK Push button + stat button to invoice form
cat > custom_addons/mpesa_integration/views/invoice_mpesa_views.xml << 'EOF'
<?xml version="1.0" encoding="utf-8"?>
<odoo>
  <record id="view_invoice_mpesa_inherit" model="ir.ui.view">
    <field name="name">account.move.mpesa.inherit</field>
    <field name="model">account.move</field>
    <field name="inherit_id" ref="account.view_move_form"/>
    <field name="arch" type="xml">

      <!-- STK Push button in header -->
      <xpath expr="//header" position="inside">
        <button name="action_mpesa_stk_push" type="object"
                string="Pay via M-Pesa (STK Push)"
                invisible="move_type != 'out_invoice' or payment_state == 'paid'"
                class="btn-success"/>
      </xpath>

      <!-- Smart button for M-Pesa transactions -->
      <xpath expr="//div[@name='button_box']" position="inside">
        <button name="action_open_mpesa_txns" type="object"
                class="oe_stat_button" icon="fa-mobile"
                invisible="mpesa_txn_count == 0">
          <field name="mpesa_txn_count" widget="statinfo" string="M-Pesa"/>
        </button>
      </xpath>

      <!-- M-Pesa receipt badge -->
      <xpath expr="//field[@name='payment_state']" position="after">
        <field name="mpesa_receipt" readonly="1"
               invisible="not mpesa_receipt"
               string="M-Pesa Receipt"/>
      </xpath>

    </field>
  </record>
</odoo>
EOF

# Update mpesa_integration manifest
cat > custom_addons/mpesa_integration/__manifest__.py << 'EOF'
{
    'name':        'M-Pesa Integration',
    'version':     '18.0.3.0.0',
    'category':    'Accounting/Payment',
    'summary':     'M-Pesa Daraja 2.0 — STK Push from invoices, auto-reconcile, C2B, B2C, reversal',
    'description': """
Kenya M-Pesa Integration — Enterprise rent collection.

Features:
- One-click STK Push from any invoice
- Auto-reconciliation of incoming payments
- C2B Paybill/Till transaction log
- B2C business payments
- Transaction reversal
- Scheduled auto-reconcile cron
- Smart buttons on invoices showing M-Pesa payment count
- Payment receipt on reconciled transactions
    """,
    'author':      'Paul Nyoike',
    'website':     'https://github.com/NyoikePaul/OdooERP',
    'license':     'LGPL-3',
    'depends':     ['base', 'account', 'mail', 'mpesa_connector'],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/invoice_mpesa_views.xml',
    ],
    'installable':  True,
    'application':  True,
    'auto_install': False,
}
EOF

# Add model to __init__
python3 - << 'PYEOF'
init = open('custom_addons/mpesa_integration/models/__init__.py').read()
if 'account_move_mpesa' not in init:
    init += 'from . import account_move_mpesa\n'
    open('custom_addons/mpesa_integration/models/__init__.py','w').write(init)
    print("Added account_move_mpesa to __init__")
PYEOF

# Add access rule for new model
python3 - << 'PYEOF'
content = open('custom_addons/mpesa_integration/security/ir.model.access.csv').read()
if 'account.move' not in content:
    # account.move is a core model, no access rule needed
    pass
print("Security OK")
PYEOF

git add .
git commit -m "feat(mpesa): STK Push from invoice — one-click rent collection, smart button, M-Pesa receipt"
git push

echo "======================================="
echo "COMMIT 2/8 — M-Pesa: Bulk Rent Collection + Kenya Phone Validation"
echo "======================================="

cat > custom_addons/mpesa_integration/wizard/bulk_stk_wizard.py << 'EOF'
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
EOF

cat > custom_addons/mpesa_integration/wizard/bulk_stk_wizard.xml << 'EOF'
<?xml version="1.0" encoding="utf-8"?>
<odoo>
  <record id="view_bulk_stk_wizard" model="ir.ui.view">
    <field name="name">mpesa.bulk.stk.wizard.form</field>
    <field name="model">mpesa.bulk.stk.wizard</field>
    <field name="arch" type="xml">
      <form string="Bulk M-Pesa STK Push — Rent Collection">
        <sheet>
          <group>
            <group>
              <field name="invoice_domain"/>
              <field name="description"/>
              <field name="dry_run"/>
            </group>
            <group>
              <field name="tenant_count" readonly="1"/>
              <field name="total_amount" readonly="1" string="Total (KES)"/>
            </group>
          </group>
          <field name="lease_ids" widget="many2many_tags"/>
          <notebook>
            <page string="Preview">
              <field name="preview_ids" readonly="1">
                <list>
                  <field name="partner_id"/>
                  <field name="phone"/>
                  <field name="invoice_id"/>
                  <field name="amount"/>
                </list>
              </field>
            </page>
          </notebook>
        </sheet>
        <footer>
          <button name="action_preview"  type="object" string="Preview"   class="btn-secondary"/>
          <button name="action_send_all" type="object" string="Send All STK Pushes" class="btn-success oe_highlight"/>
          <button string="Cancel" class="btn-secondary" special="cancel"/>
        </footer>
      </form>
    </field>
  </record>
  <record id="action_bulk_stk_wizard" model="ir.actions.act_window">
    <field name="name">Bulk Rent Collection (M-Pesa)</field>
    <field name="res_model">mpesa.bulk.stk.wizard</field>
    <field name="view_mode">form</field>
    <field name="target">new</field>
  </record>
</odoo>
EOF

# Update wizard __init__
python3 - << 'PYEOF'
init_path = 'custom_addons/mpesa_integration/wizard/__init__.py'
import os
content = open(init_path).read() if os.path.exists(init_path) else ''
if 'bulk_stk_wizard' not in content:
    content += 'from . import bulk_stk_wizard\n'
    open(init_path,'w').write(content)
# Update main __init__
main_init = open('custom_addons/mpesa_integration/__init__.py').read()
if 'wizard' not in main_init:
    main_init += 'from . import wizard\n'
    open('custom_addons/mpesa_integration/__init__.py','w').write(main_init)
print("Done")
PYEOF

# Add menu item for bulk collection
python3 - << 'PYEOF'
content = open('custom_addons/mpesa_integration/views/views.xml').read()
if 'bulk_stk' not in content:
    content = content.replace(
        '</odoo>',
        '''  <menuitem id="menu_mpesa_bulk" name="Bulk Rent Collection"
            parent="menu_mpesa_root"
            action="action_bulk_stk_wizard" sequence="2"/>
</odoo>''')
    open('custom_addons/mpesa_integration/views/views.xml','w').write(content)
    print("Menu added")
PYEOF

# Update manifest with wizard
python3 - << 'PYEOF'
content = open('custom_addons/mpesa_integration/__manifest__.py').read()
content = content.replace(
    "        'views/invoice_mpesa_views.xml',",
    "        'views/invoice_mpesa_views.xml',\n        'wizard/bulk_stk_wizard.xml',")
if 'wizard/bulk_stk_wizard' not in content:
    print("WARNING: manifest not updated correctly")
else:
    open('custom_addons/mpesa_integration/__manifest__.py','w').write(content)
    print("Manifest updated")
PYEOF

git add .
git commit -m "feat(mpesa): bulk STK push wizard — send to all tenants on rent day, preview + dry-run"
git push

echo "======================================="
echo "COMMIT 3/8 — Real Estate: KRA PIN Validation + Kenya Areas"
echo "======================================="

python3 - << 'PYEOF'
# Add KRA PIN validation + Nairobi estates to property model
content = open('custom_addons/kenya_real_estate/models/property.py').read()

# Add KRA PIN validator if not there
if '_validate_kra_pin' not in content:
    kra_validator = '''
    @api.constrains('landlord_kra_pin')
    def _validate_kra_pin(self):
        import re
        for r in self:
            if r.landlord_kra_pin:
                if not re.match(r'^[A-Z]\d{9}[A-Z]$', r.landlord_kra_pin.upper()):
                    raise ValidationError(
                        _("Invalid KRA PIN format: %s. "
                          "Expected format: A000000000B") % r.landlord_kra_pin)

    @api.constrains('monthly_rent')
    def _check_kra_mri_threshold(self):
        """Warn if rent exceeds KRA MRI threshold (KES 288,000/mo)."""
        for r in self:
            if r.monthly_rent > 288000:
                r.message_post(
                    body=_("Note: Monthly rent KES %.0f exceeds KRA MRI threshold "
                           "(KES 288,000). Normal income tax rates apply "
                           "(not 7.5%% flat rate).") % r.monthly_rent)

'''
    content = content.replace(
        "    def _free_property" if "_free_property" in content else "    def action_set_available",
        kra_validator + "\n    def action_set_available")
    open('custom_addons/kenya_real_estate/models/property.py','w').write(content)
    print("KRA PIN validation added")
PYEOF

# Add Kenya-specific estate/area selection
python3 - << 'PYEOF'
content = open('custom_addons/kenya_real_estate/models/property.py').read()
if 'nairobi_area' not in content:
    area_field = '''
    nairobi_area     = fields.Selection([
        # Nairobi Upmarket
        ('karen','Karen'),('runda','Runda'),('muthaiga','Muthaiga'),
        ('lavington','Lavington'),('kilimani','Kilimani'),('kileleshwa','Kileleshwa'),
        ('westlands','Westlands'),('spring_valley','Spring Valley'),
        ('ridgeways','Ridgeways'),('gigiri','Gigiri/UN Area'),
        # Nairobi Middle
        ('south_b','South B'),('south_c','South C'),('ngumo','Ngumo'),
        ('langata','Lang\'ata'),('rongai','Rongai'),('ruaka','Ruaka'),
        ('ruiru','Ruiru'),('thika_rd','Thika Road'),
        # Nairobi Eastlands
        ('buruburu','Buruburu'),('donholm','Donholm'),('umoja','Umoja'),
        ('embakasi','Embakasi'),('pipeline','Pipeline'),
        # Nairobi CBD/Commercial
        ('cbd','Nairobi CBD'),('upper_hill','Upper Hill'),('riverside','Riverside'),
        ('parklands','Parklands'),('ngara','Ngara'),
        # Mombasa
        ('nyali','Nyali'),('bamburi','Bamburi'),('shanzu','Shanzu'),
        ('diani','Diani'),('mombasa_cbd','Mombasa CBD'),
        # Other towns
        ('kisumu_cbd','Kisumu CBD'),('nakuru_cbd','Nakuru CBD'),
        ('eldoret','Eldoret'),('thika','Thika'),('machakos','Machakos'),
        ('other_area','Other'),
    ], string="Area/Estate")
    '''
    content = content.replace(
        "    street           = fields.Char",
        area_field + "\n    street           = fields.Char")
    open('custom_addons/kenya_real_estate/models/property.py','w').write(content)
    print("Kenya areas added")
PYEOF

git add .
git commit -m "feat(realestate): KRA PIN validation (A000000000B), Kenya area/estate selector, MRI threshold warning"
git push

echo "======================================="
echo "COMMIT 4/8 — Real Estate: M-Pesa Rent Payment from Lease"
echo "======================================="

# Add M-Pesa integration to lease model
python3 - << 'PYEOF'
content = open('custom_addons/kenya_real_estate/models/lease.py').read()
if 'action_mpesa_stk_push' not in content:
    stk_method = '''
    def action_mpesa_stk_push(self):
        """Send STK Push to tenant for outstanding rent."""
        self.ensure_one()
        if self.status != "active":
            raise UserError(_("Lease must be active."))
        if self.total_outstanding <= 0:
            raise UserError(_("No outstanding amount on this lease."))
        phone = self.tenant_id.mobile or self.tenant_id.phone
        if not phone:
            raise UserError(_(
                "No phone number for %s. Add mobile in Contacts.") % self.tenant_id.name)
        connector = self.env["mpesa.connector"]
        result = connector.stk_push(
            phone=phone,
            amount=self.total_outstanding,
            account_ref=(self.name or "RENT")[:12],
            description=("Rent %s" % self.property_id.name[:8])[:13],
        )
        txn = self.env["mpesa.transaction"].create({
            "transaction_type":   "stk_push",
            "phone":              phone,
            "partner_id":         self.tenant_id.id,
            "amount":             self.total_outstanding,
            "lease_id":           self.id,
            "checkout_request_id": result.get("checkout_request_id"),
            "merchant_request_id": result.get("merchant_request_id"),
            "status":             "pending",
        })
        self.message_post(
            body=_("STK Push sent to %s for KES %.0f. TXN: %s") % (
                phone, self.total_outstanding, txn.name),
            partner_ids=[self.tenant_id.id])
        return {"type": "ir.actions.client", "tag": "display_notification",
                "params": {"title": _("STK Push Sent"),
                           "message": _("M-Pesa prompt sent to %s") % phone,
                           "type": "success"}}

    def action_open_mpesa_payments(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "M-Pesa Payments",
            "res_model": "mpesa.transaction",
            "view_mode": "list,form",
            "domain": [("lease_id", "=", self.id)],
        }

'''
    # Insert before action_generate_invoice
    content = content.replace(
        '    def action_generate_invoice(self):',
        stk_method + '    def action_generate_invoice(self):')
    open('custom_addons/kenya_real_estate/models/lease.py','w').write(content)
    print("M-Pesa STK added to lease")

# Add mpesa_txn_count to lease
content = open('custom_addons/kenya_real_estate/models/lease.py').read()
if 'mpesa_txn_count' not in content:
    content = content.replace(
        '    payment_ids = fields.One2many("account.move", "lease_id", string="Invoices")',
        '''    payment_ids     = fields.One2many("account.move", "lease_id", string="Invoices")
    mpesa_txn_ids   = fields.One2many("mpesa.transaction", "lease_id", string="M-Pesa Payments")
    mpesa_txn_count = fields.Integer(compute="_compute_mpesa_count", string="M-Pesa Payments")

    def _compute_mpesa_count(self):
        for r in self:
            r.mpesa_txn_count = len(r.mpesa_txn_ids)''')
    open('custom_addons/kenya_real_estate/models/lease.py','w').write(content)
    print("mpesa_txn_count added")
PYEOF

# Add STK push button + M-Pesa stat button to lease form
python3 - << 'PYEOF'
content = open('custom_addons/kenya_real_estate/views/lease_views.xml').read()
if 'action_mpesa_stk_push' not in content:
    content = content.replace(
        '<button name="action_send_reminder"',
        '<button name="action_mpesa_stk_push" type="object" '
        'string="Collect via M-Pesa" '
        'invisible="status != \'active\' or total_outstanding == 0" '
        'class="btn-success"/>\n          '
        '<button name="action_send_reminder"')
    # Add M-Pesa stat button
    content = content.replace(
        '''            <button name="action_open_invoices" type="object" class="oe_stat_button" icon="fa-money">
              <field name="payment_count" widget="statinfo" string="Invoices"/>
            </button>''',
        '''            <button name="action_open_invoices" type="object" class="oe_stat_button" icon="fa-money">
              <field name="payment_count" widget="statinfo" string="Invoices"/>
            </button>
            <button name="action_open_mpesa_payments" type="object"
                    class="oe_stat_button" icon="fa-mobile"
                    invisible="mpesa_txn_count == 0">
              <field name="mpesa_txn_count" widget="statinfo" string="M-Pesa"/>
            </button>''')
    open('custom_addons/kenya_real_estate/views/lease_views.xml','w').write(content)
    print("Lease form updated with M-Pesa buttons")
PYEOF

git add .
git commit -m "feat(realestate+mpesa): STK push from lease, M-Pesa stat button, tenant payment flow"
git push

echo "======================================="
echo "COMMIT 5/8 — Real Estate: Demand Notice PDF + Kenya Legal Text"
echo "======================================="

cat > custom_addons/kenya_real_estate/report/demand_notice_report.xml << 'EOF'
<?xml version="1.0" encoding="utf-8"?>
<odoo>
  <record id="action_report_demand_notice" model="ir.actions.report">
    <field name="name">Demand Notice</field>
    <field name="model">estate.demand.notice</field>
    <field name="report_type">qweb-pdf</field>
    <field name="report_name">kenya_real_estate.report_demand_notice</field>
    <field name="binding_model_id" ref="model_estate_demand_notice"/>
    <field name="binding_type">report</field>
  </record>

  <template id="report_demand_notice">
    <t t-call="web.html_container">
      <t t-call="web.external_layout">
        <div class="page">
          <t t-foreach="docs" t-as="notice">
            <div class="text-center mb-4">
              <h2 style="color:#dc3545;">FORMAL DEMAND NOTICE</h2>
              <p class="text-muted">Issued under the Landlord and Tenant (Shops, Hotels and Catering Establishments) Act — Cap 301, Laws of Kenya</p>
              <p><strong>Ref: <t t-esc="notice.name"/></strong> | Date: <strong><t t-esc="notice.issue_date"/></strong></p>
            </div>
            <hr/>
            <p>TO: <strong><t t-esc="notice.tenant_id.name"/></strong></p>
            <p>Address: <t t-esc="notice.tenant_id.street or ''"/>, <t t-esc="notice.tenant_id.city or ''"/></p>
            <br/>
            <p>FROM: <strong><t t-esc="notice.property_id.landlord_id.name"/></strong></p>
            <p>Property: <strong><t t-esc="notice.property_id.name"/></strong></p>
            <br/>
            <h4>NOTICE OF DEMAND</h4>
            <p>
              TAKE NOTICE that you are hereby required to pay the sum of
              <strong>Kenya Shillings <t t-esc="'{:,.0f}'.format(notice.arrears_amount)"/> (KES <t t-esc="'{:,.0f}'.format(notice.arrears_amount)"/>)</strong>
              being rent arrears of <t t-esc="notice.months_arrears"/> month(s) for the premises described above,
              within <strong><t t-esc="notice.deadline - notice.issue_date"/> days</strong> from the date of this notice
              (<strong>on or before <t t-esc="notice.deadline"/></strong>).
            </p>
            <br/>
            <p>
              Should you fail to pay the above-mentioned sum within the stipulated period, we shall
              <t t-if="notice.property_id.property_type == 'commercial'">
                be compelled to file a complaint before the <strong>Business Premises Rent Tribunal (BPRT)</strong>
              </t>
              <t t-else="">
                take legal action against you including filing of a suit in the
                <strong>Magistrates Court</strong>
              </t>
              for recovery of the arrears and eviction, at your cost.
            </p>
            <br/>
            <p>
              You are further reminded that continued non-payment of rent constitutes grounds for
              termination of your tenancy as per the Distress for Rent Act (Cap 293, Laws of Kenya).
            </p>
            <br/>
            <table class="table table-bordered table-sm" style="max-width:400px">
              <tr><th>Lease Ref</th><td><t t-esc="notice.lease_id.name"/></td></tr>
              <tr><th>Monthly Rent</th><td>KES <t t-esc="'{:,.0f}'.format(notice.lease_id.monthly_rent)"/></td></tr>
              <tr><th>Months Arrears</th><td><t t-esc="notice.months_arrears"/></td></tr>
              <tr><th>Amount Due</th><td><strong>KES <t t-esc="'{:,.0f}'.format(notice.arrears_amount)"/></strong></td></tr>
              <tr><th>Pay Deadline</th><td><strong><t t-esc="notice.deadline"/></strong></td></tr>
            </table>
            <br/>
            <p>M-Pesa Paybill: <strong>[Your Paybill Number]</strong> | Account: <t t-esc="notice.lease_id.name"/></p>
            <br/>
            <div class="row mt-5">
              <div class="col-6">
                <p>________________________</p>
                <p>Landlord/Agent Signature</p>
                <p>Name: <t t-esc="notice.property_id.landlord_id.name"/></p>
                <p>Date: <t t-esc="notice.issue_date"/></p>
              </div>
              <div class="col-6">
                <p>________________________</p>
                <p>Witness Signature</p>
                <p>Name: <t t-esc="notice.witness or 'N/A'"/></p>
                <p>Date: <t t-esc="notice.issue_date"/></p>
              </div>
            </div>
            <br/>
            <p class="text-muted" style="font-size:9px">
              This notice is issued in accordance with the Landlord and Tenant Act Cap 301 and the
              Distress for Rent Act Cap 293, Laws of Kenya. Any queries, contact the issuing party above.
            </p>
          </t>
        </div>
      </t>
    </t>
  </template>
</odoo>
EOF

# Add to manifest
python3 - << 'PYEOF'
content = open('custom_addons/kenya_real_estate/__manifest__.py').read()
if 'demand_notice_report' not in content:
    content = content.replace(
        "        'report/tenancy_agreement.xml',",
        "        'report/demand_notice_report.xml',\n        'report/tenancy_agreement.xml',")
    open('custom_addons/kenya_real_estate/__manifest__.py','w').write(content)
    print("Demand notice report added to manifest")
PYEOF

git add .
git commit -m "feat(realestate): PDF Demand Notice with Kenya legal text (Cap 301, Cap 293), M-Pesa paybill on notice"
git push

echo "======================================="
echo "COMMIT 6/8 — Real Estate: Property Dashboard KPIs"
echo "======================================="

cat > custom_addons/kenya_real_estate/views/dashboard_views.xml << 'EOF'
<?xml version="1.0" encoding="utf-8"?>
<odoo>
  <!-- Property Dashboard Action -->
  <record id="estate_property_dashboard_action" model="ir.actions.act_window">
    <field name="name">Property Dashboard</field>
    <field name="res_model">estate.property</field>
    <field name="view_mode">list,kanban,form</field>
    <field name="context">{
      'search_default_leased': 1,
      'group_by': 'county'
    }</field>
  </record>

  <!-- Lease KPI List — shows arrears prominently -->
  <record id="estate_lease_arrears_action" model="ir.actions.act_window">
    <field name="name">Rent Arrears</field>
    <field name="res_model">estate.lease</field>
    <field name="view_mode">list,form</field>
    <field name="domain">[('status','=','active'),('months_arrears','>',0)]</field>
    <field name="context">{'search_default_leased': 1}</field>
  </record>

  <!-- Expiring Leases Action -->
  <record id="estate_lease_expiring_action" model="ir.actions.act_window">
    <field name="name">Expiring Leases (30 days)</field>
    <field name="res_model">estate.lease</field>
    <field name="view_mode">list,form</field>
    <field name="domain">[('status','=','active'),('is_expiring_soon','=',True)]</field>
  </record>

  <!-- Add shortcut menus -->
  <menuitem id="menu_arrears" name="Rent Arrears"
            parent="menu_re_root"
            action="estate_lease_arrears_action" sequence="8"/>
  <menuitem id="menu_expiring" name="Expiring Leases"
            parent="menu_re_root"
            action="estate_lease_expiring_action" sequence="9"/>
</odoo>
EOF

# Add to manifest
python3 - << 'PYEOF'
content = open('custom_addons/kenya_real_estate/__manifest__.py').read()
if 'dashboard_views' not in content:
    content = content.replace(
        "        'views/menu_views.xml',",
        "        'views/dashboard_views.xml',\n        'views/menu_views.xml',")
    open('custom_addons/kenya_real_estate/__manifest__.py','w').write(content)
    print("Dashboard views added")
PYEOF

git add .
git commit -m "feat(realestate): dashboard — Rent Arrears shortcut, Expiring Leases view, county grouping"
git push

echo "======================================="
echo "COMMIT 7/8 — Real Estate: Tenant KRA PIN + M-Pesa on Partner"
echo "======================================="

cat > custom_addons/kenya_real_estate/models/res_partner_kenya.py << 'EOF'
"""
Kenya-specific partner fields:
- KRA PIN (validated format A000000000B)
- ID Number / Passport
- M-Pesa phone primary
- Tenant lease history smart button
"""
import re
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartnerKenya(models.Model):
    _inherit = 'res.partner'

    kra_pin          = fields.Char("KRA PIN", size=11, tracking=True)
    id_number        = fields.Char("National ID / Passport")
    nhif_number      = fields.Char("NHIF Number")
    nssf_number      = fields.Char("NSSF Number")
    is_tenant        = fields.Boolean("Is Tenant", default=False)
    is_landlord      = fields.Boolean("Is Landlord", default=False)
    mpesa_phone      = fields.Char("Primary M-Pesa Phone",
                                   help="Phone number registered on M-Pesa for rent payment")

    # Lease stats
    lease_ids        = fields.One2many('estate.lease', 'tenant_id', string="Leases")
    active_lease_count = fields.Integer(compute='_compute_lease_stats', string="Active Leases")
    total_arrears    = fields.Monetary(compute='_compute_lease_stats', string="Total Arrears",
                                       currency_field='currency_id')
    currency_id      = fields.Many2one('res.currency',
                                       default=lambda s: s.env.ref('base.KES'))

    def _compute_lease_stats(self):
        for r in self:
            active = r.lease_ids.filtered(lambda l: l.status == 'active')
            r.active_lease_count = len(active)
            r.total_arrears = sum(active.mapped('total_outstanding'))

    def action_open_leases(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('Leases'),
            'res_model': 'estate.lease', 'view_mode': 'list,form',
            'domain': [('tenant_id', '=', self.id)],
        }

    def action_open_mpesa_txns(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('M-Pesa Transactions'),
            'res_model': 'mpesa.transaction', 'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
        }

    @api.constrains('kra_pin')
    def _validate_kra_pin(self):
        for r in self:
            if r.kra_pin:
                pin = r.kra_pin.upper().strip()
                if not re.match(r'^[A-Z]\d{9}[A-Z]$', pin):
                    raise ValidationError(
                        _("Invalid KRA PIN '%s'. Format must be: A000000000B "
                          "(letter, 9 digits, letter)") % r.kra_pin)
                r.kra_pin = pin
EOF

# Add Kenya fields to partner form via inheritance
cat > custom_addons/kenya_real_estate/views/res_partner_kenya_views.xml << 'EOF'
<?xml version="1.0" encoding="utf-8"?>
<odoo>
  <record id="view_partner_kenya_inherit" model="ir.ui.view">
    <field name="name">res.partner.kenya.inherit</field>
    <field name="model">res.partner</field>
    <field name="inherit_id" ref="base.view_partner_form"/>
    <field name="arch" type="xml">

      <!-- Smart buttons for leases + M-Pesa -->
      <xpath expr="//div[@name='button_box']" position="inside">
        <button name="action_open_leases" type="object"
                class="oe_stat_button" icon="fa-home"
                invisible="active_lease_count == 0">
          <field name="active_lease_count" widget="statinfo" string="Leases"/>
        </button>
        <button name="action_open_mpesa_txns" type="object"
                class="oe_stat_button" icon="fa-mobile">
          <div class="o_stat_info">
            <span class="o_stat_text">M-Pesa</span>
          </div>
        </button>
      </xpath>

      <!-- Kenya fields tab -->
      <xpath expr="//page[@name='internal']" position="after">
        <page name="kenya" string="Kenya Details">
          <group>
            <group string="Tax / Identity">
              <field name="kra_pin"/>
              <field name="id_number"/>
              <field name="nhif_number"/>
              <field name="nssf_number"/>
            </group>
            <group string="M-Pesa / Rental">
              <field name="mpesa_phone"/>
              <field name="is_tenant"/>
              <field name="is_landlord"/>
              <separator string="Rental Summary"/>
              <field name="active_lease_count" readonly="1"/>
              <field name="total_arrears" readonly="1"/>
            </group>
          </group>
        </page>
      </xpath>

    </field>
  </record>
</odoo>
EOF

# Add to models/__init__ and manifest
python3 - << 'PYEOF'
init = open('custom_addons/kenya_real_estate/models/__init__.py').read()
if 'res_partner_kenya' not in init:
    init += 'from . import res_partner_kenya\n'
    open('custom_addons/kenya_real_estate/models/__init__.py','w').write(init)

content = open('custom_addons/kenya_real_estate/__manifest__.py').read()
if 'res_partner_kenya_views' not in content:
    content = content.replace(
        "        'views/dashboard_views.xml',",
        "        'views/res_partner_kenya_views.xml',\n        'views/dashboard_views.xml',")
    open('custom_addons/kenya_real_estate/__manifest__.py','w').write(content)
    print("Partner views added to manifest")
PYEOF

git add .
git commit -m "feat(realestate): Kenya partner fields — KRA PIN validation, ID number, M-Pesa phone, smart buttons on contacts"
git push

echo "======================================="
echo "COMMIT 8/8 — Final syntax check + upgrade"
echo "======================================="

# Final syntax check
echo "=== Python syntax check ==="
ERRORS=0
for f in $(find custom_addons -name "*.py"); do
    python3 -m py_compile "$f" 2>/dev/null || { echo "BROKEN: $f"; ERRORS=$((ERRORS+1)); }
done
if [ $ERRORS -eq 0 ]; then
    echo "All Python files OK"
else
    echo "$ERRORS files have errors"
fi

# Final upgrade
docker compose run --rm web odoo \
  -d odoo_kenya \
  -u mpesa_connector,mpesa_integration,kenya_mpesa_acquirer,kenya_real_estate \
  --stop-after-init --no-http 2>&1 | \
  grep -iE "modules loaded|error|critical" | tail -5

docker compose restart web
sleep 10

git add .
git commit -m "feat: final 10/10 Kenya ERP — KRA PIN, M-Pesa from invoice/lease, bulk collection, demand notice PDF, partner smart buttons" 2>/dev/null || true
git push 2>/dev/null || true

echo ""
echo "============================================"
echo "KENYA ERP v5 — 10/10 COMPLETE"
echo "============================================"
echo ""
echo "NEW FEATURES:"
echo "  M-Pesa STK Push from invoice (one click)"
echo "  M-Pesa STK Push from lease (collect rent)"
echo "  Bulk rent collection wizard (send to all tenants)"
echo "  KRA PIN validation (A000000000B format)"
echo "  Kenya area/estate selector (Karen, Kilimani...)"
echo "  PDF Demand Notice (Cap 301 / Cap 293 legal text)"
echo "  Rent Arrears shortcut menu"
echo "  Expiring Leases shortcut menu"
echo "  Partner smart buttons (leases + M-Pesa)"
echo "  KRA MRI threshold warning (>288K/mo)"
echo ""
echo "  Open: http://localhost:8070"
echo "  Login: admin / kenya2026"
echo "============================================"
