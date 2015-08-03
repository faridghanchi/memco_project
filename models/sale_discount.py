# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2015 Probuse Consulting Service Pvt Ltd (<http://www.probuse.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp import models, fields, api, _
from openerp.tools import float_compare,DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.osv import osv
import openerp.addons.decimal_precision as dp
from datetime import datetime, timedelta
import time
from datetime import timedelta
from datetime import datetime

class sale_order(models.Model):
    _inherit = 'sale.order'
    
    
    @api.v7
    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        res = super(sale_order,self)._amount_all(cr, uid, ids, field_name, arg, context=context)
#        cur_obj = self.pool.get('res.currency')
#        res = {}
        for order in self.browse(cr, uid, ids, context=context):

            res[order.id]['amount_total'] = res[order.id]['amount_untaxed'] - order.discount_amt
        return res
        
    
#    @api.one
#    @api.depends('order_line.price_subtotal','amount_tax','amount_total','amount_untaxed','disc_amt')
#    def _amount_all(self):
#        res = {}
#        cur_obj=self.env['res.currency']
#        for order in self:
#            res[order.id] = {
#                'amount_untaxed': 0.0,
#                'amount_tax': 0.0,
#                'amount_total': 0.0,
#            }
#            val = val1 = 0.0
#            cur = order.pricelist_id.currency_id
#            for line in order.order_line:
#               val1 += line.price_subtotal
##               for c in self.env['account.tax'].compute_all(line.taxes_id, line.price_unit, line.product_qty, line.product_id, order.partner_id)['taxes']:
##                    val += c.get('amount', 0.0)
#            self.amount_tax=0.00#cur_obj.round(cr, uid, cur, val)
#            self.amount_untaxed=val1
#            self.amount_total=val1 - self.discount_amt
#        return res
#   
    @api.onchange('disc_method','disc_amt','amount_untaxed','order_line')
    def _onchange_amt_discount(self):
        if self.disc_method == 'per':
            self.discount_amt = (self.amount_untaxed * self.disc_amt)/100
            self.amount_total = self.amount_untaxed - self.discount_amt
        else:
            self.discount_amt = self.disc_amt
            self.amount_total = self.amount_untaxed - self.discount_amt
#            
            
    disc_method = fields.Selection([('per','Percentage'),('fix','Fixed')], 'Discount Method',
                             states={'confirmed': [('readonly',True)],
                                     'approved': [('readonly',True)],
                                     'done': [('readonly',True)]})
    disc_amt = fields.Float('Discount Amount',
                             states={'confirmed': [('readonly',True)],
                                     'approved': [('readonly',True)],
                                     'done': [('readonly',True)]})
    discount_amt = fields.Float(string='- Discount',help="The additional discount on untaxed amount.")
#    amount_total = fields.Float(compute='_amount_all', digits=dp.get_precision('Account'), string='Total',multi="sums", 
#                help="The total amount")
                

class sale_order_line(models.Model):
    _inherit = 'sale.order.line'
    
    @api.multi
    def _amount_line_disc(self):
        for line in self:
            if line.line_discount:
                line.price_nettotal = line.price_subtotal - line.line_discount
            else:
                line.price_nettotal = line.price_subtotal

    @api.multi
    @api.depends('order_id.discount_amt')
    def _compute_line_discount(self):
        for line in self:
            if line.price_subtotal:
                order_dicount_amt = line.order_id.discount_amt
                order_total_amt = line.order_id.amount_untaxed
                discount_perc = (line.price_subtotal * 100) / order_total_amt
                line_discount = (order_dicount_amt * discount_perc)/100
                line.line_discount = line_discount
    
    line_discount = fields.Float(compute= '_compute_line_discount',string='Discount')
    price_nettotal = fields.Float(compute='_amount_line_disc', string='Net Total', digits_compute= dp.get_precision('Account'))
