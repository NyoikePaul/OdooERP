from odoo import models, fields, api, _


class EstatePropertyValuation(models.Model):
    _name            = 'estate.property.valuation'
    _description     = 'Property Valuation History'
    _order           = 'valuation_date desc'

    property_id      = fields.Many2one('estate.property', required=True, ondelete='cascade')
    valuation_date   = fields.Date("Date", required=True, fault=fields.Date.today)
    valuation_value  = fields.Monetary("Market Value (KES)", currency_field='currency_id', required=True)
    currency_id      = fields.Many2one('res.currency', default=lambda s: s.env.ref('base.KES'))
    method           = fields.Selection([
        ('comparable','Comparable Sales'),('income','Income Approach'),
        ('cost','Cost Approach'),('bank','Bank Valuation'),('dcf','DCF'),
    ], default='comparable', required=True)
    valued_by        = fields.Char("Valued By")
    rrt_ref       = fields.Char("Report Reference")
    notes            = fields.Text()

    _sql_constraints = [('value_positive','CHECK(valuation_value>0)','Valuation must be positive.')]

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for r in records:
            r.property_id.write({'sale_price': r.valuation_value})
            r.property_id.message_post(
                body=_(f"Valuation: KES {r.valuation_value:,.0f} ({r.method}) on {r.valn_date}"))
        return records
