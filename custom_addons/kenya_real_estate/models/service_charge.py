from odoo import models, fields, api, _
from odoo.exceptions import UserError


class EstateServiceCharge(models.Model):
    _name        = 'estate.service.charge'
    _description = 'Service Charge Bill'
    _inherit     = ['mail.thread']
    _order       = 'period_date desc'

    name          = fields.Char("Ref", readonly=True, copy=False, default='New')
    building_id   = fields.Many2one('estate.building', required=True)
    period_date   = fields.Date("Period", required=True, default=fields.Date.today)
    currency_id   = fields.Many2one('res.currency', default=lambda s: s.env.ref('base.KES'))
    apportionment = fields.Selection([
        ('equal','Equal Split'),('sqft','By Unit Size'),('bedrooms','By Bedrooms'),
    ], default='equal', required=True)
    line_ids      = fields.One2many('estate.service.charge.line', 'charge_id', string="Expenses")
    total_amount  = fields.Monetary("Total (KES)", currency_field='currency_id',
                                     compute='_compute_total', store=True)
    status        = fields.Selection([('draft','Draft'),('invoiced','Invoiced')], default='draft', tracking=True)

    @api.depends('line_ids.amount')
    def _compute_total(self):
        for r in self:
            r.total_amount = sum(r.line_ids.mapped('amount'))

    def action_generate_invoices(self):
        self.ensure_one()
        if not self.total_amount:
            raise UserError(_("Add expense lines first."))
        units = self.building_id.unit_ids.filtered(lambda u: u.status=='leased')
        if not units:
            raise UserError(_("No leased units."))
        bmap = {'bedsitter':.5,'studio':.5,'1br':1,'2br':2,'3br':3,'4br+':4,'penthouse':4,'office':2,'shop':1}
        if self.apportionment == 'sqft':
            denom = sum(u.size_sqft for u in units) or len(units)
            shares = {u.id: u.size_sqft/denom for u in units}
        elif self.apportionment == 'bedrooms':
            denom = sum(bmap.get(u.unit_type,1) for u in units) or len(units)
            shares = {u.id: bmap.get(u.unit_type,1)/denom for u in units}
        else:
            sv = 1/len(units)
            shares = {u.id: sv for u in units}
        invoices = []
        for unit in units:
            lease = self.env['estate.lease'].search([('unit_id','=',unit.id),('status','=','active')],limit=1)
            if not lease:
                continue
            inv = self.env['account.move'].create({
                'move_type':'out_invoice','partner_id':unit.tenant_id.id,
                'lease_id':lease.id,'invoice_date':self.period_date,
                'invoice_line_ids':[(0,0,{
                    'name':f"Service Charge — {self.period_date.strftime('%B %Y')} — {unit.name}",
                    'quantity':1,'price_unit':self.total_amount*shares[unit.id],
                })]
            })
            invoices.append(inv.id)
        self.write({'status':'invoiced'})
        return {'type':'ir.actions.act_window','name':'Service Charge Invoices',
                'res_model':'account.move','view_mode':'list,form','domain':[('id','in',invoices)]}

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name','New')=='New':
                v['name'] = self.env['ir.sequence'].next_by_code('estate.service.charge') or 'New'
        return super().create(vals_list)


class EstateServiceChargeLine(models.Model):
    _name        = 'estate.service.charge.line'
    _description = 'Service Charge Line'
    charge_id    = fields.Many2one('estate.service.charge', ondelete='cascade')
    description  = fields.Char("Description", required=True)
    category     = fields.Selection([
        ('security','Security'),('cleaning','Cleaning'),('lighting','Lighting'),
        ('lift','Lift'),('water','Water/Borehole'),('generator','Generator'),
        ('gardening','Gardening'),('management','Management'),('other','Other'),
    ], required=True, default='other')
    currency_id  = fields.Many2one(related='charge_id.currency_id')
    amount       = fields.Monetary("Amount (KES)", currency_field='currency_id', required=True)
    supplier     = fields.Char("Supplier")
    receipt_ref  = fields.Char("Receipt Ref")
