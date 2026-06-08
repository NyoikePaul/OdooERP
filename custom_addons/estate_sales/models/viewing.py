"""
Property Viewing Scheduler
Prevents double-booking: same property cannot have two viewings at same time.
"""
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import timedelta


class EstateViewing(models.Model):
    _name        = 'estate.viewing'
    _description = 'Property Viewing'
    _inherit     = ['mail.thread', 'mail.activity.mixin']
    _order       = 'viewing_date desc'

    name         = fields.Char("Viewing Ref", readonly=True, copy=False, default='New')
    property_id  = fields.Many2one('estate.property', required=True, tracking=True)
    unit_id      = fields.Many2one('estate.unit', string="Specific Unit")
    client_id    = fields.Many2one('res.partner', string="Client/Prospect", required=True, tracking=True)
    agent_id     = fields.Many2one('res.users', string="Showing Agent")
    viewing_date = fields.Datetime("Viewing Date & Time", required=True, tracking=True)
    duration     = fields.Float("Duration (hrs)", default=0.5)
    end_time     = fields.Datetime(compute='_compute_end', store=True, string="End Time")

    source       = fields.Selection([
        ('website','Website'),('walk_in','Walk-in'),
        ('facebook','Facebook'),('referral','Referral'),
        ('phone','Phone Enquiry'),('email','Email'),
    ], default='phone')

    status = fields.Selection([
        ('scheduled','Scheduled'),('confirmed','Confirmed'),
        ('completed','Completed'),('no_show','No Show'),('cancelled','Cancelled'),
    ], default='scheduled', tracking=True)

    client_rating = fields.Selection([
        ('hot','🔥 Hot — Very Interested'),
        ('warm','👍 Warm — Considering'),
        ('cold','❄️ Cold — Just Looking'),
    ], string="Client Interest")

    next_step    = fields.Selection([
        ('second_viewing','Second Viewing'),
        ('offer','Make Offer'),
        ('follow_up','Follow Up'),
        ('not_interested','Not Interested'),
    ], string="Next Step")

    feedback     = fields.Text("Feedback / Notes")
    sale_id      = fields.Many2one('estate.property.sale', string="Linked Sale")

    _sql_constraints = [('name_unique','UNIQUE(name)','Viewing ref must be unique.')]

    @api.depends('viewing_date','duration')
    def _compute_end(self):
        for r in self:
            if r.viewing_date and r.duration:
                r.end_time = r.viewing_date + timedelta(hours=r.duration)

    @api.constrains('property_id','viewing_date','duration','status')
    def _check_no_double_booking(self):
        for r in self:
            if r.status == 'cancelled':
                continue
            others = self.search([
                ('property_id','=',r.property_id.id),
                ('status','not in',('cancelled','no_show')),
                ('id','!=',r.id),
                ('viewing_date','<',r.end_time),
                ('end_time','>',r.viewing_date),
            ])
            if others:
                raise ValidationError(
                    _(f"Double booking! {r.property_id.name} already has a viewing at "
                      f"{others[:1].viewing_date} — {others[:1].end_time}. "
                      f"Ref: {others[:1].name}"))

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name','New') == 'New':
                v['name'] = self.env['ir.sequence'].next_by_code('estate.viewing') or 'New'
        return super().create(vals_list)

    def action_confirm(self):
        self.write({'status':'confirmed'})
        self.message_post(
            body=_(f"Viewing confirmed: {self.property_id.name} on {self.viewing_date}"),
            partner_ids=[self.client_id.id])

    def action_complete(self):
        self.write({'status':'completed'})

    def action_no_show(self):
        self.write({'status':'no_show'})

    def action_cancel(self):
        self.write({'status':'cancelled'})

    def action_create_sale(self):
        """Convert viewing to a sale transaction."""
        self.ensure_one()
        sale = self.env['estate.property.sale'].create({
            'property_id': self.property_id.id,
            'buyer_id':    self.client_id.id,
            'agent_id':    self.agent_id.id,
            'source':      self.source,
            'status':      'offer',
            'date_viewing':self.viewing_date.date() if self.viewing_date else False,
        })
        self.write({'sale_id': sale.id})
        return {'type':'ir.actions.act_window','res_model':'estate.property.sale',
                'res_id':sale.id,'view_mode':'form'}
