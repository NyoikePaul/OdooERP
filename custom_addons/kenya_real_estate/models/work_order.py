"""
Maintenance Work Orders — Kenya
Assign contractors/technicians, track materials, auto-create vendor bills.
"""
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class EstateWorkOrder(models.Model):
    _name        = 'estate.work.order'
    _description = 'Maintenance Work Order'
    _inherit     = ['mail.thread', 'mail.activity.mixin']
    _order       = 'create_date desc'

    name         = fields.Char("Work Order Ref", readonly=True, copy=False, default='New')
    maintenance_id = fields.Many2one('estate.maintenance.request', string="Maintenance Request",
                                      required=True, ondelete='restrict')
    property_id  = fields.Many2one(related='maintenance_id.property_id', store=True)
    unit_id      = fields.Many2one(related='maintenance_id.unit_id', store=True)

    # Assignment
    assigned_to  = fields.Many2one('res.users',   string="Technician")
    contractor_id= fields.Many2one('res.partner', string="Contractor/Vendor")
    contractor_ref = fields.Char("Contractor LPO/Quote Ref")

    # Schedule
    scheduled_date = fields.Datetime("Scheduled Date")
    start_date     = fields.Datetime("Started At")
    end_date       = fields.Datetime("Completed At")
    labor_hours    = fields.Float("Labor Hours")

    # Costs
    currency_id    = fields.Many2one('res.currency', default=lambda s: s.env.ref('base.KES'))
    labor_rate     = fields.Monetary("Labor Rate (KES/hr)", currency_field='currency_id')
    labor_cost     = fields.Monetary("Labor Cost (KES)", currency_field='currency_id',
                                      compute='_compute_costs', store=True)
    material_cost  = fields.Monetary("Materials Cost (KES)", currency_field='currency_id')
    total_cost     = fields.Monetary("Total Cost (KES)", currency_field='currency_id',
                                      compute='_compute_costs', store=True)
    vendor_bill_id = fields.Many2one('account.move', string="Vendor Bill", readonly=True)

    # Status
    status = fields.Selection([
        ('draft',       'Draft'),
        ('assigned',    'Assigned'),
        ('in_progress', 'In Progress'),
        ('done',        'Completed'),
        ('billed',      'Billed'),
        ('cancelled',   'Cancelled'),
    ], default='draft', tracking=True)

    # Items
    item_ids     = fields.One2many('estate.work.order.item', 'work_order_id', string="Materials")
    work_notes   = fields.Text("Work Done / Notes")

    _sql_constraints = [('name_unique','UNIQUE(name)','Work order ref must be unique.')]

    @api.depends('labor_hours','labor_rate','material_cost','item_ids.total_cost')
    def _compute_costs(self):
        for r in self:
            r.labor_cost  = r.labor_hours * r.labor_rate
            mat = sum(r.item_ids.mapped('total_cost'))
            r.material_cost = mat
            r.total_cost  = r.labor_cost + mat

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name','New') == 'New':
                v['name'] = self.env['ir.sequence'].next_by_code('estate.work.order') or 'New'
        return super().create(vals_list)

    def action_assign(self):
        if not self.assigned_to and not self.contractor_id:
            raise UserError(_("Assign a technician or contractor first."))
        self.write({'status':'assigned'})
        self.maintenance_id.write({'status':'in_progress'})

    def action_start(self):
        self.write({'status':'in_progress','start_date':fields.Datetime.now()})

    def action_complete(self):
        self.write({'status':'done','end_date':fields.Datetime.now()})
        self.maintenance_id.write({
            'status':'done',
            'actual_cost':self.total_cost,
            'date_resolved':fields.Date.today(),
        })
        self.message_post(body=_(
            f"Work order completed. Total cost: KES {self.total_cost:,.0f}. "
            f"Labor: {self.labor_hours}hrs @ KES {self.labor_rate:,.0f}/hr."))

    def action_create_vendor_bill(self):
        """Auto-create vendor bill for contractor."""
        self.ensure_one()
        if not self.contractor_id:
            raise UserError(_("No contractor set on this work order."))
        if self.status != 'done':
            raise UserError(_("Complete the work order first."))
        lines = [(0,0,{
            'name':f"Labor — {self.maintenance_id.name} ({self.labor_hours}hrs)",
            'quantity':1,'price_unit':self.labor_cost,
        })]
        for item in self.item_ids:
            lines.append((0,0,{
                'name':f"Material — {item.description}",
                'quantity':item.quantity,'price_unit':item.unit_cost,
            }))
        bill = self.env['account.move'].create({
            'move_type':    'in_invoice',
            'partner_id':   self.contractor_id.id,
            'invoice_date': fields.Date.today(),
            'ref':          self.contractor_ref or self.name,
            'invoice_line_ids': lines,
        })
        self.write({'vendor_bill_id':bill.id,'status':'billed'})
        return {'type':'ir.actions.act_window','res_model':'account.move',
                'res_id':bill.id,'view_mode':'form'}


class EstateWorkOrderItem(models.Model):
    _name        = 'estate.work.order.item'
    _description = 'Work Order Material Item'

    work_order_id = fields.Many2one('estate.work.order', ondelete='cascade')
    description   = fields.Char("Material/Item", required=True)
    quantity      = fields.Float("Qty", default=1)
    currency_id   = fields.Many2one(related='work_order_id.currency_id')
    unit_cost     = fields.Monetary("Unit Cost (KES)", currency_field='currency_id')
    total_cost    = fields.Monetary("Total (KES)", currency_field='currency_id',
                                     compute='_compute', store=True)
    supplier      = fields.Char("Supplier")

    @api.depends('quantity','unit_cost')
    def _compute(self):
        for r in self:
            r.total_cost = r.quantity * r.unit_cost
