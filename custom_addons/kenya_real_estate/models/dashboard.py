"""
Kenya Real Estate Dashboard
Single-record model that computes all KPIs live from the database.
"""
from odoo import models, fields, api
from datetime import date
from dateutil.relativedelta import relativedelta


class EstateDashboard(models.Model):
    _name        = 'estate.dashboard'
    _description = 'Real Estate Dashboard'
    _auto        = False  # no DB table

    # ── Portfolio KPIs ────────────────────────────
    total_properties     = fields.Integer("Total Properties")
    available_properties = fields.Integer("Available")
    leased_properties    = fields.Integer("Leased")
    for_sale_properties  = fields.Integer("For Sale")
    maintenance_props    = fields.Integer("Under Maintenance")
    occupancy_rate       = fields.Float("Occupancy Rate %")

    # ── Unit KPIs ─────────────────────────────────
    total_units          = fields.Integer("Total Units")
    occupied_units       = fields.Integer("Occupied Units")
    vacant_units         = fields.Integer("Vacant Units")
    unit_occupancy_rate  = fields.Float("Unit Occupancy %")

    # ── Revenue KPIs ──────────────────────────────
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

    # ── Lease KPIs ────────────────────────────────
    active_leases        = fields.Integer("Active Leases")
    expiring_30d         = fields.Integer("Expiring in 30 Days")
    expiring_60d         = fields.Integer("Expiring in 60 Days")
    leases_in_arrears    = fields.Integer("Leases in Arrears")

    # ── Maintenance KPIs ──────────────────────────
    maintenance_open     = fields.Integer("Open Requests")
    maintenance_critical = fields.Integer("Critical/High")
    maintenance_in_prog  = fields.Integer("In Progress")
    avg_resolution_days  = fields.Float("Avg Resolution Days")

    # ── Sales KPIs ────────────────────────────────
    active_viewings      = fields.Integer("Viewings Scheduled")
    active_offers        = fields.Integer("Active Offers")
    sales_this_month     = fields.Integer("Sales This Month")
    commission_ytd       = fields.Float("Commission YTD (KES)")

    # ── Screening KPIs ────────────────────────────
    pending_applications = fields.Integer("Pending Applications")

    def _get_kpis(self):
        """Compute all KPIs and return as dict."""
        env = self.env
        today = date.today()
        month_start = today.replace(day=1)
        year_start  = today.replace(month=1, day=1)

        # Properties
        props = env['estate.property'].search([])
        available = props.filtered(lambda p: p.status == 'available')
        leased    = props.filtered(lambda p: p.status == 'leased')
        for_sale  = props.filtered(lambda p: p.status == 'for_sale')
        maint     = props.filtered(lambda p: p.status == 'maintenance')
        total_p   = len(props)
        occ_rate  = (len(leased) / total_p * 100) if total_p else 0.0

        # Units
        units     = env['estate.unit'].search([])
        occupied  = units.filtered(lambda u: u.status == 'leased')
        vacant    = units.filtered(lambda u: u.status == 'vacant')
        total_u   = len(units)
        unit_occ  = (len(occupied) / total_u * 100) if total_u else 0.0

        # Revenue
        active_l  = env['estate.lease'].search([('status','=','active')])
        rent_roll = sum(active_l.mapped('monthly_rent'))

        invs_month = env['account.move'].search([
            ('move_type','=','out_invoice'),
            ('payment_state','=','paid'),
            ('invoice_date','>=',month_start),
            ('invoice_date','<=',today),
        ])
        collected = sum(invs_month.mapped('amount_total'))

        invs_ytd = env['account.move'].search([
            ('move_type','=','out_invoice'),
            ('payment_state','=','paid'),
            ('invoice_date','>=',year_start),
        ])
        ytd_rev = sum(invs_ytd.mapped('amount_total'))

        # Arrears by aging bucket
        unpaid = env['account.move'].search([
            ('move_type','=','out_invoice'),
            ('state','=','posted'),
            ('payment_state','not in',('paid','reversed')),
            ('amount_residual','>',0),
        ])
        arr_30=arr_60=arr_90=arr_90p=0
        for inv in unpaid:
            if not inv.invoice_date_due:
                continue
            days = (today - inv.invoice_date_due).days
            amt  = inv.amount_residual
            if days <= 0:    pass
            elif days <= 30: arr_30  += amt
            elif days <= 60: arr_60  += amt
            elif days <= 90: arr_90  += amt
            else:            arr_90p += amt
        total_arrears = arr_30 + arr_60 + arr_90 + arr_90p
        coll_rate = (collected / (collected + total_arrears) * 100) if (collected + total_arrears) else 100.0

        # Lease expiry
        exp30 = active_l.filtered(lambda l: l.days_to_expiry <= 30  and l.days_to_expiry >= 0)
        exp60 = active_l.filtered(lambda l: l.days_to_expiry <= 60  and l.days_to_expiry >= 0)
        arr_l = active_l.filtered(lambda l: l.months_arrears > 0)

        # Maintenance
        mreqs = env['estate.maintenance.request'].search([('status','not in',('done','cancelled'))])
        crit  = mreqs.filtered(lambda m: m.priority in ('2','3'))
        inprog= mreqs.filtered(lambda m: m.status == 'in_progress')

        done_m = env['estate.maintenance.request'].search([
            ('status','=','done'),
            ('date_reported','>=',year_start.strftime('%Y-%m-%d')),
            ('date_resolved','!=',False),
        ])
        if done_m:
            avg_days = sum(
                (m.date_resolved - m.date_reported).days
                for m in done_m if m.date_resolved and m.date_reported
            ) / len(done_m)
        else:
            avg_days = 0

        # Sales
        viewings = env['estate.viewing'].search(
            [('status','=','scheduled')]) if 'estate.viewing' in self.env else []
        offers   = env['estate.offer'].search([('status','=','new')])
        sales_mo = env['estate.property.sale'].search([
            ('status','=','sold'),
            ('date_completion','>=',month_start),
        ]) if 'estate.property.sale' in self.env else []
        comm_ytd = env['estate.commission'].search([
            ('status','=','paid'),
        ])
        comm_total = sum(comm_ytd.mapped('commission'))

        # Screening
        apps = env['estate.tenant.screening'].search([('status','in',('new','screening'))])

        return {
            'total_properties':     total_p,
            'available_properties': len(available),
            'leased_properties':    len(leased),
            'for_sale_properties':  len(for_sale),
            'maintenance_props':    len(maint),
            'occupancy_rate':       round(occ_rate, 1),
            'total_units':          total_u,
            'occupied_units':       len(occupied),
            'vacant_units':         len(vacant),
            'unit_occupancy_rate':  round(unit_occ, 1),
            'monthly_rent_roll':    rent_roll,
            'collected_this_month': collected,
            'outstanding_arrears':  total_arrears,
            'arrears_30d':          arr_30,
            'arrears_60d':          arr_60,
            'arrears_90d':          arr_90,
            'arrears_90plus':       arr_90p,
            'collection_rate':      round(coll_rate, 1),
            'annual_revenue_ytd':   ytd_rev,
            'active_leases':        len(active_l),
            'expiring_30d':         len(exp30),
            'expiring_60d':         len(exp60),
            'leases_in_arrears':    len(arr_l),
            'maintenance_open':     len(mreqs),
            'maintenance_critical': len(crit),
            'maintenance_in_prog':  len(inprog),
            'avg_resolution_days':  round(avg_days, 1),
            'active_viewings':      len(viewings),
            'active_offers':        len(offers),
            'sales_this_month':     len(sales_mo),
            'commission_ytd':       comm_total,
            'pending_applications': len(apps),
        }

    @api.model
    def get_dashboard_data(self):
        return self._get_kpis()
