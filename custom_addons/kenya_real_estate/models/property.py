from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class EstateProperty(models.Model):
    _name        = 'estate.property'
    _description = 'Real Estate Property'
    _inherit     = ['mail.thread', 'mail.activity.mixin']
    _order       = 'name'
    _rec_name    = 'name'

    # ── Identity ──────────────────────────────────────
    name             = fields.Char("Property Name", required=True, tracking=True)
    ref              = fields.Char("Property Ref", readonly=True, copy=False, default='New')
    property_type_id = fields.Many2one('estate.property.type', string="Category", tracking=True)
    tag_ids          = fields.Many2many('estate.property.tag', string="Tags")
    amenity_ids      = fields.Many2many('estate.amenity', string="Amenities")
    active           = fields.Boolean(default=True)

    # ── Classification ────────────────────────────────
    property_type = fields.Selection([
        ('residential', 'Residential'),
        ('commercial',  'Commercial'),
        ('land',        'Land'),
        ('industrial',  'Industrial'),
    ], string="Type", required=True, default='residential', tracking=True)

    status = fields.Selection([
        ('available',   'Available'),
        ('leased',      'Leased'),
        ('for_sale',    'For Sale'),
        ('sold',        'Sold'),
        ('maintenance', 'Under Maintenance'),
    ], string="Status", default='available', tracking=True)

    # ── Ownership ─────────────────────────────────────
    landlord_id      = fields.Many2one('res.partner', string="Landlord/Owner",
                                       required=True, tracking=True)
    agent_id         = fields.Many2one('res.users', string="Listing Agent")
    management_fee   = fields.Float("Management Fee (%)", default=10.0,
                                    help="Agent management fee as % of rent")

    # ── Location ──────────────────────────────────────
    street           = fields.Char("Street Address")
    location         = fields.Char("Estate / Area")
    constituency     = fields.Char("Constituency")
    county           = fields.Char("County")
    latitude         = fields.Float("GPS Latitude",  digits=(10, 7))
    longitude        = fields.Float("GPS Longitude", digits=(10, 7))

    # ── Physical ──────────────────────────────────────
    bedrooms         = fields.Integer("Bedrooms")
    bathrooms        = fields.Integer("Bathrooms")
    size_sqft        = fields.Float("Size (sq ft)")
    floor            = fields.Integer("Floor Number")
    total_floors     = fields.Integer("Total Floors")
    year_built       = fields.Integer("Year Built")
    furnished        = fields.Selection([
        ('unfurnished', 'Unfurnished'),
        ('semi',        'Semi-Furnished'),
        ('fully',       'Fully Furnished'),
    ], default='unfurnished')
    parking_spaces   = fields.Integer("Parking Spaces")
    garden           = fields.Boolean("Garden / Compound")
    garden_area_sqft = fields.Float("Garden Area (sq ft)")

    # ── Financials ────────────────────────────────────
    currency_id      = fields.Many2one('res.currency',
                                       default=lambda s: s.env.ref('base.KES'))
    monthly_rent     = fields.Monetary("Monthly Rent (KES)",
                                       currency_field='currency_id', tracking=True)
    sale_price       = fields.Monetary("Sale Price (KES)",
                                       currency_field='currency_id')
    acquisition_cost = fields.Monetary("Acquisition Cost (KES)",
                                       currency_field='currency_id',
                                       help="Purchase price + stamp duty + legal fees")
    stamp_duty       = fields.Monetary("Stamp Duty (KES)", currency_field='currency_id')
    legal_fees       = fields.Monetary("Legal Fees (KES)", currency_field='currency_id')
    annual_insurance = fields.Monetary("Annual Insurance (KES)",
                                       currency_field='currency_id')
    insurance_expiry = fields.Date("Insurance Expiry Date")

    # ── Computed Financials ───────────────────────────
    annual_revenue   = fields.Monetary("Annual Gross Revenue (KES)",
                                       currency_field='currency_id',
                                       compute='_compute_financials', store=True)
    total_revenue    = fields.Monetary("Total Revenue Collected (KES)",
                                       currency_field='currency_id',
                                       compute='_compute_financials', store=True)
    total_expenses   = fields.Monetary("Total Expenses (KES)",
                                       currency_field='currency_id',
                                       compute='_compute_financials', store=True)
    net_income       = fields.Monetary("Net Operating Income (KES)",
                                       currency_field='currency_id',
                                       compute='_compute_financials', store=True)
    gross_yield      = fields.Float("Gross Yield (%)",
                                    compute='_compute_financials', store=True)
    cap_rate         = fields.Float("Cap Rate (%)",
                                    compute='_compute_financials', store=True)
    total_arrears    = fields.Monetary("Total Arrears (KES)",
                                       currency_field='currency_id',
                                       compute='_compute_financials', store=True)
    occupancy_days   = fields.Integer("Days Occupied",
                                      compute='_compute_occupancy', store=True)
    vacancy_days     = fields.Integer("Days Vacant (This Year)",
                                      compute='_compute_occupancy', store=True)
    vacancy_loss     = fields.Monetary("Vacancy Revenue Loss (KES)",
                                       currency_field='currency_id',
                                       compute='_compute_occupancy', store=True)
    landlord_payout  = fields.Monetary("Landlord Net Payout (KES/mo)",
                                       currency_field='currency_id',
                                       compute='_compute_landlord_payout', store=True)

    # ── Relations ─────────────────────────────────────
    lease_ids        = fields.One2many('estate.lease', 'property_id', string="Leases")
    offer_ids        = fields.One2many('estate.offer', 'property_id', string="Offers")
    commission_ids   = fields.One2many('estate.commission', 'property_id',
                                       string="Commissions")
    inspection_ids   = fields.One2many('estate.inspection', 'property_id',
                                       string="Inspections")
    maintenance_ids  = fields.One2many('estate.maintenance.request', 'property_id',
                                       string="Maintenance")
    unit_ids         = fields.One2many('estate.unit', 'property_id', string="Units")

    # ── Computed Counts ───────────────────────────────
    lease_count       = fields.Integer(compute='_compute_counts', store=True)
    offer_count       = fields.Integer(compute='_compute_counts', store=True)
    maintenance_count = fields.Integer(compute='_compute_counts', store=True)
    inspection_count  = fields.Integer(compute='_compute_counts', store=True)

    active_lease_id   = fields.Many2one('estate.lease',
                                        compute='_compute_active_lease',
                                        string="Current Lease", store=True)
    current_tenant_id = fields.Many2one('res.partner',
                                        compute='_compute_active_lease',
                                        string="Current Tenant", store=True)

    # ── Media ─────────────────────────────────────────
    image_1920       = fields.Image("Main Photo", max_width=1920, max_height=1920)
    image_128        = fields.Image("Thumbnail", related='image_1920',
                                    max_width=128, max_height=128, store=True)
    description      = fields.Html("Description")

    # ═══════════════ COMPUTE METHODS ════════════════ #


    _sql_constraints = [
        ('ref_unique', 'UNIQUE(ref)', 'Property reference must be unique.'),
        ('monthly_rent_positive', 'CHECK(monthly_rent >= 0)', 'Monthly rent cannot be negative.'),
        ('sale_price_positive', 'CHECK(sale_price >= 0)', 'Sale price cannot be negative.'),
    ]

    @api.depends('lease_ids', 'offer_ids', 'maintenance_ids', 'inspection_ids')
    def _compute_counts(self):
        for rec in self:
            rec.lease_count       = len(rec.lease_ids)
            rec.offer_count       = len(rec.offer_ids)
            rec.maintenance_count = len(rec.maintenance_ids)
            rec.inspection_count  = len(rec.inspection_ids)

    @api.depends('lease_ids.status', 'lease_ids.tenant_id')
    def _compute_active_lease(self):
        for rec in self:
            active = rec.lease_ids.filtered(lambda l: l.status == 'active')
            rec.active_lease_id   = active[0] if active else False
            rec.current_tenant_id = active[0].tenant_id if active else False

    @api.depends(
        'monthly_rent', 'sale_price', 'acquisition_cost',
        'annual_insurance', 'management_fee',
        'lease_ids.payment_ids.payment_state',
        'lease_ids.payment_ids.amount_total',
        'lease_ids.payment_ids.amount_residual',
        'maintenance_ids.actual_cost',
    )
    def _compute_financials(self):
        for rec in self:
            # Revenue
            invoices = rec.env['account.move'].search([
                ('lease_id.property_id', '=', rec.id),
                ('move_type', '=', 'out_invoice'),
            ])
            paid_invoices = invoices.filtered(lambda i: i.payment_state == 'paid')
            unpaid        = invoices.filtered(lambda i: i.payment_state != 'paid')

            gross_revenue = sum(paid_invoices.mapped('amount_total'))
            arrears       = sum(unpaid.mapped('amount_residual'))

            # Expenses
            maint_cost    = sum(rec.maintenance_ids.mapped('actual_cost'))
            mgmt_fee      = rec.monthly_rent * rec.management_fee / 100
            annual_mgmt   = mgmt_fee * 12
            total_expenses = maint_cost + (rec.annual_insurance or 0) + annual_mgmt

            # NOI & yields
            annual_gross  = rec.monthly_rent * 12
            noi           = annual_gross - total_expenses
            cap_rate      = (noi / rec.acquisition_cost * 100) if rec.acquisition_cost else 0.0
            gross_yield   = (annual_gross / rec.sale_price * 100) if rec.sale_price else 0.0

            rec.annual_revenue  = annual_gross
            rec.total_revenue   = gross_revenue
            rec.total_expenses  = total_expenses
            rec.net_income      = noi
            rec.cap_rate        = cap_rate
            rec.gross_yield     = gross_yield
            rec.total_arrears   = arrears

    @api.depends('monthly_rent', 'management_fee', 'annual_insurance')
    def _compute_landlord_payout(self):
        for rec in self:
            mgmt_deduction = rec.monthly_rent * rec.management_fee / 100
            insurance_mo   = (rec.annual_insurance or 0) / 12
            # KRA WHT: 10% commercial, 5% residential (Section 35 KITA)
            wht_rate       = 0.10 if rec.property_type == 'commercial' else 0.05
            wht            = rec.monthly_rent * wht_rate
            rec.landlord_payout = rec.monthly_rent - mgmt_deduction - insurance_mo - wht

    @api.depends('lease_ids.date_start', 'lease_ids.date_end', 'lease_ids.status')
    def _compute_occupancy(self):
        from datetime import date
        today     = fields.Date.today()
        year_start = date(today.year, 1, 1)

        for rec in self:
            occupied = 0
            for lease in rec.lease_ids:
                if lease.status not in ('active', 'expired', 'renewed'):
                    continue
                if not lease.date_start or not lease.date_end:
                    continue
                start = max(lease.date_start, year_start)
                end   = min(lease.date_end, today)
                if end > start:
                    occupied += (end - start).days

            year_days          = (today - year_start).days or 1
            rec.occupancy_days = occupied
            rec.vacancy_days   = max(year_days - occupied, 0)
            daily_rate         = rec.monthly_rent / 30
            rec.vacancy_loss   = rec.vacancy_days * daily_rate

    # ═══════════════ ACTIONS ════════════════════════ #

    def action_open_leases(self):
        self.ensure_one()
        return self._open_window('estate.lease', 'property_id', 'Leases')

    def action_open_offers(self):
        self.ensure_one()
        return self._open_window('estate.offer', 'property_id', 'Offers & Enquiries')

    def action_open_maintenance(self):
        self.ensure_one()
        return self._open_window('estate.maintenance.request',
                                 'property_id', 'Maintenance Requests')

    def action_open_inspections(self):
        self.ensure_one()
        return self._open_window('estate.inspection', 'property_id', 'Inspections')

    def _open_window(self, model, field, name):
        return {
            'type':      'ir.actions.act_window',
            'name':      name,
            'res_model': model,
            'view_mode': 'list,form',
            'domain':    [(field, '=', self.id)],
            'context':   {f'default_{field}': self.id},
        }

    def action_set_available(self):
        self.write({'status': 'available'})

    def action_set_for_sale(self):
        self.write({'status': 'for_sale'})

    def action_generate_rent_roll(self):
        """Generate rent roll report for this property."""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Rent Roll — {self.name}',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [
                ('lease_id.property_id', '=', self.id),
                ('move_type', '=', 'out_invoice'),
            ],
        }

    # ═══════════════ CRUD ═══════════════════════════ #

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('ref', 'New') == 'New':
                vals['ref'] = (
                    self.env['ir.sequence'].next_by_code('estate.property') or 'New'
                )
        return super().create(vals_list)