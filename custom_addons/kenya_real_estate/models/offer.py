from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta


class EstateOffer(models.Model):
    _name        = 'estate.offer'
    _description = 'Property Offer / Enquiry'
    _inherit     = ['mail.thread', 'mail.activity.mixin']
    _order       = 'create_date desc'

    property_id  = fields.Many2one('estate.property', string="Property",
                                   required=True, ondelete='cascade', tracking=True)
    unit_id      = fields.Many2one('estate.unit', string="Unit",
                                   domain="[('building_id.unit_ids.property_id','=',property_id)]")
    partner_id   = fields.Many2one('res.partner', string="Interested Party",
                                   required=True, tracking=True)
    offer_type   = fields.Selection([
        ('enquiry',  'Enquiry'),
        ('offer',    'Formal Offer'),
        ('viewing',  'Viewing Request'),
    ], default='enquiry', tracking=True)
    offer_amount = fields.Monetary("Offered Amount (KES)", currency_field='currency_id')
    currency_id  = fields.Many2one('res.currency', default=lambda s: s.env.ref('base.KES'))
    listing_price= fields.Monetary(related='property_id.monthly_rent',
                                   string="Listed Rent", readonly=True)
    deadline     = fields.Date("Offer Deadline",
                               default=lambda s: fields.Date.today() + timedelta(days=7))
    status       = fields.Selection([
        ('new',      'New'),
        ('viewing',  'Viewing Scheduled'),
        ('accepted', 'Accepted'),
        ('refused',  'Refused'),
        ('expired',  'Expired'),
    ], default='new', tracking=True)
    notes        = fields.Text("Notes")

    def action_accept(self):
        self.write({'status': 'accepted'})
        # Refuse all other offers on same property
        others = self.search([
            ('property_id', '=', self.property_id.id),
            ('id', '!=', self.id),
            ('status', 'in', ('new', 'viewing')),
        ])
        others.write({'status': 'refused'})
        self.message_post(body=_("Offer accepted ✅"))

    def action_refuse(self):
        self.write({'status': 'refused'})
        self.message_post(body=_("Offer refused ❌"))

    def action_schedule_viewing(self):
        self.write({'status': 'viewing'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mail.activity',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_res_model': 'estate.offer',
                'default_res_id': self.id,
                'default_activity_type_id': self.env.ref('mail.mail_activity_data_meeting').id,
                'default_summary': f"Property Viewing — {self.property_id.name}",
            }
        }
