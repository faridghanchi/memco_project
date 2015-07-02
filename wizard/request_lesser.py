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

class lesser_cutting(osv.osv_memory):

    _name = "lesser.cutting"
    _columns = {
        'create_date': fields.date('Invoice Date'),
        'product_id':fields.many2one('product.product', 'Product'),
        'ref':fields.char('Reference'),
        'required_qty':fields.float('Required Qty'),
        'create_date':fields.date(),
        'notes':fields.text('Notes'),
        'request_user' : fields.many2one('res.users','Requested User')
    }
    _defaults = {
#        'journal_type': _get_journal_type,
#        'journal_id' : _get_journal,
    }
    
    def default_get(self, cr, uid, fields, context=None):
        print "kkkkkkkkk"
        if context is None:
            context = {}
        res = super(lesser_cutting, self).default_get(cr, uid, fields, context=context)
        active_ids = context.get('active_ids',[])
        print "active_ids", active_ids
        mo = self.pool.get('mrp.production').browse(cr, uid, active_ids, context=context)
        print "MO:>>>>",mo, mo.user_id
        pickk = []
        if 'ref' in fields:
            res.update({'ref': mo.name})
        if 'request_user' in fields:
            res.update({'request_user': mo.user_id.id})
        return res

    def view_init(self, cr, uid, fields_list, context=None):
        if context is None:
            context = {}
        res = super(lesser_cutting, self).view_init(cr, uid, fields_list, context=context)
        mo_obj = self.pool.get('mrp.production')
        count = 0
        active_ids = context.get('active_ids',[])
#        for pick in pick_obj.browse(cr, uid, active_ids, context=context):
#            if pick.done_l_carrier_invoice == True:
#                raise osv.except_osv(_('Warning!'), _('None of these picking lists require invoicing.'))
        return res

    def open_lesser_request(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        
        invoice_ids = self.create_request(cr, uid, ids, context=context)
        if not invoice_ids:
            raise osv.except_osv(_('Error!'), _('No invoice created!'))

        data = self.browse(cr, uid, ids[0], context=context)

        action_model = False
        action = {}
        
#        journal2type = {'sale':'out_invoice', 'purchase':'in_invoice' , 'sale_refund':'out_refund', 'purchase_refund':'in_refund'}
#        inv_type = 'in_invoice'
        data_pool = self.pool.get('ir.model.data')
        action_id = data_pool.xmlid_to_res_id(cr, uid, 'memco_project.tree_view_memco_lesser_request1')

        if action_id:
            action_pool = self.pool['ir.actions.act_window']
            action = action_pool.browse(cr, uid, action_id, context=context)
#            action['domain'] = "[('id','in', ["+str(invoice_ids)+"])]"
            return action.id
        return True

    def create_request(self, cr, uid, ids, context=None):
        res ={}
        print "ppppppppppppppppppppppppp"
        context = dict(context or {})
        picking_pool = self.pool.get('stock.picking')
        carrier_pool = self.pool.get('carrier.extra.cost')
        lesser_obj = self.pool.get('memco.lesser.request')
        invoice_line_obj = self.pool.get('account.invoice.line')
        data = self.browse(cr, uid, ids[0], context=context)
        print "datadatadatadatadatadatadata", data
        user_id = self.pool.get('res.users').browse(cr,uid,uid,context=None)
        ppick = []
        ppick = {
            'product_id': data.product_id.id,
            'mo': data.ref,
            'notes':data.notes,
            'qty':data.required_qty,
            'request_user':data.request_user.id,
        }
        print 'pickk',ppick
        res = lesser_obj.create(cr, uid, ppick)
        return res

