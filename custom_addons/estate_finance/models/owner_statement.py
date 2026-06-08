"""
Owner/Landlord Statement
Monthly summary of: rent collected, management fee, WHT deducted, expenses, net payout.
"""
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import calendar


class EstateOwnerStatement(models.Model):
    _name        = 'estate.owner.statement'
    _description = "Landlord / Owner Statement"
    _inherit     = ['mail.thread']
    _order       = 'period_year desc, period_month desc'

    name           = fields.Char("Statement Ref", readonly=True, copy=False, default='New')
    landlord_id    = fields.Many2one('res.partner', string="Landlord/Owner", required=True)
    period_month   = fields.Selection([
        ('01','January'),('02','February'),('03','March'),('04','April'),
        ('05','May'),('06','June'),('07','July'),('08','August'),
        ('09','September'),('10','October'),('11','November'),('12','December'),
    ], required=True)
    period_year    = fields.Integer("Year", required=True,
                                    default=lambda s: fields.Date.today().year)
    currency_id    = fields.Many2one('res.currency', default=lambda s: s.env.ref('base.KES'))

    # Income
    gross_rent_collected = fields.Monetary("Gross Rent Collected",   currency_field='currency_id', default=0)
    other_income         = fields.Monetary("Other Income",           currency_field='currency_id', default=0)
    total_income         = fields.Monetary("Total Income",           currency_field='currency_id', compute='_compute', store=True)

    # Deductions
    management_fee_pct   = fields.Float("Management Fee (%)", default=10.0)
    management_fee       = fields.Monetary("Management Fee",         currency_field='currency_id', compute='_compute', store=True)
    wht_deducted         = fields.Monetary("KRA WHT Deducted",       currency_field='currency_id', default=0)
    maintenance_costs    = fields.Monetary("Maintenance Costs",      currency_field='currency_id', default=0)
    insurance_costs      = fields.Monetary("Insurance Premium",      currency_field='currency_id', default=0)
    other_deductions     = fields.Monetary("Other Deductions",       currency_field='currency_id', default=0)
    total_deductions     = fields.Monetary("Total Deductions",       currency_field='currency_id', compute='_compute', store=True)

    # Net
    net_payout           = fields.Monetary("Net Payout to Landlord", currency_field='currency_id', compute='_compute', store=True)

    status = fields.Selection([
        ('draft','Draft'),('sent','Sent to Landlord'),('paid','Payout Made'),
    ], default='draft', tracking=True)

    line_ids = fields.One2many('estate.owner.statement.line', 'statement_id', string="Property Lines")
    notes    = fields.Text()

    @api.depends('gross_rent_collected','other_income','management_fee_pct',
                 'wht_deducted','maintenance_costs','insurance_costs','other_deductions')
    def _compute(self):
        for r in self:
            r.total_income     = r.gross_rent_collected + r.other_income
            r.management_fee   = r.gross_rent_collected * r.management_fee_pct / 100
            r.total_deductions = (r.management_fee + r.wht_deducted +
                                   r.maintenance_costs + r.insurance_costs + r.other_deductions)
            r.net_payout       = r.total_income - r.total_deductions

    def action_populate(self):
        """Auto-populate from invoices/leases for the period."""
        self.ensure_one()
        from datetime import date
        m, y = int(self.period_month), self.period_year
        last_day = calendar.monthrange(y, m)[1]

        properties = self.env['estate.property'].search([
            ('landlord_id','=',self.landlord_id.id)])
        leases = self.env['estate.lease'].search([
            ('property_id','in',properties.ids),('status','=','active')])
        invs = self.env['account.move'].search([
            ('lease_id','in',leases.ids),
            ('move_type','=','out_invoice'),
            ('payment_state','=','paid'),
            ('invoice_date','>=',date(y,m,1)),
            ('invoice_date','<=',date(y,m,last_day)),
        ])

        rent_total = sum(invs.mapped('amount_total'))
        wht_total  = sum(leases.mapped('wht_amount'))
        mgmt       = rent_total * self.management_fee_pct / 100

        self.line_ids.unlink()
        for lease in leases:
            lease_invs = invs.filtered(lambda i: i.lease_id == lease)
            if not lease_invs:
                continue
            self.env['estate.owner.statement.line'].create({
                'statement_id': self.id,
                'property_id':  lease.property_id.id,
                'lease_id':     lease.id,
                'tenant_id':    lease.tenant_id.id,
                'rent_due':     lease.monthly_rent,
                'rent_collected':sum(lease_invs.mapped('amount_total')),
                'wht':          lease.wht_amount,
            })

        self.write({
            'gross_rent_collected': rent_total,
            'wht_deducted':         wht_total,
        })
        self.message_post(body=_(f"Auto-populated: KES {rent_total:,.0f} rent collected "
                                  f"from {len(leases)} leases."))

    def action_send_to_landlord(self):
        self.write({'status':'sent'})
        self.message_post(
            body=_(f"Statement for {self.period_month}/{self.period_year} — "
                   f"Net payout: KES {self.net_payout:,.0f}"),
            partner_ids=[self.landlord_id.id],
            subtype_xmlid='mail.mt_comment')

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name','New') == 'New':
                v['name'] = self.env['ir.sequence'].next_by_code('estate.owner.statement') or 'New'
        return super().create(vals_list)


class EstateOwnerStatementLine(models.Model):
    _name = 'estate.owner.statement.line'
    _description = 'Owner Statement Line'
    statement_id    = fields.Many2one('estate.owner.statement', ondelete='cascade')
    property_id     = fields.Many2one('estate.property')
    lease_id        = fields.Many2one('estate.lease')
    tenant_id       = fields.Many2one('res.partner', string="Tenant")
    currency_id     = fields.Many2one(related='statement_id.currency_id')
    rent_due        = fields.Monetary("Rent Due",      currency_field='currency_id')
    rent_collected  = fields.Monetary("Collected",     currency_field='currency_id')
    wht             = fields.Monetary("WHT Deducted",  currency_field='currency_id')
    net_to_owner    = fields.Monetary("Net to Owner",  currency_field='currency_id',
                                       compute='_compute', store=True)

    @api.depends('rent_collected','wht')
    def _compute(self):
        for r in self:
            r.net_to_owner = r.rent_collected - r.wht
