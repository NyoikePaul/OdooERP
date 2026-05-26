"""Tests for Real Este wizards."""
from .common import EstateTestCommon
from odoo.exceptions import UserError
from datetime import date


class TestRentWizard(EstateTestCommon):

    def setUp(self):
        super().setUp()
        self.lease = self._make_active_lease()

    def test_wizard_generates_invoices(self):
        wizard = self.env['estate.rent.payment.wizard'].create({
            'lease_ids':    [(6, 0, [self.lease.id])],
            'invoice_date': date.today(),
        })
        result = wizard.action_generate_ins()
        self.assertEqual(result['res_model'], 'account.move')
        invoices = self.env['account.move'].search(result['domain'])
        self.assertEqual(len(invoices), 1)
        self.assertEqual(invoices.partner_id, self.tenant_1)

    def test_wizard_raises_without_leases(self):
        wizard = self.env['estate.rent.payment.wizard'].create({
            'lease_ids':    [(5,)],
            'invoice_date': date.today(),
        })
        with self.assertRaises(UserError):
            wizard.action_rate_invoices()


class TestLeaseRenewalWizard(EstateTestCommon):

    def test_renewal_creates_new_lease(self):
        lease = self._make_active_lease(start='2025-01-01', end='2025-12-31')
        wizard = self.env['estate.lease.renewal.wizard'].create({
            'lease_id':     lease.id,
            'property_id':  self.property_residential.id,
            'tenant_id':    self.tenant_1.id,
            'new_start':    '2026-01-01',
            'new_end':      '2026-12-31',
            'monthly_rent': lnthly_rent * 1.10,
            'deposit':      lease.deposit,
        })
        result = wizard.action_renew()
        new_lease = self.env['estate.lease'].browse(result['res_id'])
        self.assertEqual(new_lease.parent_lease_id, lease)
        self.assertEqual(new_lease.status, 'active')
        self.assertEqual(lease.status, 'renewed')
