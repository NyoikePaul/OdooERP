"""
KRA Monthly Rental Income (MRI) Tax Return — April 2025 Compliance
Residential: 7.5% flat rate for income < KES 288,000/month
Commercial: Normal income tax rates apply
"""
from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)


class EstateKraReturn(models.Model):
    _name        = 'estate.kra.return'
    _description = 'KRA MRI Tax Return'
    _inherit     = ['mail.thread']
    _order       = 'period_year desc, period_month desc'

    name           = fields.Char("Return Ref", readonly=True, copy=False, default='New')
    landlord_id    = fields.Many2one('res.partner', required=True)
    kra_pin        = fields.Char("Landlord KRA PIN", required=True)
    period_month   = fields.Selection([
        ('01','January'),('02','February'),('03','March'),('04','April'),
        ('05','May'),('06','June'),('07','July'),('08','August'),
        ('09','September'),('10','October'),('11','November'),('12','December'),
    ], required=True)
    period_year    = fields.Integer("Year", required=True, default=lambda s: fields.Date.today().year)
    currency_id    = fields.Many2one('res.currency', default=lambda s: s.env.ref('base.KES'))
    line_ids       = fields.One2many('estate.kra.return.line', 'return_id', string="Income Lines")
    gross_income   = fields.Monetary("Gross Income",    currency_field='currency_id', compute='_compute', store=True)
    wht_collected  = fields.Monetary("WHT Deducted",    currency_field='currency_id', compute='_compute', store=True)
    tax_rate       = fields.Float("Applicable Rate (%)", compute='_compute', store=True)
    tax_due        = fields.Monetary("Tax Due (KES)",   currency_field='currency_id', compute='_compute', store=True)
    status         = fields.Selection([
        ('draft','Draft'),('ready','Ready to File'),('filed','Filed'),('paid','Tax Paid'),
    ], default='draft', tracking=True)
    due_date       = fields.Date("Due Date", compute='_compute_due', store=True)
    filing_date    = fields.Date("Date Filed")
    payment_ref    = fields.Char("KRA Payment Ref")

    @api.depends('period_month','period_year')
    def _compute_due(self):
        from datetime import date
        for r in self:
            if r.period_month and r.period_year:
                m = int(r.period_month) + 1
                y = r.period_year
                if m > 12: m,y = 1, y+1
                r.due_date = date(y,m,20)

    @api.depends('line_ids.gross_rent','line_ids.wht_deducted')
    def _compute(self):
        for r in self:
            gross = sum(r.line_ids.mapped('gross_rent'))
            wht   = sum(r.line_ids.mapped('wht_deducted'))
            r.gross_income  = gross
            r.wht_collected = wht
            rate = 7.5 if gross < 288000 else 30.0
            r.tax_rate = rate
            r.tax_due  = max(gross * rate / 100 - wht, 0)

    def action_populate(self):
        self.ensure_one()
        from datetime import date
        import calendar
        m, y = int(self.period_month), self.period_year
        leases = self.env['estate.lease'].search([
            ('property_id.landlord_id','=',self.landlord_id.id),('status','=','active')])
        invs = self.env['account.move'].search([
            ('lease_id','in',leases.ids),('move_type','=','out_invoice'),
            ('payment_state','=','paid'),
            ('invoice_date','>=',date(y,m,1)),
            ('invoice_date','<=',date(y,m,calendar.monthrange(y,m)[1])),
        ])
        existing = self.line_ids.mapped('property_id')
        for inv in invs:
            prop = inv.lease_id.property_id
            if prop in existing: continue
            self.env['estate.kra.return.line'].create({
                'return_id':self.id,'property_id':prop.id,
                'lease_id':inv.lease_id.id,'gross_rent':inv.amount_total,
                'wht_deducted':inv.lease_id.wht_amount,
            })
        self.write({'status':'ready'})

    def action_mark_filed(self):
        self.write({'status':'filed','filing_date':fields.Date.today()})
    def action_mark_paid(self):
        self.write({'status':'paid'})

    @api.model
    def _cron_kra_reminders(self):
        from datetime import timedelta
        today   = fields.Date.today()
        in_5    = today + timedelta(days=5)
        pending = self.search([('status','in',('draft','ready')),
                                ('due_date','<=',in_5),('due_date','>=',today)])
        for r in pending:
            r.message_post(
                body=_(f"KRA MRI Return due in {(r.due_date - today).days} days. Tax due: KES {r.tax_due:,.0f}."),
                partner_ids=[r.landlord_id.id], subtype_xmlid='mail.mt_note')

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name','New')=='New':
                v['name'] = self.env['ir.sequence'].next_by_code('estate.kra.return') or 'New'
        return super().create(vals_list)


class EstateKraReturnLine(models.Model):
    _name = 'estate.kra.return.line'
    _description = 'KRA Return Income Line'
    return_id    = fields.Many2one('estate.kra.return', ondelete='cascade')
    property_id  = fields.Many2one('estate.property', required=True)
    lease_id     = fields.Many2one('estate.lease')
    currency_id  = fields.Many2one(related='return_id.currency_id')
    gross_rent   = fields.Monetary("Gross Rent",    currency_field='currency_id')
    wht_deducted = fields.Monetary("WHT Deducted",  currency_field='currency_id')
    net_rent     = fields.Monetary("Net Rent",      currency_field='currency_id', compute='_compute', store=True)
    property_type= fields.Selection(related='property_id.property_type', store=True)

    @api.depends('gross_rent','wht_deducted')
    def _compute(self):
        for r in self:
            r.net_rent = r.gross_rent - r.wht_deducted
