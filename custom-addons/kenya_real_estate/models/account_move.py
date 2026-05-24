# -*- coding: utf-8 -*-
from odoo import models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    # Real Estate Lease Linkage (Fixes the KeyError: 'lease_id')
    lease_id = fields.Many2one('estate.lease', string="Lease", ondelete='set null', copy=False)

    # eTIMS Compliance Tracking Fields
    etims_status = fields.Selection([
        ('unsubmitted', 'Unsubmitted'),
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed')
    ], string='eTIMS Status', default='unsubmitted', copy=False, tracking=True)
    
    etims_receipt_number = fields.Char(string='eTIMS Receipt Number', copy=False, tracking=True)
    etims_signature = fields.Char(string='eTIMS Signature', copy=False, tracking=True)
    etims_error_log = fields.Text(string='eTIMS Error Log', copy=False)
