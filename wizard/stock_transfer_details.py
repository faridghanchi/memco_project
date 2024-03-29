# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-TODAY OpenERP S.A. <http://www.odoo.com>
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

from openerp import models, fields, api
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from datetime import datetime
from openerp.exceptions import Warning

class stock_transfer_details(models.TransientModel):
    _inherit = 'stock.transfer_details'
    
    def default_get(self, cr, uid, fields, context=None):
        res = super(stock_transfer_details, self).default_get(cr, uid, fields, context=context)
        if context is None: context = {}
        res = super(stock_transfer_details, self).default_get(cr, uid, fields, context=context)
        picking_ids = context.get('active_ids', [])
        active_model = context.get('active_model')

        if not picking_ids or len(picking_ids) != 1:
            # Partial Picking Processing may only be done for one picking at a time
            return res
        assert active_model in ('stock.picking'), 'Bad context propagation'
        picking_id, = picking_ids
        picking = self.pool.get('stock.picking').browse(cr, uid, picking_id, context=context)
        print "picking:>>>>>>", picking,picking.picking_type_id, picking.picking_type_id.code,picking.picking_type_id.name
        items = []
        packs = []
        picking.do_prepare_partial()
        for op in picking.pack_operation_ids:
            item = {
                'packop_id': op.id,
                'product_id': op.product_id.id,
                'product_uom_id': op.product_uom_id.id,
                'quantity': op.product_qty,
                'package_id': op.package_id.id,
                'lot_id': op.lot_id.id,
                'sourceloc_id': op.location_id.id,
                'destinationloc_id': op.location_dest_id.id,
                'result_package_id': op.result_package_id.id,
                'date': op.date, 
                'owner_id': op.owner_id.id,
                'local_carrier_cost':picking.i_carrier_cost,
                'international_c_cost':picking.l_carrier_cost,
                'unit_lc_cost':picking.lc_cost,
                
            }
            
            if op.product_id:
                items.append(item)
            elif op.package_id:
                packs.append(item)
#            print "\n@@@@@@@@@@@@@@Items:.", item
        total_qty = []
        total_net_total = []
        for line in items:
#            total_qty.append(line['quantity'])
            product = self.pool.get('product.product').browse(cr,uid,line['product_id'])
            print "product",product
            total_net_total.append(line['quantity'] * product.standard_price)
        if picking.picking_type_id.code == 'incoming':
            """Only for incoming shipment means purchase time
            """
            for line in items:
                """
                suppose Product A | qty=10
                        Product B | qty=5
                        Product C | qty=5 and Local_carrier_cost = 400, International_c_cost = 200
                        total qty=20
                        20 ---------100%
                        10 --------  ?  
                        100*10/20= 50% for Product A.
                        100*5/20= 25% for Product B.
                        100*5/20= 25% for Product C.
                        
                        New logic
                        
                        Nettotal(qty*unitprice) 
                        cost = line_total * carreier_cost /sum(total_net_total)
                        1000 * 100 / 1500
                """
    #            a = (line['local_carrier_cost']*((100 * line['quantity']) /sum(total_qty)))/100
    #            b = (line['international_c_cost']*((100 * line['quantity']) /sum(total_qty)))/100
    #            c = (line['unit_lc_cost']*((100 * line['quantity']) /sum(total_qty)))/100
    #            line['local_carrier_cost'] = a/line['quantity']
    #            line['international_c_cost'] = b/line['quantity']
    #            line['unit_lc_cost'] = c/line['quantity']


    #            a = ((line['local_carrier_cost'] * line['quantity']) /sum(total_qty))
    #            b = ((line['international_c_cost'] * line['quantity']) /sum(total_qty))
    #            c = ((line['unit_lc_cost'] * line['quantity']) /sum(total_qty))
    #            line['local_carrier_cost'] = a
    #            line['international_c_cost'] = b
    #            line['unit_lc_cost'] = c
                product = self.pool.get('product.product').browse(cr,uid,line['product_id'])
    #            1000*100/1500
                if not product.standard_price:
                    raise Warning ("You must set cost price in product Configuration!")
                print "line['quantity']", line['quantity'], product.standard_price,line['local_carrier_cost']
                local_cost = (((line['quantity']*product.standard_price) * line['local_carrier_cost']) /sum(total_net_total))
                inter_cost = (((line['quantity']*product.standard_price) * line['international_c_cost']) / sum(total_net_total))
                lc_cost = (((line['quantity']*product.standard_price) * line['unit_lc_cost']) / sum(total_net_total))
                
                line['local_carrier_cost'] = local_cost
                line['international_c_cost'] = inter_cost
                line['unit_lc_cost'] = lc_cost

        res.update(item_ids=items)
        res.update(packop_ids=packs)
        return res
        
        
    @api.one
    def do_detailed_transfer(self):
        processed_ids = []
        # Create new and update existing pack operations
        for lstits in [self.item_ids, self.packop_ids]:
            for prod in lstits:
#                print "\n################## prod", prod
                pack_datas = {
                    'product_id': prod.product_id.id,
                    'product_uom_id': prod.product_uom_id.id,
                    'product_qty': prod.quantity,
                    'package_id': prod.package_id.id,
                    'lot_id': prod.lot_id.id,
                    'location_id': prod.sourceloc_id.id,
                    'location_dest_id': prod.destinationloc_id.id,
                    'result_package_id': prod.result_package_id.id,
                    'date': prod.date if prod.date else datetime.now(),
                    'owner_id': prod.owner_id.id
                }

                if prod.packop_id:
                    prod.packop_id.write(pack_datas)
                    processed_ids.append(prod.packop_id.id)
                else:
                    pack_datas['picking_id'] = self.picking_id.id
                    packop_id = self.env['stock.pack.operation'].create(pack_datas)
                    processed_ids.append(packop_id.id)

                #probuse
#                print "prod.local_carrier_cost", prod.local_carrier_cost
                prod.product_id.local_carrier_cost = prod.local_carrier_cost/prod.quantity
                prod.product_id.international_c_cost = prod.international_c_cost/prod.quantity
                prod.product_id.unit_lc_cost = prod.unit_lc_cost/prod.quantity

        # Delete the others
        packops = self.env['stock.pack.operation'].search(['&', ('picking_id', '=', self.picking_id.id), '!', ('id', 'in', processed_ids)])
        for packop in packops:
            packop.unlink()

        # Execute the transfer of the picking
        self.picking_id.do_transfer()

        return True

class stock_transfer_details_items(models.TransientModel):
    _inherit = 'stock.transfer_details_items'
    
    local_carrier_cost = fields.Float()
    international_c_cost = fields.Float(string='International Carrier Cost')
    unit_lc_cost = fields.Float(string='Unit LC cost')

