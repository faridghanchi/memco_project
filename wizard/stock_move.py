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
from openerp.exceptions import Warning

class stock_move(models.Model):
    _name= "stock.move"
    _inherit = "stock.move"
    
    def split(self, cr, uid, move, qty, restrict_lot_id=False, restrict_partner_id=False, context=None):
        """ Splits qty from move move into a new move
        :param move: browse record
        :param qty: float. quantity to split (given in product UoM)
        :param restrict_lot_id: optional production lot that can be given in order to force the new move to restrict its choice of quants to this lot.
        :param restrict_partner_id: optional partner that can be given in order to force the new move to restrict its choice of quants to the ones belonging to this partner.
        :param context: dictionay. can contains the special key 'source_location_id' in order to force the source location when copying the move

        returns the ID of the backorder move created
        """
        self.write(cr,uid,move.id,{'state':'ready_to_shipping'})
        if move.state in ('done','cancel'):
            raise osv.except_osv(_('Error'), _('You cannot split a move done'))
        if move.state == 'draft':
            #we restrict the split of a draft move because if not confirmed yet, it may be replaced by several other moves in
            #case of phantom bom (with mrp module). And we don't want to deal with this complexity by copying the product that will explode.
            raise osv.except_osv(_('Error'), _('You cannot split a draft move. It needs to be confirmed first.'))

        if move.product_qty <= qty or qty == 0:
            return move.id

        uom_obj = self.pool.get('product.uom')
        context = context or {}

        #HALF-UP rounding as only rounding errors will be because of propagation of error from default UoM
        uom_qty = uom_obj._compute_qty_obj(cr, uid, move.product_id.uom_id, qty, move.product_uom, rounding_method='HALF-UP', context=context)
        uos_qty = uom_qty * move.product_uos_qty / move.product_uom_qty
        print "Uos_qty sarhad uthate hi values:.>..", uos_qty

        defaults = {
            'product_uom_qty': uom_qty,
            'product_uos_qty': uos_qty,
            'procure_method': 'make_to_stock',
            'restrict_lot_id': restrict_lot_id,
            'restrict_partner_id': restrict_partner_id,
            'split_from': move.id,
            'procurement_id': move.procurement_id.id,
            'move_dest_id': move.move_dest_id.id,
            'origin_returned_move_id': move.origin_returned_move_id.id,
        }
        if context.get('source_location_id'):
            defaults['location_id'] = context['source_location_id']
        new_move = self.copy(cr, uid, move.id, defaults, context=context)

        ctx = context.copy()
        ctx['do_not_propagate'] = True
        self.write(cr, uid, [move.id], {
            'product_uom_qty': move.product_uom_qty - uom_qty,
            'product_uos_qty': move.product_uos_qty - uos_qty
        })

        if move.move_dest_id and move.propagate and move.move_dest_id.state not in ('cancel'):
            new_move_prop = self.split(cr, uid, move.move_dest_id, qty, context=context)
            self.write(cr, uid, [new_move], {'move_dest_id': new_move_prop}, context=context)
        #returning the first element of list returned by action_confirm is ok because we checked it wouldn't be exploded (and
        #thus the result of action_confirm should always be a list of 1 element length)
        return self.action_confirm(cr, uid, [new_move], context=context)[0]
        
        
    

class stock_move_company_memco(osv.osv_memory):
    _name = "stock.move.company.memco"
    _description = "Consume Products"

    _columns = {
        'product_id': fields.many2one('product.product', 'Product', required=True, select=True),
        'product_qty': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'product_uom': fields.many2one('product.uom', 'Product Unit of Measure', required=True),
        'location_id': fields.many2one('stock.location', 'Location', required=True),
        'restrict_lot_id': fields.many2one('stock.production.lot', 'Lot'),
    }

    #TOFIX: product_uom should not have different category of default UOM of product. Qty should be convert into UOM of original move line before going in consume and scrap
    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res = super(stock_move_company_memco, self).default_get(cr, uid, fields, context=context)
        move = self.pool.get('stock.move').browse(cr, uid, context['active_id'], context=context)
        if 'product_id' in fields:
            res.update({'product_id': move.product_id.id})
        if 'product_uom' in fields:
            res.update({'product_uom': move.product_uom.id})
        if 'product_qty' in fields:
            res.update({'product_qty': move.product_uom_qty})
        if 'location_id' in fields:
            res.update({'location_id': move.location_id.id})
        return res


    def do_move_consumed(self, cr, uid, ids, context=None):
        print "PPPPPPPPPPPPP"
        if context is None:
            context = {}
        res = []
        production_obj = self.pool.get('mrp.production')
        move_obj = self.pool.get('stock.move')
        uom_obj = self.pool.get('product.uom')
        move_ids = context['active_ids']
        print "::::>>>", move_ids
        for data in self.browse(cr, uid, ids, context=context):
            if move_ids and move_ids[0]:
                move = move_obj.browse(cr, uid, move_ids[0], context=context)
                move_qty = move.product_qty
#                if move_qty <= 0:
#                    raise osv.except_osv(_('Error!'), _('Cannot consume a move with negative or zero quantity.'))
                quantity_rest = move_qty - data.product_qty
                quantity_rest_uom = move.product_uom_qty - self.pool.get("product.uom")._compute_qty_obj(cr, uid, move.product_id.uom_id, data.product_qty, move.product_uom)
                if float_compare(quantity_rest_uom, 0, precision_rounding=move.product_uom.rounding) != 0:
                    new_mov = self.pool.get('stock.move').split(cr, uid, move, quantity_rest, context=context)
                    move_obj.write(cr, uid, new_mov, {'state':'done'}, context=context)
                    res.append(new_mov)
                if res:
                    self.pool.get('stock.move').action_assign(cr, uid, res, context=context)
                move_obj.write(cr, uid, move_ids, {'state':'assigned'}, context=context)
#            qty = uom_obj._compute_qty(cr, uid, data['product_uom'].id, data.product_qty, data.product_id.uom_id.id)
            
#            if not move_ids.is_approved:
#                raise Warning('Please request to Warehouse Manager for Approval')
        return {'type': 'ir.actions.act_window_close'}


#kaushik
class stock_move_consume(osv.osv_memory):
    _inherit = "stock.move.consume"
    _description = "Consume Products"

    def do_move_consume(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        move_obj = self.pool.get('stock.move')
        uom_obj = self.pool.get('product.uom')
        move_ids = context['active_ids']
        
        for data in self.browse(cr, uid, ids, context=context):
            if move_ids and move_ids[0]:
                move = move_obj.browse(cr, uid, move_ids[0], context=context)
                if not move.is_approved:
#                    mrp_id = move.raw_material_production_id.id
#                    model_obj = self.pool.get('ir.model.data')
#                    res_obj = self.pool.get('res.groups')
#                    user_obj = self.pool.get('res.users')
#                    mrp_obj = self.pool.get('mrp.production')
#                    manager_list = []
#                    view_model, m_id = model_obj.get_object_reference(cr, uid, 'stock', 'group_stock_manager')
#                    m_data = res_obj.browse(cr, uid, m_id)
#                    for user in m_data.users:
#                        partner = user_obj.browse(cr,uid,user.id, context).partner_id.id
#                        manager_list.append(partner)
#                    mrp_obj.message_subscribe(cr, uid, [mrp_id], manager_list, context=context)
#                    mrp_obj.message_post(cr, uid, mrp_id, body=_("New Purchase Request created :%s") % move._description, context=context)
                    raise osv.except_osv(_('Warning!'),_('You can not transfer products. Please contact to warehouse manager.'))
                
            qty = uom_obj._compute_qty(cr, uid, data['product_uom'].id, data.product_qty, data.product_id.uom_id.id)
            move_obj.action_consume(cr, uid, move_ids,
                             qty, data.location_id.id, restrict_lot_id=data.restrict_lot_id.id,
                             context=context)
        return {'type': 'ir.actions.act_window_close'}
