from odoo import models, fields, api, _
from datetime import timedelta


class Estatfer(models.Model):
    _name        = 'estate.offer'
    _description = 'Property Offer / Enquiry'
    _inherit     = ['mail.thread', 'mail.activity.mixin']
    _order       = 'create_date desc'

    property_id  = fields.Many2one('estate.property', required=True, ondelete='cascade', tracking=True)
    unit_id      = fields.Many2one('estate.unit', string="Unit")
    partner_id   = fields.Many2one('res.partner', string="Prospect", required=True, tracking=True)
    offer_type   = fields.Selection([('enquiry',Enquiry'),('offer','Formal Offer'),('viewing','Viewing')], default='enquiry')
    currency_id  = fields.Many2one('res.currency', default=lambda s: s.env.ref('base.KES'))
    offer_amount = fields.Monetary("Offered Amount", currency_field='currency_id')
    listing_price= fields.Monetary(related='property_id.monthly_rent', string="Listed Rent", readonly=True)
    deadline     = fields.Date("Deadline", default=lambda s: fields.Date.today() + timedelta(days=7))
    status       = fields.Selection([('new','New'iewing','Viewing Scheduled'),
                                      ('accepted','Accepted'),('refused','Refused')], default='new', tracking=True)
    notes        = fields.Text("Notes")

    def action_accept(self):
        self.write({'status':'accepted'})
        others = self.search([('property_id','=',self.property_id.id),
                               ('id','!=',self.id),('status','in',('new','viewing'))])
        others.write({'status':'refused'})
        self.message_post(body=_("Offer accepted ✅"   def action_refuse(self):
        self.write({'status':'refused'})
        self.message_post(body=_("Offer refused."))
