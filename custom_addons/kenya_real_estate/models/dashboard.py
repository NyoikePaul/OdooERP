"""
Kenya Real Estate Dashboard — optimised for production.
Uses search_count(), read_group(), and a single SQL query for arrears aging.
No full recordset loads except where field computation requires it.
"""
from odoo import models, fields, api
from datetime import date


class EstateDashboard(models.Model):
    _name        = 'estate.dashboard'
    _description = 'Real Estate Dashboard'
    _auto        = False  # no DB table

    # Portfolio KPIs
    total_properties     = fields.Integer("Total Properties")
    available_properties = fields.Integer("Available")
    leased_properties    = fields.Integer("Leased")
    for_sale_properties  = fields.Integer("For Sale")
    maintenance_props    = fields.Integer("Under Maintenance")
    occupancy_rate       = fields.Float("Occupancy Rate %")

    # Unit KPIs
    total_units         = fields.Integer("Total Units")
    occupied_units      = fields.Integer("Occupied Units")
    vacant_units        = fields.Integer("Vacant Units")
    unit_occupancy_rate = fields.Float("Unit Occupancy %")

    # Revenue KPIs
    currency_id          = fields.Many2one('res.currency',
                                           default=lambda s: s.env.ref('base.KES'))
    monthly_rent_roll    = fields.Float("Monthly Rent Roll (KES)")
    collected_this_month = fields.Float("Collected This Month (KES)")
    outstanding_arrears  = fields.Float("Total Arrears (KES)")
    arrears_30d          = fields.Float("1-30 Day Arrears")
    arrears_60d          = fields.Float("31-60 Day Arrears")
    arrears_90d          = fields.Float("61-90 Day Arrears")
    arrears_90plus       = fields.Float("90+ Day Arrears")
    collection_rate      = fields.Float("Collection Rate %")
    annual_revenue_ytd   = fields.Float("Revenue YTD (KES)")

    # Lease KPIs
    active_leases     = fields.Integer("Active Leases")
    expiring_30d      = fields.Integer("Expiring in 30 Days")
    expiring_60d      = fields.Integer("Expiring in 60 Days")
    leases_in_arrears = fields.Integer("Leases in Arrears")

    # Maintenance KPIs
    maintenance_open     = fields.Integer("Open Requests")
    maintenance_critical = fields.Integer("Critical/High")
    maintenance_in_prog  = fields.Integer("In Progress")
    avg_resolution_days  = fields.Float("Avg Resolution Days")

    # Sales KPIs
    active_viewings  = fields.Integer("Viewings Scheduled")
    active_offers    = fields.Integer("Active Offers")
    sales_this_month = fields.Integer("Sales This Month")
    commission_ytd   = fields.Float("Commission YTD (KES)")

    # Screening KPIs
    pending_applications = fields.Integer("Pending Applications")

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _count(self, model, domain):
        """search_count — never loads records into memory."""
        return self.env[model].search_count(domain)

    def _sum(self, model, field, domain):
        """read_group aggregate sum — single SQL GROUP BY query."""
        if model not in self.env:
            return 0.0
        groups = self.env[model].read_group(domain, [field], [])
        return groups[0][field] or 0.0 if groups else 0.0

    def _arrears_aging(self, today):
        """
        Single SQL query for arrears aging buckets.
        Far faster than loading all unpaid invoices into Python.
        """
        self.env.cr.execute("""
            SELECT
                SUM(CASE WHEN (%(today)s - invoice_date_due) BETWEEN 1  AND 30  THEN amount_residual ELSE 0 END) AS b30,
                SUM(CASE WHEN (%(today)s - invoice_date_due) BETWEEN 31 AND 60  THEN amount_residual ELSE 0 END) AS b60,
                SUM(CASE WHEN (%(today)s - invoice_date_due) BETWEEN 61 AND 90  THEN amount_residual ELSE 0 END) AS b90,
                SUM(CASE WHEN (%(today)s - invoice_date_due) > 90               THEN amount_residual ELSE 0 END) AS b90p
            FROM account_move
            WHERE move_type       = 'out_invoice'
              AND state           = 'posted'
              AND payment_state   NOT IN ('paid', 'reversed')
              AND amount_residual > 0
              AND invoice_date_due IS NOT NULL
        """, {'today': today})
        row = self.env.cr.fetchone()
        return (
            float(row[0] or 0),
            float(row[1] or 0),
            float(row[2] or 0),
            float(row[3] or 0),
        )

    def _avg_resolution_days(self, year_start):
        """Single SQL AVG — no Python loop over done requests."""
        self.env.cr.execute("""
            SELECT AVG(date_resolved - date_reported)
            FROM estate_maintenance_request
            WHERE status        = 'done'
              AND date_reported >= %(year_start)s
              AND date_resolved IS NOT NULL
              AND date_reported IS NOT NULL
        """, {'year_start': year_start})
        result = self.env.cr.fetchone()[0]
        return round(float(result.days) if result else 0.0, 1)

    # ------------------------------------------------------------------ #
    #  Main KPI method                                                     #
    # ------------------------------------------------------------------ #

    def _get_kpis(self):
        today      = date.today()
        month_start = today.replace(day=1)
        year_start  = today.replace(month=1, day=1)

        # ── Properties (5 counts, zero records loaded) ──────────────────
        total_p    = self._count('estate.property', [])
        leased_p   = self._count('estate.property', [('status', '=', 'leased')])
        avail_p    = self._count('estate.property', [('status', '=', 'available')])
        sale_p     = self._count('estate.property', [('status', '=', 'for_sale')])
        maint_p    = self._count('estate.property', [('status', '=', 'maintenance')])
        occ_rate   = round(leased_p / total_p * 100, 1) if total_p else 0.0

        # ── Units ────────────────────────────────────────────────────────
        total_u    = self._count('estate.unit', [])
        occupied_u = self._count('estate.unit', [('status', '=', 'leased')])
        vacant_u   = self._count('estate.unit', [('status', '=', 'vacant')])
        unit_occ   = round(occupied_u / total_u * 100, 1) if total_u else 0.0

        # ── Revenue (read_group aggregates) ──────────────────────────────
        rent_roll = self._sum('estate.lease', 'monthly_rent', [('status', '=', 'active')])
        collected = self._sum('account.move', 'amount_total', [
            ('move_type',     '=',  'out_invoice'),
            ('payment_state', '=',  'paid'),
            ('invoice_date',  '>=', month_start),
            ('invoice_date',  '<=', today),
        ])
        ytd_rev = self._sum('account.move', 'amount_total', [
            ('move_type',     '=',  'out_invoice'),
            ('payment_state', '=',  'paid'),
            ('invoice_date',  '>=', year_start),
        ])

        # ── Arrears aging (single SQL query) ─────────────────────────────
        arr_30, arr_60, arr_90, arr_90p = self._arrears_aging(today)
        total_arrears = arr_30 + arr_60 + arr_90 + arr_90p
        coll_rate = round(
            collected / (collected + total_arrears) * 100, 1
        ) if (collected + total_arrears) else 100.0

        # ── Leases ───────────────────────────────────────────────────────
        active_l   = self._count('estate.lease', [('status', '=', 'active')])
        exp_30     = self._count('estate.lease', [
            ('status',        '=',  'active'),
            ('days_to_expiry', '>=', 0),
            ('days_to_expiry', '<=', 30),
        ])
        exp_60     = self._count('estate.lease', [
            ('status',        '=',  'active'),
            ('days_to_expiry', '>=', 0),
            ('days_to_expiry', '<=', 60),
        ])
        arr_leases = self._count('estate.lease', [
            ('status',        '=',  'active'),
            ('months_arrears', '>',  0),
        ])

        # ── Maintenance ──────────────────────────────────────────────────
        maint_open = self._count('estate.maintenance.request',
                                  [('status', 'not in', ('done', 'cancelled'))])
        maint_crit = self._count('estate.maintenance.request', [
            ('status',   'not in', ('done', 'cancelled')),
            ('priority', 'in',     ('2', '3')),
        ])
        maint_prog = self._count('estate.maintenance.request',
                                  [('status', '=', 'in_progress')])
        avg_days   = self._avg_resolution_days(year_start)

        # ── Sales ────────────────────────────────────────────────────────
        viewings  = self._count('estate.viewing',
                                 [('status', '=', 'scheduled')])                     if 'estate.viewing' in self.env else 0
        offers    = self._count('estate.offer', [('status', '=', 'new')])
        sales_mo  = self._count('estate.property.sale', [
            ('status',          '=',  'sold'),
            ('date_completion', '>=', month_start),
        ]) if 'estate.property.sale' in self.env else 0
        comm_ytd  = self._sum('estate.commission', 'commission',
                               [('status', '=', 'paid')])

        # ── Screening ────────────────────────────────────────────────────
        pending_apps = self._count('estate.tenant.screening',
                                    [('status', 'in', ('new', 'screening'))])

        return {
            'total_properties':     total_p,
            'available_properties': avail_p,
            'leased_properties':    leased_p,
            'for_sale_properties':  sale_p,
            'maintenance_props':    maint_p,
            'occupancy_rate':       occ_rate,
            'total_units':          total_u,
            'occupied_units':       occupied_u,
            'vacant_units':         vacant_u,
            'unit_occupancy_rate':  unit_occ,
            'monthly_rent_roll':    rent_roll,
            'collected_this_month': collected,
            'outstanding_arrears':  total_arrears,
            'arrears_30d':          arr_30,
            'arrears_60d':          arr_60,
            'arrears_90d':          arr_90,
            'arrears_90plus':       arr_90p,
            'collection_rate':      coll_rate,
            'annual_revenue_ytd':   ytd_rev,
            'active_leases':        active_l,
            'expiring_30d':         exp_30,
            'expiring_60d':         exp_60,
            'leases_in_arrears':    arr_leases,
            'maintenance_open':     maint_open,
            'maintenance_critical': maint_crit,
            'maintenance_in_prog':  maint_prog,
            'avg_resolution_days':  avg_days,
            'active_viewings':      viewings,
            'active_offers':        offers,
            'sales_this_month':     sales_mo,
            'commission_ytd':       comm_ytd,
            'pending_applications': pending_apps,
        }

    @api.model
    def get_dashboard_data(self):
        return self._get_kpis()
