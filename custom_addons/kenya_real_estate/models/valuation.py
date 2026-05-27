from odoo import models, fields, api, _


class EstatePropertyValuation(models.Model):
    _name        = 'estate.property.valuation'
    _description = 'Property Valuation History'
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
    ], default='comparable')
    valued_by        = fields.Char("Valued By (Firm/Person)")
    report_ref       = fields.Char("Valuation Report Ref")
    notes            = fields.Text("Notes")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            # Update property sale price with latest valuation
            rec.property_id.write({'sale_price': rec.valuation_value})
            rec.property_id.message_post(
                body=_(f"Property valued at KES {rec.valuation_value:,.0f} "
                       f"on {rec.valuation_date} by {rec.valued_by or 'Unknown'}.")
            )
        return records
