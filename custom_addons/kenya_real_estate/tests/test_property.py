from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestEstateProperty(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.landlord = cls.env['res.partner'].create({
            'name': 'Test Landlord Kenya',
            'city': 'Nairobi',
        })

    def _make_property(self, **kwargs):
        vals = {
            'name': 'Test Property',
            'property_type': 'residential',
            'landlord_id': self.landlord.id,
            'monthly_rent': 50000,
            'county': 'Nairobi',
        }
        vals.update(kwargs)
        return self.env['estate.property'].create(vals)

    def test_default_status_is_available(self):
        prop = self._make_property()
        self.assertEqual(prop.status, 'available')

    def test_auto_ref_generated(self):
        prop = self._make_property()
        self.assertNotEqual(prop.ref, 'New')
        self.assertIn('PROP/', prop.ref)

    def test_lease_count_computed(self):
        prop = self._make_property()
        self.assertEqual(prop.lease_count, 0)

    def test_multiple_property_types(self):
        for ptype in ('residential', 'commercial', 'land', 'industrial'):
            prop = self._make_property(property_type=ptype, name=f'Test {ptype}')
            self.assertEqual(prop.property_type, ptype)
