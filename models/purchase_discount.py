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

class purchase_order(models.Model):
    _inherit = 'purchase.order'
    
    
    @api.one
    @api.depends('order_line.price_subtotal','amount_tax','amount_total','amount_untaxed','disc_amt')
    def _amount_all(self):
        res = {}
        cur_obj=self.env['res.currency']
        for order in self:
            res[order.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
            }
            val = val1 = 0.0
            cur = order.pricelist_id.currency_id
            for line in order.order_line:
               val1 += line.price_subtotal
#               for c in self.env['account.tax'].compute_all(line.taxes_id, line.price_unit, line.product_qty, line.product_id, order.partner_id)['taxes']:
#                    val += c.get('amount', 0.0)
            self.amount_tax=0.00#cur_obj.round(cr, uid, cur, val)
            self.amount_untaxed=val1
            self.amount_total=val1 - self.discount_amt
        return res
   
    @api.onchange('disc_method','disc_amt')
    def _onchange_amt_discount(self):
        if self.disc_method == 'per':
            self.discount_amt = (self.amount_untaxed * self.disc_amt)/100
            self.amount_total = self.amount_untaxed - self.discount_amt
        else:
            self.discount_amt = self.disc_amt
            self.amount_total = self.amount_untaxed - self.discount_amt
            
            
    disc_method = fields.Selection([('per','Percentage'),('fix','Fixed')], 'Discount Method',
                             states={'confirmed': [('readonly',True)],
                                     'approved': [('readonly',True)],
                                     'done': [('readonly',True)]})
    disc_amt = fields.Float('Discount Amount',
                             states={'confirmed': [('readonly',True)],
                                     'approved': [('readonly',True)],
                                     'done': [('readonly',True)]})
    discount_amt = fields.Float(string='-Discount',help="The additional discount on untaxed amount.")
    amount_total = fields.Float(compute='_amount_all', digits=dp.get_precision('Account'), string='Total',multi="sums", 
                help="The total amount")
                
    def _prepare_invoice(self, cr, uid, order, line_ids, context=None):
        """Prepare the dict of values to create the new invoice for a
           purchase order. This method may be overridden to implement custom
           invoice generation (making sure to call super() to establish
           a clean extension chain).

           :param browse_record order: purchase.order record to invoice
           :param list(int) line_ids: list of invoice line IDs that must be
                                      attached to the invoice
           :return: dict of value to create() the invoice
        """
        journal_ids = self.pool['account.journal'].search(
                            cr, uid, [('type', '=', 'purchase'),
                                      ('company_id', '=', order.company_id.id)],
                            limit=1)
        if not journal_ids:
            raise osv.except_osv(
                _('Error!'),
                _('Define purchase journal for this company: "%s" (id:%d).') % \
                    (order.company_id.name, order.company_id.id))
        return {
            'name': order.partner_ref or order.name,
            'reference': order.partner_ref or order.name,
            'account_id': order.partner_id.property_account_payable.id,
            'type': 'in_invoice',
            'partner_id': order.partner_id.id,
            'currency_id': order.currency_id.id,
            'journal_id': len(journal_ids) and journal_ids[0] or False,
            'invoice_line': [(6, 0, line_ids)],
            'origin': order.name,
            'fiscal_position': order.fiscal_position.id or False,
            'payment_term': order.payment_term_id.id or False,
            'company_id': order.company_id.id,
            'disc_method':  order.disc_method,
            'disc_amt': order.disc_amt,
            'discount_amt': order.discount_amt
        }


class purchase_order_line(models.Model):
    _inherit = 'purchase.order.line'
    
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

