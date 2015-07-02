# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from openerp.osv import fields, osv
from openerp.tools.translate import _

class local_line(osv.osv_memory):

    _name = "local.line"
    _columns = {
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'price':fields.float(string='Cost price'),
        'local_carrire_id':fields.many2one('local.invoice.carrier', 'local carrier'),
        
    }
class local_invoice_carrier(osv.osv_memory):

    _name = "local.invoice.carrier"
    _columns = {
        'journal_id': fields.many2one('account.journal', 'Destination Journal', required=True),
        'group': fields.boolean("Group by partner"),
        'invoice_date': fields.date('Invoice Date'),
        'partner_id':fields.many2one('res.partner', 'Partner'),
        'line_id':fields.one2many('local.line','local_carrire_id',string="Line"),
        'ref':fields.char('Reference'),
        'carrier_cost_id':fields.many2one('carrier.extra.cost', 'Carrier Cost'),
    }
    _defaults = {
#        'journal_type': _get_journal_type,
#        'journal_id' : _get_journal,
    }
    
    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res = super(local_invoice_carrier, self).default_get(cr, uid, fields, context=context)
        active_ids = context.get('active_ids',[])
        pick = self.pool.get('stock.picking').browse(cr, uid, context['active_id'], context=context)
        select_line = self.pool.get('carrier.extra.cost').browse(cr, uid, context['active_id'], context=context)
#        pick1 = self.pool.get('stock.picking').read(cr, uid, context['active_id'], context=context)
        carrier_extra_obj = self.pool.get('carrier.extra.cost')
        pickk = []
        for a in select_line.m_cost_line:
            pickk.append((0, 0, {
                'product_id':a.product.id,
                'price':a.cost,
                'local_carrire_id':active_ids
            }))
        if 'partner_id' in fields:
            res.update({'partner_id': select_line.carrier_company.id})
        if 'ref' in fields:
            res.update({'ref': select_line.l_picking_id.origin})
        if 'carrier_cost_id' in fields:
            res.update({'carrier_cost_id': select_line.id})
        if 'line_id' in fields:
            res.update({'line_id': pickk})
        return res

    def view_init(self, cr, uid, fields_list, context=None):
        if context is None:
            context = {}
        res = super(local_invoice_carrier, self).view_init(cr, uid, fields_list, context=context)
        pick_obj = self.pool.get('stock.picking')
        count = 0
        active_ids = context.get('active_ids',[])
#        for pick in pick_obj.browse(cr, uid, active_ids, context=context):
#            if pick.done_l_carrier_invoice == True:
#                raise osv.except_osv(_('Warning!'), _('None of these picking lists require invoicing.'))
        return res

    def open_invoice(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        
        invoice_ids = self.create_invoice(cr, uid, ids, context=context)
        if not invoice_ids:
            raise osv.except_osv(_('Error!'), _('No invoice created!'))

        data = self.browse(cr, uid, ids[0], context=context)

        action_model = False
        action = {}
        
        journal2type = {'sale':'out_invoice', 'purchase':'in_invoice' , 'sale_refund':'out_refund', 'purchase_refund':'in_refund'}
        inv_type = 'in_invoice'
        data_pool = self.pool.get('ir.model.data')
        if inv_type == "in_invoice":
            action_id = data_pool.xmlid_to_res_id(cr, uid, 'account.action_invoice_tree2')

        if action_id:
            action_pool = self.pool['ir.actions.act_window']
            action = action_pool.read(cr, uid, action_id, context=context)
            action['domain'] = "[('id','in', ["+str(invoice_ids)+"])]"
            return action
        return True

    def create_invoice(self, cr, uid, ids, context=None):
        res ={}
        context = dict(context or {})
        picking_pool = self.pool.get('stock.picking')
        carrier_pool = self.pool.get('carrier.extra.cost')
        invoice_obj = self.pool.get('account.invoice')
        invoice_line_obj = self.pool.get('account.invoice.line')
        data = self.browse(cr, uid, ids[0], context=context)
        user_id = self.pool.get('res.users').browse(cr,uid,uid,context=None)
        ppick = []
        for a in data.line_id:
            print "a", a,a.product_id
#            aaa = {
#                'discount': 0.0,
#                'uos_id': a.product_id.uom_id.id,
#                'account_analytic_id': data.journal_id.id,
#                'product_id':a.product_id.id,
#                'price_unit':a.price,
#                'name':a.product_id.name,
#                'quantity':1
#            }
            ppick.append((0, False, {
                'discount': 0.0,
                'uos_id': a.product_id.uom_id.id,
#                'account_analytic_id': data.journal_id.id,
                'product_id':a.product_id.id,
                'price_unit':a.price,
                'name':a.product_id.name,
                'quantity':1
            }))
#            ppick.append(aaa)
        print 'pickk',ppick, data.partner_id.name
        a = data.partner_id.property_account_payable.id
        inv = {
                    
                    'date_due': data.invoice_date,
                    'date_invoice':data.invoice_date,
                    'company_id': user_id.company_id.id,
                    'currency_id': user_id.company_id.currency_id.id,
                    'user_id': uid,
                    'name': data.ref,
                    'origin': data.ref,
                    'type': 'in_invoice',
                    'journal_id':data.journal_id.id,
                    'reference' : data.partner_id.ref,
                    'account_id': a,
                    'partner_id': data.partner_id.id,
                    'invoice_line':ppick,
#                    'currency_id' : orders[0].currency_id.id,
#                    'comment': multiple_order_invoice_notes(orders),
#                    'payment_term': orders[0].payment_term_id.id,
#                    'fiscal_position': partner.property_account_position.id
                }
        print 'inv', inv
        res = invoice_obj.create(cr, uid, inv)
        carrier_pool.write(cr,uid,data.carrier_cost_id.id,{'state':'done'})
        
#        inv = {
#            'partner_id':data.partner_id.id,
#            'date_invoice':data.invoice_date,
#            'invoice_line':ppick
#        }
#        pa = invoice_obj.create(cr,uid,inv)
#        pa = invoice_line_obj.create(cr,uid,ppick)
        return res

