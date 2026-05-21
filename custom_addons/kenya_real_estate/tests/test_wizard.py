from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from datetime import date


class TestRentWizard(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.landlord = cls.env['res.partner'].create({'name': 'Wizard Landlord'})
        cls.tenant   = cls.env['res.partner'].create({'name': 'Wizard Tenant'})
        prop = cls.env['estate.property'].create({
            'name': 'Wizard Test Property',
            'property_type': 'residential',
            'landlord_id': cls.landlord.id,
            'monthly_rent': 45000,
        })
        cls.lease = cls.env['estate.lease'].create({
            'property_id': prop.id,
            'tenant_id': cls.tenant.id,
            'date_start': date(2026, 1, 1),
            'date_end': date(2026, 12, 31),
        })
        cls.lease.action_activate()

    def test_wizard_generates_invoices(self):
        wizard = self.env['estate.rent.payment.wizard'].create({
            'lease_ids': [(6, 0, [self.lease.id])],
            'invoice_date': date.today(),
        })
        result = wizard.action_generate_invoices()
        self.assertEqual(result['res_model'], 'account.move')
        invoices = self.env['account.move'].search(result['domain'])
        self.assertEqual(len(invoices), 1)
        self.assertEqual(invoices.partner_id, self.tenant)

    def test_wizard_raises_without_leases(self):
        wizard = self.env['estate.rent.payment.wizard'].create({
            'lease_ids': [(5,)],
            'invoice_date': date.today(),
        })
        with self.assertRaises(UserError):
            wizard.action_generate_invoices()
