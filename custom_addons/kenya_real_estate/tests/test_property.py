"""Tests for estate.property model."""
from .common import EstateTestCommon
from odoo.exceptions import ValidationError


class TestEstateProperty(EstateTestCommon):

    def test_default_status_is_available(self):
        self.assertEqual(self.property_residential.status, 'available')

    def test_auto_ref_generated(self):
        self.assertNotEqual(self.property_residential.ref, 'New')
        self.assertIn('PROP/', self.property_residential.ref)

    def test_lease_count_computed(self):
        self.assertEqual(self.property_residential.lease_count, 0)
        self._make_active_lease()
        self.assertEqual(self.property_residential.lease_count, 1)

    def test_current_tenant_from_active_lease(self):
        self.assertFalse(self.property_residential.current_tenant_id)
        lease = self._make_active_lease()
        self.assertEqual(self.property_residential.current_tenant_id, self.tenant_1)

    def test_action_set_for_sale(self):
        self.property_residential.action_set_for_sale()
        self.assertEqual(self.property_residential.status, 'for_sale')

    def test_action_set_available(self):
        self.property_residential.write({'status': 'for_sale'})
        self.property_residential.action_set_available()
        self.assertEqual(self.property_residential.status, 'available')
