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

class stock_move_rel_company_memco(osv.osv_memory):
    _name = "stock.move.rel.company.memco"
    _description = "Consume Products"

    _columns = {
        'product_id': fields.many2one('product.product', 'Product', required=True, select=True),
        'product_qty': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'product_uom': fields.many2one('product.uom', 'Product Unit of Measure', required=True),
        'move_qty': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'move_uom': fields.many2one('product.uom', 'Product Unit of Measure'),
        'location_id': fields.many2one('stock.location', 'Location', required=True),
        'restrict_lot_id': fields.many2one('stock.production.lot', 'Lot'),
#        'mo_id':fields.many2one('mrp.production', string='MO'),
#        'move_id':fields.many2one('stock.move', string='Move'),
        'option': fields.selection([('release','Release'),('delete','Delete')],string='Options')
    }
        
    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        box = []
        res = super(stock_move_rel_company_memco, self).default_get(cr, uid, fields, context=context)
        move = self.pool.get('stock.move').browse(cr, uid, context['active_id'], context=context)
        if 'product_id' in fields:
            res.update({'product_id': move.product_id.id})
        if 'product_uom' in fields:
            res.update({'product_uom': move.product_uom.id})
        if 'product_qty' in fields:
            box = sum(line.qty for line in move.reserved_quant_ids)
            res.update({'product_qty': box})
        if 'location_id' in fields:
            res.update({'location_id': move.location_id.id})
        print "RES:>>>>", res
        if res['product_qty'] == 0.00:
            raise osv.except_osv(_('Warning!'), _('Not assign any quantity for this move.'))
        return res


    def do_move_release(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = []
        production_obj = self.pool.get('mrp.production')
        move_obj = self.pool.get('stock.move')
        uom_obj = self.pool.get('product.uom')
        move_ids = context['active_ids']
        remain = 0.00
        for data in self.browse(cr, uid, ids, context=context):
            if data.option == 'release':
                move = move_obj.browse(cr, uid, move_ids[0], context=context)
                box = sum(line.qty for line in move.reserved_quant_ids)
                if data.move_qty > move.product_uom_qty and box <= data.move_qty:
                    raise osv.except_osv(_('Warning!'), _('Quantity allready assigned that move.'))
                if move_ids and move_ids[0]:
                    move = move_obj.browse(cr, uid, move_ids[0], context=context)
                    if move.reserved_quant_ids:
                        for exist_quant in move.reserved_quant_ids:
                            if exist_quant.qty >= data.move_qty and remain == 0.00:
                                remain = exist_quant.qty - data.move_qty
                                print "remain 0:.", remain
                                if remain == 0.00:
                                    self.pool.get('stock.quant').write(cr,uid,exist_quant.id,{'reservation_id':False})
                                    move_obj.write(cr,uid,move.id,{'state':'confirmed'})
                                    break
                                else:
                                    self.pool.get('stock.quant').write(cr,uid,exist_quant.id,{'qty':remain})
                                    new_quant = {
                                    'product_id':exist_quant.product_id.id,
                                    'qty':data.move_qty,
                                    'location_id':exist_quant.location_id.id,
                                    'in_date':exist_quant.in_date,
                                    'reservation_id':False,
                                    }
                                    remain = 0.00
                                    new_quant_id = self.pool.get('stock.quant').create(cr,uid,new_quant)
                                    move_obj.write(cr,uid,move.id,{'state':'confirmed'})
                                    break

                            elif remain == 0.00 and exist_quant.qty <= data.move_qty:
                                remain = data.move_qty - exist_quant.qty
                                print "remain 3:>>>", remain
                                self.pool.get('stock.quant').write(cr,uid,exist_quant.id,{'reservation_id':False})
                                move_obj.write(cr,uid,move.id,{'state':'confirmed'})
                                continue
                            elif remain !=0.00 and exist_quant.qty >=remain:
                                remain = exist_quant.qty - remain
                                print "remain 4:>>>", remain
                                if remain == 0.00:
                                    self.pool.get('stock.quant').write(cr,uid,exist_quant.id,{'reservation_id':False})
                                    break
                                else:
#                                    self.pool.get('stock.quant').write(cr,uid,exist_quant.id,{'reservation_id':False})
#                                    continue
                                    self.pool.get('stock.quant').write(cr,uid,exist_quant.id,{'qty':remain})
                                    new_quant = {
                                    'product_id':exist_quant.product_id.id,
                                    'qty':data.move_qty,
                                    'location_id':exist_quant.location_id.id,
                                    'in_date':exist_quant.in_date,
                                    'reservation_id':False,
                                    }
                                    remain = 0.00
                                    new_quant_id = self.pool.get('stock.quant').create(cr,uid,new_quant)
                                    move_obj.write(cr,uid,move.id,{'state':'confirmed'})
                                    break
                            elif remain !=0.00 and exist_quant.qty <= remain:
                                remain = remain -  exist_quant.qty
                                print "remain 5:>>>", remain
                                if remain == 0.00:
                                    self.pool.get('stock.quant').write(cr,uid,exist_quant.id,{'reservation_id':False})
                                    break
                                else:
                                    self.pool.get('stock.quant').write(cr,uid,exist_quant.id,{'reservation_id':False})
                                    continue

            if data.option == 'delete':
                if move_ids and move_ids[0]:
                    move = move_obj.browse(cr, uid, move_ids[0], context=context)
                    if move.reserved_quant_ids:
#                        for a in move.reserved_quant_ids:
#                            self.pool.get('stock.quant').write(cr,uid,a.id,{'reservation_id':False})
#                            move_obj.write(cr,uid,move.id,{'state':'cancel'})
                        for exist_quant in move.reserved_quant_ids:
                            if exist_quant.qty >= data.move_qty and remain == 0.00:
                                remain = exist_quant.qty - data.move_qty
                                rem = move.product_uom_qty - data.move_qty
                                print "\nremain 0:.", remain, rem
                                if remain == 0.00:
                                    self.pool.get('stock.quant').write(cr,uid,exist_quant.id,{'reservation_id':False})
                                    new_move = move.copy()
                                    move_obj.write(cr,uid,new_move.id,{'state':'cancel','product_uom_qty':data.move_qty})
                                    move_obj.write(cr,uid,move.id,{'product_uom_qty':rem})
                                    break
                                else:
                                    print "\n@@@@@@@@@", data.move_qty
                                    self.pool.get('stock.quant').write(cr,uid,exist_quant.id,{'qty':remain})
                                    new_quant = {
                                    'product_id':exist_quant.product_id.id,
                                    'qty':data.move_qty,
                                    'location_id':exist_quant.location_id.id,
                                    'in_date':exist_quant.in_date,
                                    'reservation_id':False,
                                    }
                                    remain = 0.00
                                    new_quant_id = self.pool.get('stock.quant').create(cr,uid,new_quant)
                                    new_move = move.copy()
   
                                    print 'new move', new_move
                                    print "@@@@@   QTY   @@@@@@", data.product_qty - data.move_qty
                                    
    #                                    new_move_id = self.pool.get('stock.move').create(cr,uid,new_move)
                                    move_obj.write(cr,uid,new_move.id,{'state':'cancel','product_uom_qty':data.move_qty})
                                    move_obj.write(cr,uid,move.id,{'state':'confirmed','product_uom_qty':data.product_qty - data.move_qty})
                                    remain = 0.00
                                    break

                            elif remain == 0.00 and exist_quant.qty < data.move_qty:
                                remain = data.move_qty - exist_quant.qty
                                print "\nremain 3:>>>", remain
                                self.pool.get('stock.quant').write(cr,uid,exist_quant.id,{'reservation_id':False})
                                move_obj.write(cr,uid,move.id,{'state':'cancel'})
                                
                                continue
                            elif remain !=0.00 and exist_quant.qty >=remain:
                                remain = exist_quant.qty - remain
                                rem = move.product_uom_qty - data.move_qty
                                print "\nremain 4:>>>", remain
                                if remain == 0.00:
                                    self.pool.get('stock.quant').write(cr,uid,exist_quant.id,{'reservation_id':False})
                                    new_move = move.copy()
                                    move_obj.write(cr,uid,new_move.id,{'state':'cancel','product_uom_qty':data.move_qty})
                                    move_obj.write(cr,uid,move.id,{'product_uom_qty':rem})
                                    break
                                else:
#                                    self.pool.get('stock.quant').write(cr,uid,exist_quant.id,{'reservation_id':False})
#                                    continue
                                    self.pool.get('stock.quant').write(cr,uid,exist_quant.id,{'qty':remain})
                                    new_quant = {
                                    'product_id':exist_quant.product_id.id,
                                    'qty':data.move_qty,
                                    'location_id':exist_quant.location_id.id,
                                    'in_date':exist_quant.in_date,
                                    'reservation_id':False,
                                    }
                                    remain = 0.00
                                    new_quant_id = self.pool.get('stock.quant').create(cr,uid,new_quant)
                                    new_move = move.copy()
   
                                    print 'new move', new_move
                                    print "@@@@@   QTY   @@@@@@", data.product_qty - data.move_qty
                                    
                                    move_obj.write(cr,uid,new_move.id,{'state':'cancel','product_uom_qty':data.move_qty})
                                    move_obj.write(cr,uid,move.id,{'state':'confirmed','product_uom_qty':rem})
                                    break
                            elif remain !=0.00 and exist_quant.qty <= remain:
                                remain = remain -  exist_quant.qty
                                print "\nremain 5:>>>", remain
                                if remain == 0.00:
                                    self.pool.get('stock.quant').write(cr,uid,exist_quant.id,{'reservation_id':False})
                                    break
                                else:
                                    self.pool.get('stock.quant').write(cr,uid,exist_quant.id,{'reservation_id':False})
                                    continue



#                if not data.move_id.reserved_quant_ids:
#                    print "reserved quant:>>", move.reserved_quant_ids
#                    for a in move.reserved_quant_ids:
#                        aa = self.pool.get('stock.quant').write(cr,uid,a.id,{'reservation_id':False})
#                        print aa



#                quantity_rest = move_qty - data.product_qty
#                print "quantity_rest", quantity_rest
#                quantity_rest_uom = move.product_uom_qty - self.pool.get("product.uom")._compute_qty_obj(cr, uid, move.product_id.uom_id, data.product_qty, move.product_uom)
#                print "Lughai ke sath khata khat", move.reserved_quant_ids
#                for q_line in move.reserved_quant_ids:
#                    print "ASDDDDD:", q_line.qty,data.product_qty, llll


#                if float_compare(quantity_rest_uom, 0, precision_rounding=move.product_uom.rounding) != 0:
#                    new_mov = self.pool.get('stock.move').split(cr, uid, move, quantity_rest, context=context)
#                    move_obj.write(cr, uid, new_mov, {'state':'done'}, context=context)
#                    res.append(new_mov)
#                if res:
#                    self.pool.get('stock.move').action_assign(cr, uid, res, context=context)
#                print "EEEEEEEEEEee", move_ids
#                move_obj.write(cr, uid, move_ids, {'state':'assigned'}, context=context)
            
        return {'type': 'ir.actions.act_window_close'}


