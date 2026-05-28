"""
KRA Monthly Rental Income (MRI) Tax Return Preparation
New KRA system introduced April 2025 — Section 6A Income Tax Act.

Residential rental income tax (for individuals):
- Monthly income < KES 288,000: 7.5% flat rate (no deductions)
- Monthly income >= KES 288,000: Normal IT rates apply

Commercial rent: subject to normal income tax + WHT at source
"""
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class EstateKraReturn(models.Model):
    _name        = 'estate.kra.return'
    _description = 'KRA Monthly Rental Income Return'
    _inherit     = ['mail.thread']
    _order       = 'period_year desc, period_month desc'

    name           = fields.Char("Return Ref", readonly=True, default='New')
    landlord_id    = fields.Many2one('res.partner', string="Landlord", required=True)
    kra_pin        = fields.Char("Landlord KRA PIN", required=True)
    period_month   = fields.Selection([
        ('01','January'),('02','February'),('03','March'),
        ('04','April'),('05','May'),('06','June'),
        ('07','July'),('08','August'),('09','September'),
        ('10','October'),('11','November'),('12','December'),
    ], required=True)
    period_year    = fields.Integer("Year", required=True,
                                    default=lambda s: fields.Date.today().year)
    currency_id    = fields.Many2one('res.currency',
                                     default=lambda s: s.env.ref('base.KES'))

    line_ids       = fields.One2many('estate.kra.return.line', 'return_id',
                                     string="Rental Income Lines")

    gross_income   = fields.Monetary("Gross Rental Income (KES)",
                                     currency_field='currency_id',
                                     compute='_compute_totals', store=True)
    wht_collected  = fields.Monetary("WHT Already Deducted (KES)",
                                     currency_field='currency_id',
                                     compute='_compute_totals', store=True)
    taxable_income = fields.Monetary("Taxable Income (KES)",
                                     currency_field='currency_id',
                                     compute='_compute_totals', store=True)
    tax_due        = fields.Monetary("Tax Due (KES)",
                                     currency_field='currency_id',
                                     compute='_compute_totals', store=True)
    tax_rate       = fields.Float("Applicable Rate (%)",
                                  compute='_compute_totals', store=True)

    status = fields.Selection([
        ('draft',    'Draft'),
        ('ready',    'Ready to File'),
        ('filed',    'Filed'),
        ('paid',     'Tax Paid'),
    ], default='draft', tracking=True)
    filing_date    = fields.Date("Date Filed")
    payment_ref    = fields.Char("KRA Payment Reference")
    due_date       = fields.Date("Due Date", compute='_compute_due_date', store=True)

    @api.depends('period_month', 'period_year')
    def _compute_due_date(self):
        """KRA MRI due by 20th of following month."""
        for rec in self:
            if rec.period_month and rec.period_year:
                import calendar
                month = int(rec.period_month) + 1
                year  = rec.period_year
                if month > 12:
                    month = 1
                    year += 1
                from datetime import date
                rec.due_date = date(year, month, 20)

    @api.depends('line_ids.gross_rent', 'line_ids.wht_deducted')
    def _compute_totals(self):
        for rec in self:
            gross = sum(rec.line_ids.mapped('gross_rent'))
            wht   = sum(rec.line_ids.mapped('wht_deducted'))
            rec.gross_income  = gross
            rec.wht_collected = wht
            # Residential MRI: 7.5% flat if < 288,000/mo
            if gross < 288000:
                rate = 7.5
                tax  = gross * 0.075
            else:
                # Progressive normal IT rates (simplified)
                rate = 30.0
                tax  = gross * 0.30
            rec.tax_rate       = rate
            rec.taxable_income = gross
            rec.tax_due        = max(tax - wht, 0)

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name', 'New') == 'New':
                v['name'] = self.env['ir.sequence'].next_by_code('estate.kra.return') or 'New'
        return super().create(vals_list)

    def action_populate_from_invoices(self):
        """Auto-populate from paid invoices for the period."""
        self.ensure_one()
        from datetime import date
        month = int(self.period_month)
        year  = self.period_year
        # Find all paid rent invoices for this landlord in this period
        leases = self.env['estate.lease'].search([
            ('property_id.landlord_id', '=', self.landlord_id.id),
            ('status', '=', 'active'),
        ])
        invoices = self.env['account.move'].search([
            ('lease_id', 'in', leases.ids),
            ('move_type', '=', 'out_invoice'),
            ('payment_state', '=', 'paid'),
            ('invoice_date', '>=', date(year, month, 1)),
            ('invoice_date', '<=', date(year, month,
             __import__('calendar').monthrange(year, month)[1])),
        ])
        existing_props = self.line_ids.mapped('property_id')
        for inv in invoices:
            prop = inv.lease_id.property_id
            if prop in existing_props:
                continue
            self.env['estate.kra.return.line'].create({
                'return_id':   self.id,
                'property_id': prop.id,
                'lease_id':    inv.lease_id.id,
                'gross_rent':  inv.amount_total,
                'wht_deducted': inv.lease_id.wht_amount,
            })
        self.write({'status': 'ready'})

    def action_mark_filed(self):
        self.write({'status': 'filed', 'filing_date': fields.Date.today()})
        self.message_post(body=_(f"KRA MRI return filed on {fields.Date.today()}."))

    def action_mark_paid(self):
        self.write({'status': 'paid'})

    @api.model
    def _cron_kra_filing_reminders(self):
        """Remind landlords of upcoming KRA filing due dates."""
        from datetime import timedelta
        today   = fields.Date.today()
        in_5    = today + timedelta(days=5)
        pending = self.search([
            ('status', 'in', ('draft', 'ready')),
            ('due_date', '<=', in_5),
            ('due_date', '>=', today),
        ])
        for ret in pending:
            ret.message_post(
                body=_(f"KRA MRI Return due in {(ret.due_date - today).days} days "
                       f"({ret.due_date}). Tax due: KES {ret.tax_due:,.0f}."),
                partner_ids=[ret.landlord_id.id],
                subtype_xmlid='mail.mt_note',
            )


class EstateKraReturnLine(models.Model):
    _name        = 'estate.kra.return.line'
    _description = 'KRA Return — Rental Income Line'

    return_id    = fields.Many2one('estate.kra.return', ondelete='cascade')
    property_id  = fields.Many2one('estate.property', required=True)
    lease_id     = fields.Many2one('estate.lease')
    currency_id  = fields.Many2one(related='return_id.currency_id')
    gross_rent   = fields.Monetary("Gross Rent (KES)", currency_field='currency_id')
    wht_deducted = fields.Monetary("WHT Deducted (KES)", currency_field='currency_id')
    net_rent     = fields.Monetary("Net Rent (KES)", currency_field='currency_id',
                                   compute='_compute_net', store=True)
    property_type = fields.Selection(related='property_id.property_type', store=True)

    @api.depends('gross_rent', 'wht_deducted')
    def _compute_net(self):
        for rec in self:
            rec.net_rent = rec.gross_rent - rec.wht_deducted
