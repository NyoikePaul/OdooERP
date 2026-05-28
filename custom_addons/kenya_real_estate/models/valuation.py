from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class EstatePropertyValuation(models.Model):
    _name        = 'estate.property.valuation'
    _description = 'Property Valuation Record'
    _order       = 'valuation_date desc'

    property_id      = fields.Many2one('estate.property', string="Property",
                                       required=True, ondelete='cascade')
    valuation_date   = fields.Date("Date", required=True, default=fields.Date.today)
    valuation_value  = fields.Monetary("Market Value (KES)", currency_field='currency_id',
                                       required=True)
    currency_id      = fields.Many2one('res.currency',
                                       default=lambda s: s.env.ref('base.KES'))
    valuation_method = fields.Selection([
        ('comparable', 'Comparable Sales'),
        ('income',     'Income Approach'),
        ('cost',       'Cost Approach'),
        ('bank',       'Bank/Mortgage Valuation'),
        ('dcf',        'Discounted Cash Flow'),
    ], default='comparable', required=True)
    valued_by        = fields.Char("Valued By")
    report_ref       = fields.Char("Report Reference")
    notes            = fields.Text("Notes")

    _sql_constraints = [
        ('value_positive', 'CHECK(valuation_value > 0)', 'Valuation must be positive.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec.property_id.write({'sale_price': rec.valuation_value})
            rec.property_id.message_post(
                body=_(f"Valuation recorded: KES {rec.valuation_value:,.0f} "
                       f"({rec.valuation_method}) on {rec.valuation_date}"
                       + (f" by {rec.valued_by}" if rec.valued_by else ""))
            )
        return records
