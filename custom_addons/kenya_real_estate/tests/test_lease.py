"""Tests for estate.lease model."""
from .common import EstateTestCommon
from odoo.exceptions import ValidationError
from datetime import date


class TestEstateLease(EstateTestCommon):

    def test_lease_auto_ref(self):
        lease = self._make_active_lease()
        self.assertIn('LEASE/', lease.name)

    def test_activate_lease_updates_property(self):
        lease = self._make_active_lease()
        self.assertEqual(lease.status, 'active')
        self.assertEqual(self.property_residential.status, 'leased')

    def test_cancel_lease_frees_property(self):
        lease = self._make_active_lease()
        lease.action_cancel()
        self.assertEqual(lease.status, 'cancelled')
        self.assertEqual(self.property_residential.status, 'available')

    def test_expire_sets_property_available(self):
        lease = self._make_active_lease()
        lease.action_expire()
        self.assertEqual(lease.status, 'expired')
        self.assertEqual(self.property_residential.status, 'available')

    def test_surrender_workflow(self):
        lease = self._make_active_lease()
        lease.action_surrender()
        self.assertEqual(lease.status, 'surrendered')
        self.assertEqual(self.property_residential.status, 'available')

    def test_date_validation_end_before_start(self):
        with self.assertRaises(ValidationError):
            self.env['estate.lease'].create({
                'property_id':  self.property_commercial.id,
                'tenant_id':    self.tenant_1.id,
                'date_start':   '2026-12-31',
                'date_end':     '2026-01-01',
                'deposit_paid': True,
            })

    def test_generate_rent_invoice(self):
        lease = self._make_active_lease()
        result = lease.action_generate_rent_invoice()
        self.assertEqual(result['res_model'], 'account.move')
        inv = self.env['account.move'].browse(result['res_id'])
        self.assertEqual(inv.partner_id, self.tenant_1)
        self.assertEqual(inv.lease_id, lease)

    def test_invoice_includes_service_charge(self):
        lease = self._make_active_lease()
        lease.write({'service_charge': 5000})
        result = lease.action_generate_rent_invoice()
        inv = self.env['account.move'].browse(result['res_id'])
        self.assertEqual(len(inv.invoice_line_ids), 2)
