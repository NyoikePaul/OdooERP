from odoo import models, fields, api


class EstatePaymentAging(models.Model):
    _name        = 'estate.payment.aging'
    _description = 'Tenant Payment Aging'
    _auto        = False
    _order       = 'total_outstanding desc'

    tenant_id          = fields.Many2one('res.partner',    string="Tenant",   readonly=True)
    property_id        = fields.Many2one('estate.property',string="Property", readonly=True)
    lease_id           = fields.Many2one('estate.lease',   string="Lease",    readonly=True)
    currency_id        = fields.Many2one('res.currency',               readonly=True)
    current            = fields.Float("Current",      readonly=True)
    days_1_30          = fields.Float("1-30 Days",    readonly=True)
    days_31_60         = fields.Float("31-60 Days",   readonly=True)
    days_61_90         = fields.Float("61-90 Days",   readonly=True)
    days_90_plus       = fields.Float("90+ Days",     readonly=True)
    total_outstanding  = fields.Float("Total",        readonly=True)

    def init(self):
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW estate_payment_aging AS
            SELECT
                ROW_NUMBER() OVER () AS id,
                am.partner_id       AS tenant_id,
                NULL::integer       AS property_id,
                NULL::integer       AS lease_id,
                am.currency_id      AS currency_id,
                SUM(CASE WHEN (CURRENT_DATE - am.invoice_date_due) <= 0
                    THEN am.amount_residual ELSE 0 END)              AS current,
                SUM(CASE WHEN (CURRENT_DATE - am.invoice_date_due) BETWEEN 1  AND 30
                    THEN am.amount_residual ELSE 0 END)              AS days_1_30,
                SUM(CASE WHEN (CURRENT_DATE - am.invoice_date_due) BETWEEN 31 AND 60
                    THEN am.amount_residual ELSE 0 END)              AS days_31_60,
                SUM(CASE WHEN (CURRENT_DATE - am.invoice_date_due) BETWEEN 61 AND 90
                    THEN am.amount_residual ELSE 0 END)              AS days_61_90,
                SUM(CASE WHEN (CURRENT_DATE - am.invoice_date_due) > 90
                    THEN am.amount_residual ELSE 0 END)              AS days_90_plus,
                SUM(am.amount_residual)                              AS total_outstanding
            FROM account_move am
            WHERE am.move_type = 'out_invoice'
              AND am.state = 'posted'
              AND am.payment_state NOT IN ('paid', 'reversed')
              AND am.amount_residual > 0
            GROUP BY am.partner_id, am.currency_id
            HAVING SUM(am.amount_residual) > 0
        """)
