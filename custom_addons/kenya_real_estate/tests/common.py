"""
Common test base classes and shared fixtures for kenya_real_estate tests.
Following OCA / odoo/odoo testing patterns.
"""
from odoo.tests.common import TransactionCase
from odoo import fields


class EstateTestCommon(TransactionCase):
    """Base class with shared test data for all Real Estate tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # ── Partners ──────────────────────────────
        cls.landlord = cls.env['res.partner'].create({
            'name':         'Test Landlord Ltd',
            'company_type': 'company',
            'city':         'Nairobi',
            'country_id':   cls.env.ref('base.ke').id,
        })
        cls.tenant_1 = cls.env['res.partner'].create({
            'name':    'Test Tenant One',
            'city':    'Nairobi',
            'phone':   '+254712345678',
            'email':   'tenant1@test.com',
            'country_id': cls.env.ref('base.ke').id,
        })
        cls.tenant_2 = cls.env['res.partner'].create({
            'name':  'Test Tenant Two Ltd',
            'company_type': 'company',
            'city':  'Mombasa',
            'phone': '+254733456789',
            'country_id': cls.env.ref('base.ke').id,
        })

        # ── Property Type ──────────────────────────
        cls.prop_type = cls.env['estate.property.type'].create({
            'name': 'Test Apartment',
        })

        # ── Properties ────────────────────────────
        cls.property_residential = cls.env['estate.property'].create({
            'name':          'Test Kilimani Apartment',
            'property_type': 'residential',
            'property_type_id': cls.prop_type.id,
            'landlord_id':   cls.landlord.id,
            'monthly_rent':  75000,
            'county':        'Nairobi',
            'bedrooms':      3,
            'bathrooms':     2,
        })
        cls.property_commercial = cls.env['estate.property'].create({
            'name':          'Test Westlands Office',
            'property_type': 'commercial',
            'landlord_id':   cls.landlord.id,
            'monthly_rent':  120000,
            'county':        'Nairobi',
        })

        # ── Building + Units ──────────────────────
        cls.building = cls.env['estate.building'].create({
            'name':        'Test Building',
            'landlord_id': cls.landlord.id,
            'county':      'Nairobi',
        })
        cls.unit_1a = cls.env['estate.unit'].create({
            'name':         '1A',
            'building_id':  cls.building.id,
            'unit_type':    '2br',
            'monthly_rent': 65000,
            'floor':        1,
        })

    def _make_active_lease(self, property_id=None, tenant_id=None,
                           start='2026-01-01', end='2026-12-31',
                           monthly_rent=None):
        """Helper: create and activate a lease."""
        prop   = property_id or self.property_residential
        tenant = tenant_id or self.tenant_1
        lease  = self.env['estate.lease'].create({
            'property_id':  prop.id,
            'tenant_id':    tenant.id,
            'date_start':   start,
            'date_end':     end,
            'monthly_rent': monthly_rent or prop.monthly_rent,
            'deposit':      (monthly_rent or prop.monthly_rent) * 2,
            'deposit_paid': True,
        })
        lease.action_activate()
        return lease
