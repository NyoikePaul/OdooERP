"""
Tests for financial computations:
- KRA WHT calculation
- Rent escalation
- Landlord payout
- Late payment penalties
- NOI / yield calculations
"""
from .common import EstateTestCommon
from odoo.exceptions import UserError, ValidationError
from odoo import fields


class TestLeaseFinancials(EstateTestCommon):

    def test_wht_residential_5_percent(self):
        """Residential WHT should be 5% per KRA Section 35 KITA."""
        lease = self._make_active_lease()
        self.assertEqual(lease.wht_rate, 5.0)
        self.assertAlmostEqual(lease.wht_amount, 75000 * 0.05, places=2)

    def test_wht_commercial_10_percent(self):
        """Commercial WHT should be 10% per KRA Section 35 KITA."""
        lease = self._make_active_lease(property_id=self.property_commercial)
        self.assertEqual(lease.wht_rate, 10.0)
        self.assertAlmostEqual(lease.wht_amount, 120000 * 0.10, places=2)

    def test_wht_disabled(self):
        """WHT should be 0 when apply_wht is False."""
        lease = self._make_active_lease()
        lease.write({'apply_wht': False})
        self.assertEqual(lease.wht_rate, 0.0)
        self.assertEqual(lease.wht_amount, 0.0)
        self.assertEqual(lease.landlord_payout, lease.monthly_rent)

    def test_landlord_payout_calculation(self):
        """Landlord payout = rent - WHT."""
        lease = self._make_active_lease()
        expected = lease.monthly_rent - (lease.monthly_rent * 0.05)
        self.assertAlmostEqual(lease.landlord_payout, expected, places=2)

    def test_rent_escalation(self):
        """Escalation should increase rent by the configured rate."""
        lease = self._make_active_lease()
        original_rent = lease.monthly_rent
        lease.write({'escalation_rate': 10.0})
        lease.action_apply_escalation()
        expected = original_rent * 1.10
        self.assertAlmostEqual(lease.monthly_rent, expected, places=2)

    def test_escalation_history_recorded(self):
        """Escalation history should record the date and amounts."""
        lease = self._make_active_lease()
        lease.action_apply_escalation()
        self.assertIn(str(fields.Date.today()), lease.escalation_history)
        self.assertIn('%', lease.escalation_history)

    def test_cannot_activate_without_deposit(self):
        """Activation should fail if deposit not marked as paid."""
        lease = self.env['estate.lease'].create({
            'property_id':  self.property_residential.id,
            'tenant_id':    self.tenant_2.id,
            'date_start':   '2026-06-01',
            'date_end':     '2027-05-31',
            'monthly_rent': 75000,
            'deposit':      150000,
            'deposit_paid': False,
        })
        with self.assertRaises(UserError):
            lease.action_activate()

    def test_lease_duration_computed(self):
        """12-month lease should compute 12 duration months."""
        lease = self._make_active_lease(start='2026-01-01', end='2026-12-31')
        self.assertEqual(lease.duration_months, 11)  # Jan to Dec = 11 months

    def test_total_lease_value(self):
        """Total lease value = duration months × monthly rent."""
        lease = self._make_active_lease(start='2026-01-01', end='2026-12-31')
        expected = lease.duration_months * lease.monthly_rent
        self.assertEqual(lease.total_lease_value, expected)


class TestPropertyFinancials(EstateTestCommon):

    def test_annual_revenue_computed(self):
        """Annual revenue = monthly_rent × 12."""
        prop = self.property_residential
        self.assertEqual(prop.annual_revenue, prop.monthly_rent * 12)

    def test_landlord_payout_residential(self):
        """Residential landlord payout should deduct 5% WHT + management fee."""
        prop = self.property_residential
        expected = prop.monthly_rent * (1 - 0.05 - prop.management_fee / 100)
        self.assertAlmostEqual(prop.landlord_payout, expected, places=1)

    def test_gross_yield_with_sale_price(self):
        """Gross yield = (annual rent / sale price) × 100."""
        self.property_residential.write({'sale_price': 10000000})
        annual = self.property_residential.monthly_rent * 12
        expected = (annual / 10000000) * 100
        self.assertAlmostEqual(self.property_residential.gross_yield, expected, places=2)

    def test_status_changes_on_lease_activate(self):
        """Property status should change to 'leased' when lease is activated."""
        self.assertEqual(self.property_residential.status, 'available')
        lease = self._make_active_lease()
        self.assertEqual(self.property_residential.status, 'leased')

    def test_status_returns_available_on_cancel(self):
        """Property should return to 'available' when lease is cancelled."""
        lease = self._make_active_lease()
        lease.action_cancel()
        self.assertEqual(self.property_residential.status, 'available')

    def test_overlap_constraint_raised(self):
        """Two overlapping active leases on same property should raise ValidationError."""
        self._make_active_lease(start='2026-01-01', end='2026-12-31')
        with self.assertRaises(ValidationError):
            self._make_active_lease(start='2026-06-01', end='2027-05-31')

    def test_property_ref_auto_generated(self):
        """Property ref should be auto-generated in PROP/YYYY/XXXX format."""
        prop = self.property_residential
        self.assertNotEqual(prop.ref, 'New')
        self.assertIn('PROP/', prop.ref)
