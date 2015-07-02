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
from openerp import models, fields as new_fields, api
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare

class stock_move_assign_company_memco(osv.osv_memory):
    _name = "stock.move.assign.company.memco"
    _description = "Consume Products assign to another project"

    _columns = {
        'product_id': fields.many2one('product.product', 'Product', required=True, select=True),
        'product_qty': fields.float('Total Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'product_uom': fields.many2one('product.uom', 'Product Unit of Measure', required=True),
#        'location_id': fields.many2one('stock.location', 'Location', required=True),
        'assign_qty': fields.float('Assign Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'p_uom': fields.many2one('product.uom', 'Product Unit of Measure'),
        'restrict_lot_id': fields.many2one('stock.production.lot', 'Lot'),
        'mo_id':fields.many2one('mrp.production', string='Manufacturing'),
        'move_id':fields.many2one('stock.move', string='Assign Move'),
    }
        
    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        box = []
        box1 = []
        res = super(stock_move_assign_company_memco, self).default_get(cr, uid, fields, context=context)
        move = self.pool.get('stock.move').browse(cr, uid, context['active_id'], context=context)
        if 'product_id' in fields:
            res.update({'product_id': move.product_id.id})
        if 'product_uom' in fields:
            res.update({'product_uom': move.product_uom.id})
        if 'product_qty' in fields:
            box = sum(line.qty for line in move.reserved_quant_ids)
            res.update({'product_qty': box})
        if 'assign_qty' in fields:
            box1 = sum(line.qty for line in move.reserved_quant_ids)
            res.update({'assign_qty': box1})
#        if 'location_id' in fields:
#            res.update({'location_id': move.location_id.id})
        print "RES:>>>>", res
        if res['product_qty'] == 0.00:
            raise osv.except_osv(_('Warning!'), _('Not assign any quantity for this move.'))
        return res


    def do_move_assign(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = []
        box = []
        production_obj = self.pool.get('mrp.production')
        move_obj = self.pool.get('stock.move')
        uom_obj = self.pool.get('product.uom')
        move_ids = context['active_ids']
        remain = 0.00
        for data in self.browse(cr, uid, ids, context=context):
            box = sum(line.qty for line in data.move_id.reserved_quant_ids)
            #box = 0
            #data.assign_qty = 15
            #data.move_id.product_uom_qty >= data.assign_qty
            #
            #
#            if box <= data.assign_qty:
#                raise osv.except_osv(_('Warning!'), _('Quantity allready assigned that move.'))
            if data.assign_qty > data.move_id.product_uom_qty and box <= data.assign_qty:
                raise osv.except_osv(_('Warning!'), _('Quantity allready assigned that move.'))
            if move_ids and move_ids[0]:
                move = move_obj.browse(cr, uid, move_ids[0], context=context)
                if move.reserved_quant_ids:
                    for exist_quant in move.reserved_quant_ids:
                        if exist_quant.qty >= data.assign_qty:
                            remain = exist_quant.qty - data.assign_qty
                            print "remain 0:.", remain
                            self.pool.get('stock.quant').write(cr,uid,exist_quant.id,{'qty':remain})
                            new_quant = {
                            'product_id':exist_quant.product_id.id,
                            'qty':data.assign_qty,
                            'location_id':exist_quant.location_id.id,
                            'in_date':exist_quant.in_date,
                            'reservation_id':data.move_id.id,
                            }
                            remain = 0.00
                            new_quant_id = self.pool.get('stock.quant').create(cr,uid,new_quant)
                            move_obj.write(cr,uid,move.id,{'state':'assigned'})
                            break
                        elif exist_quant.qty <= data.assign_qty:
                            remain = data.assign_qty - exist_quant.qty
                            self.pool.get('stock.quant').write(cr,uid,exist_quant.id,{'reservation_id':data.move_id.id})
                            continue
                        elif remain == 0.00 and exist_quant.qty <= data.assign_qty:
                            remain = data.assign_qty - exist_quant.qty
                            print "remain 1:>>>", remain
                            self.pool.get('stock.quant').write(cr,uid,exist_quant.id,{'reservation_id':data.move_id.id})
                            move_obj.write(cr,uid,move.id,{'state':'confirmed'})
                            continue
                        elif remain !=0.00 and exist_quant.qty >= remain:
                            remain = exist_quant.qty - remain
                            print "remain 2:>>>", remain
                            self.pool.get('stock.quant').write(cr,uid,exist_quant.id,{'reservation_id':data.move_id.id})
                            continue
                        elif remain !=0.00 and exist_quant.qty <= remain:
                            remain = exist_quant.qty - remain
                            print "remain 3:>>>", remain
                            self.pool.get('stock.quant').write(cr,uid,exist_quant.id,{'reservation_id':data.move_id.id})
                            continue
                        
#                        if data.move_id.reserved_quant_ids:
#                            box = []
#                            for com in data.move_id.reserved_quant_ids:
#                                box.append(com.qty)
#                            print 'reserved quant ids:>>>',data.move_id.reserved_quant_ids,lll
#                            self.pool.get('stock.quant').write(cr,uid,exist_quant.id,{'reservation_id':data.move_id.id})
                print "data.move_id", data.move_id
                
                #self.pool.get('stock.quant').write(cr,uid,exist_move.id,{'reservation_id':data.move_id.id})

#                if not data.move_id.reserved_quant_ids:
#                    print "reserved quant:>>", move.reserved_quant_ids
#                    for a in move.reserved_quant_ids:
#                        aa = self.pool.get('stock.quant').write(cr,uid,a.id,{'reservation_id':False})
#                        print aa

        return {'type': 'ir.actions.act_window_close'}


