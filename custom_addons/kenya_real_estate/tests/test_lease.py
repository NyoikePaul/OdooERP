from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from datetime import date


class TestEstateLease(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.landlord = cls.env['res.partner'].create({'name': 'Landlord Test'})
        cls.tenant   = cls.env['res.partner'].create({'name': 'Tenant Test'})
        cls.prop = cls.env['estate.property'].create({
            'name': 'Test Flat Nairobi',
            'property_type': 'residential',
            'landlord_id': cls.landlord.id,
            'monthly_rent': 60000,
        })

    def _make_lease(self, **kwargs):
        vals = {
            'property_id': self.prop.id,
            'tenant_id': self.tenant.id,
            'date_start': date(2026, 1, 1),
            'date_end': date(2026, 12, 31),
        }
        vals.update(kwargs)
        return self.env['estate.lease'].create(vals)

    def test_lease_auto_ref(self):
        lease = self._make_lease()
        self.assertIn('LEASE/', lease.name)

    def test_activate_lease_updates_property(self):
        lease = self._make_lease()
        self.assertEqual(lease.status, 'draft')
        lease.action_activate()
        self.assertEqual(lease.status, 'active')
        self.assertEqual(self.prop.status, 'leased')

    def test_cancel_lease_frees_property(self):
        lease = self._make_lease()
        lease.action_activate()
        lease.action_cancel()
        self.assertEqual(lease.status, 'cancelled')
        self.assertEqual(self.prop.status, 'available')

    def test_date_validation_end_before_start_raises(self):
        with self.assertRaises(ValidationError):
            self._make_lease(
                date_start=date(2026, 12, 31),
                date_end=date(2026, 1, 1),
            )

    def test_generate_rent_invoice(self):
        lease = self._make_lease()
        lease.action_activate()
        result = lease.action_generate_rent_invoice()
        self.assertEqual(result['res_model'], 'account.move')
        invoice = self.env['account.move'].browse(result['res_id'])
        self.assertEqual(invoice.partner_id, self.tenant)
        self.assertEqual(invoice.lease_id, lease)
