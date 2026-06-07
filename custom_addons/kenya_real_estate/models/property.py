from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class EstateProperty(models.Model):
    _name            = 'estate.property'
    _description     = 'Real Estate Property'
    _inherit         = ['mail.thread', 'mail.activity.mixin']
    _order           = 'ref desc'
    _rec_name        = 'name'

    # ── Identity ─────────────────────────────────────────
    name             = fields.Char("Property Name", required=True, tracking=True, index=True)
    ref              = fields.Char("Property Ref",  readonly=True, copy=False, default='New', index=True)
    property_type_id = fields.Many2one('estate.property.type', string="Category", tracking=True, ondelete='restrict')
    tag_ids          = fields.Many2many('estate.property.tag',  string="Tags")
    amenity_ids      = fields.Many2many('estate.amenity',       string="Amenities")
    active           = fields.Boolean(default=True)
    description      = fields.Html("Description")

    # ── Classification ───────────────────────────────────
    property_type    = fields.Selection([
        ('residential', 'Residential'),
        ('commercial',  'Commercial'),
        ('industrial',  'Industrial'),
        ('land',        'Land'),
    ], string="Type", required=True, default='residential', tracking=True)

    status           = fields.Selection([
        ('available',   'Available'),
        ('leased',      'Leased'),
        ('for_sale',    'For Sale'),
        ('sold',        'Sold'),
        ('maintenance', 'Under Maintenance'),
    ], default='available', tracking=True, index=True)

    furnished        = fields.Selection([
        ('unfurnished', 'Unfurnished'),
        ('semi',        'Semi-Furnished'),
        ('fully',       'Fully Furnished'),
    ], default='unfurnished')

    # ── Ownership ────────────────────────────────────────
    landlord_id      = fields.Many2one('res.partner', string="Landlord/Owner",
                                        required=True, tracking=True, index=True,
                                        domain=[('active','=',True)])
    agent_id         = fields.Many2one('res.users',   string="Listing Agent")
    management_fee   = fields.Float("Management Fee (%)", default=10.0)
    landlord_kra_pin = fields.Char("Landlord KRA PIN")

    # ── Location ─────────────────────────────────────────

    nairobi_area     = fields.Selection([
        # Nairobi Upmarket
        ('karen','Karen'),('runda','Runda'),('muthaiga','Muthaiga'),
        ('lavington','Lavington'),('kilimani','Kilimani'),('kileleshwa','Kileleshwa'),
        ('westlands','Westlands'),('spring_valley','Spring Valley'),
        ('ridgeways','Ridgeways'),('gigiri','Gigiri/UN Area'),
        # Nairobi Middle
        ('south_b','South B'),('south_c','South C'),('ngumo','Ngumo'),
        ('langata','Langata'),('rongai','Rongai'),('ruaka','Ruaka'),
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
    
    street           = fields.Char("Street Address")
    estate           = fields.Char("Estate / Area")
    constituency     = fields.Char("Constituency")
    county           = fields.Selection([
        ('nairobi','Nairobi'),('mombasa','Mombasa'),('kisumu','Kisumu'),
        ('nakuru','Nakuru'),('eldoret','Uasin Gishu'),('nyeri','Nyeri'),
        ('thika','Kiambu'),('machakos','Machakos'),('kisii','Kisii'),
        ('malindi','Kilifi'),('other','Other County'),
    ], string="County", tracking=True)
    postal_code      = fields.Char("Postal Code")
    latitude         = fields.Float("GPS Latitude",  digits=(10, 7))
    longitude        = fields.Float("GPS Longitude", digits=(10, 7))

    # ── Physical ─────────────────────────────────────────
    bedrooms         = fields.Integer("Bedrooms")
    bathrooms        = fields.Integer("Bathrooms")
    size_sqft        = fields.Float("Size (sq ft)")
    plot_size_sqft   = fields.Float("Plot Size (sq ft)")
    floor            = fields.Integer("Floor Number")
    total_floors     = fields.Integer("Total Floors")
    year_built       = fields.Integer("Year Built")
    parking_spaces   = fields.Integer("Parking Spaces")
    garden           = fields.Boolean("Garden / Compound")
    garden_area      = fields.Float("Garden Area (sq ft)")
    has_borehole     = fields.Boolean("Has Borehole")
    has_generator    = fields.Boolean("Has Generator")

    # ── Financials ───────────────────────────────────────
    currency_id      = fields.Many2one('res.currency',
                                        default=lambda s: s.env.ref('base.KES'), required=True)
    monthly_rent     = fields.Monetary("Monthly Rent (KES)", currency_field='currency_id', tracking=True)
    sale_price       = fields.Monetary("Sale Price (KES)",   currency_field='currency_id')
    acquisition_cost = fields.Monetary("Acquisition Cost (KES)", currency_field='currency_id')
    annual_insurance = fields.Monetary("Annual Insurance (KES)", currency_field='currency_id')
    insurance_expiry = fields.Date("Insurance Expiry")

    # ── Computed Financials ──────────────────────────────
    annual_revenue   = fields.Monetary("Annual Gross Revenue",    currency_field='currency_id', compute='_compute_kpis', store=True)
    total_revenue    = fields.Monetary("Total Revenue Collected", currency_field='currency_id', compute='_compute_kpis', store=True)
    total_expenses   = fields.Monetary("Total Expenses",         currency_field='currency_id', compute='_compute_kpis', store=True)
    net_income       = fields.Monetary("Net Operating Income",   currency_field='currency_id', compute='_compute_kpis', store=True)
    gross_yield      = fields.Float("Gross Yield (%)",   compute='_compute_kpis', store=True, digits=(5, 2))
    cap_rate         = fields.Float("Cap Rate (%)",      compute='_compute_kpis', store=True, digits=(5, 2))
    total_arrears    = fields.Monetary("Total Arrears",  currency_field='currency_id', compute='_compute_kpis', store=True)
    landlord_payout  = fields.Monetary("Landlord Net Payout (KES/mo)", currency_field='currency_id', compute='_compute_kpis', store=True)
    occupancy_days   = fields.Integer("Days Occupied YTD", compute='_compute_occupancy', store=True)
    vacancy_days     = fields.Integer("Days Vacant YTD",   compute='_compute_occupancy', store=True)
    vacancy_loss     = fields.Monetary("Vacancy Revenue Loss", currency_field='currency_id', compute='_compute_occupancy', store=True)

    # ── Relations ────────────────────────────────────────
    lease_ids        = fields.One2many('estate.lease',              'property_id', string="Leases")
    offer_ids        = fields.One2many('estate.offer',              'property_id', string="Offers")
    commission_ids   = fields.One2many('estate.commission',         'property_id', string="Commissions")
    inspection_ids   = fields.One2many('estate.inspection',         'property_id', string="Inspections")
    maintenance_ids  = fields.One2many('estate.maintenance.request','property_id', string="Maintenance")
    unit_ids         = fields.One2many('estate.unit',               'property_id', string="Units")
    insurance_ids    = fields.One2many('estate.insurance',          'property_id', string="Insurance")
    valuation_ids    = fields.One2many('estate.property.valuation', 'property_id', string="Valuations")

    # ── Computed Counts ──────────────────────────────────
    lease_count       = fields.Integer(compute='_compute_counts', store=True)
    offer_count       = fields.Integer(compute='_compute_counts', store=True)
    maintenance_count = fields.Integer(compute='_compute_counts', store=True)
    invoice_count = fields.Integer(compute='_compute_counts', store=True)
    total_revenue_ytd = fields.Monetary(compute='_compute_counts', currency_field='currency_id', store=True)

    active_lease_id   = fields.Many2one('estate.lease',   compute='_compute_active_lease', string="Active Lease",     store=True)
    current_tenant_id = fields.Many2one('res.partner',    compute='_compute_active_lease', string="Current Tenant",   store=True)

    # ── Media ────────────────────────────────────────────
    image_1920        = fields.Image("Photo", max_width=1920, max_height=1920)
    image_128         = fields.Image("Thumbnail", related='image_1920', max_width=128, max_height=128, store=True)

    _sql_constraints = [
        ('ref_unique',          'UNIQUE(ref)',          'Property reference must be unique.'),
        ('monthly_rent_pos',    'CHECK(monthly_rent >= 0)',  'Monthly rent cannot be negative.'),
        ('sale_price_pos',      'CHECK(sale_price >= 0)',    'Sale price cannot be negative.'),
    ]

    # ═══ COMPUTE ════════════════════════════════════════

    @api.depends('lease_ids', 'offer_ids', 'maintenance_ids')
    def _compute_counts(self):
        for r in self:
            r.lease_count       = len(r.lease_ids)
            r.offer_count       = len(r.offer_ids)
            r.maintenance_count = len(r.maintenance_ids)
            invs = self.env['account.move'].search([
                ('lease_id.property_id','=',r.id),('move_type','=','out_invoice')])
            r.invoice_count = len(invs)
            r.total_revenue_ytd = sum(
                invs.filtered(lambda i: i.payment_state=='paid').mapped('amount_total'))

    @api.depends('lease_ids.status', 'lease_ids.tenant_id')
    def _compute_active_lease(self):
        for r in self:
            active = r.lease_ids.filtered(lambda l: l.status == 'active')
            r.active_lease_id   = active[:1]
            r.current_tenant_id = active[:1].tenant_id

    @api.depends('monthly_rent', 'sale_price', 'acquisition_cost', 'annual_insurance',
                 'management_fee', 'property_type', 'maintenance_ids.actual_cost',
                 'lease_ids.payment_ids.payment_state', 'lease_ids.payment_ids.amount_total',
                 'lease_ids.payment_ids.amount_residual')
    def _compute_kpis(self):
        for r in self:
            # Revenue from all paid invoices
            invs  = self.env['account.move'].search([
                ('lease_id.property_id', '=', r.id),
                ('move_type', '=', 'out_invoice'),
            ])
            paid  = invs.filtered(lambda i: i.payment_state == 'paid')
            unpaid= invs.filtered(lambda i: i.payment_state not in ('paid','reversed'))

            gross_rev    = sum(paid.mapped('amount_total'))
            arrears      = sum(unpaid.mapped('amount_residual'))
            maint_cost   = sum(r.maintenance_ids.mapped('actual_cost'))
            mgmt_mo      = r.monthly_rent * r.management_fee / 100
            ins_mo       = (r.annual_insurance or 0) / 12
            wht_rate     = 0.10 if r.property_type == 'commercial' else 0.05
            wht_mo       = r.monthly_rent * wht_rate
            annual_gross = r.monthly_rent * 12
            total_exp    = maint_cost + (r.annual_insurance or 0) + mgmt_mo * 12

            r.annual_revenue = annual_gross
            r.total_revenue  = gross_rev
            r.total_expenses = total_exp
            r.net_income     = annual_gross - total_exp
            r.total_arrears  = arrears
            r.gross_yield    = (annual_gross / r.sale_price * 100) if r.sale_price else 0.0
            r.cap_rate       = (r.net_income / r.acquisition_cost * 100) if r.acquisition_cost else 0.0
            r.landlord_payout= r.monthly_rent - mgmt_mo - ins_mo - wht_mo

    @api.depends('lease_ids.date_start', 'lease_ids.date_end', 'lease_ids.status', 'monthly_rent')
    def _compute_occupancy(self):
        from datetime import date
        today      = fields.Date.today()
        year_start = date(today.year, 1, 1)
        for r in self:
            occupied = 0
            for l in r.lease_ids.filtered(lambda x: x.status in ('active','expired','renewed')):
                if not l.date_start or not l.date_end:
                    continue
                start = max(l.date_start, year_start)
                end   = min(l.date_end, today)
                if end > start:
                    occupied += (end - start).days
            year_days        = (today - year_start).days or 1
            r.occupancy_days = occupied
            r.vacancy_days   = max(year_days - occupied, 0)
            r.vacancy_loss   = r.vacancy_days * (r.monthly_rent / 30)

    # ═══ ACTIONS ════════════════════════════════════════

    def _open_related(self, model, field_name, title):
        return {'type':'ir.actions.act_window','name':title,'res_model':model,
                'view_mode':'list,form','domain':[(field_name,'=',self.id)],
                'context':{f'default_{field_name}':self.id}}

    def action_open_leases(self):       self.ensure_one(); return self._open_related('estate.lease','property_id','Leases')
    def action_open_offers(self):       self.ensure_one(); return self._open_related('estate.offer','property_id','Offers')
    def action_open_maintenance(self):  self.ensure_one(); return self._open_related('estate.maintenance.request','property_id','Maintenance')

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


    def action_set_available(self):     self.write({'status':'available'})
    def action_open_invoices(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window", "name": "Invoices",
            "res_model": "account.move", "view_mode": "list,form",
            "domain": [("lease_id.property_id", "=", self.id),
                       ("move_type", "=", "out_invoice")],
        }

    def action_open_mpesa(self):
        self.ensure_one()
        tenant = self.current_tenant_id
        if not tenant:
            return
        return {
            "type": "ir.actions.act_window", "name": "M-Pesa Payments",
            "res_model": "mpesa.transaction", "view_mode": "list,form",
            "domain": [("partner_id", "=", tenant.id)],
        }

    def action_set_for_sale(self):      self.write({'status':'for_sale'})

    # ═══ CRUD ════════════════════════════════════════════

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('ref','New') == 'New':
                v['ref'] = self.env['ir.sequence'].next_by_code('estate.property') or 'New'
        return super().create(vals_list)
