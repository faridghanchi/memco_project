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

from openerp import models, fields, api, _
from openerp.tools import float_compare
from openerp.osv import osv

class stock_move(models.Model):
    """
    """
    _name = 'stock.move'
    _inherit = 'stock.move'
    
#    def _get_suppliers(self):
#        p = self.env['product.product'].browse(prod_id).product_tmpl_id
#        suppliers =[]
#        for a in p.seller_ids:
#            suppliers.append(a.name.id)
#        print "suppliers:>>>>", suppliers
#        if res:
#            res['value'].update({'supplier_ids':suppliers})
#        print "res:>>>>>.."

    @api.model
    def _get_suppliers(self):
        print "########", self
        for move in self:
            p = self.env['product.product'].browse(move.product_id.id).product_tmpl_id
            suppliers = []
            for a in p.seller_ids:
                suppliers.append(a.name.id)
            return suppliers
    
    is_approved = fields.Boolean("Is Approved", readonly=True)
    
    supplier_ids = fields.Many2many('res.partner',string='Supplier Name')
    genarate_pr = fields.Boolean("Generate Purchase Request")
    additional_product = fields.Boolean("Additional Products")
    unit_local_c_cost = fields.Float(string='Local Carrier Unit cost',compute='_get_carrier_cost')
    unit_inter_c_cost = fields.Float(string='International Carrier Unit cost',compute='_get_carrier_cost')
    unit_lc_cost = fields.Float(string='LC cost')
    notes = fields.Text('Notes')
    state = fields.Selection([('draft', 'New'),
                                   ('cancel', 'Cancelled'),
                                   ('waiting', 'Waiting Another Move'),
                                   ('confirmed', 'Waiting Availability'),
                                   ('assigned', 'Available'),
                                   ('ready_to_shipping','Ready To Shipping'),
                                   ('shipping_process','Shipping Process'),
                                   ('done', 'Done'),
                                   ], 'Status', readonly=True, select=True, copy=False,
                 help= "* New: When the stock move is created and not yet confirmed.\n"\
                       "* Waiting Another Move: This state can be seen when a move is waiting for another one, for example in a chained flow.\n"\
                       "* Waiting Availability: This state is reached when the procurement resolution is not straight forward. It may need the scheduler to run, a component to me manufactured...\n"\
                       "* Available: When products are reserved, it is set to \'Available\'.\n"\
                       "* Done: When the shipment is processed, the state is \'Done\'.")
    l_cost = fields.Float(string='Local Carrier Cost')
    i_cost = fields.Float(string="Internatioanl Carrier Cost")
    lc_cost = fields.Float(string="LC Cost")

    @api.multi
    def approved_warehouse_man(self):
        if self.location_dest_id.name == 'Production' and self.location_id.name == 'Stock':
            return self.write({'is_approved': True})


#    @api.one#kk
#    def approved_warehouse_man(self):
#        """ Changes the state to assigned.
#        @return: True
#        """
#        print "&&&&&&&&&&&&&&&&&"
#        print "self.location_dest_id.name", self.location_dest_id.name
##        self.is_approved = True
#        self.write({'approve': True})
#        print stop
#        print "comp", self.location_id.name, self.is_approved
#        if self.location_dest_id.name == 'Production' and self.location_id == 'Stock':
#            self.is_approved = True

#    @api.multi
#    def _get_carrier_cost(self):
#        """
#            suppose Product A | qty=10
#                    Product B | qty=5
#                    Product C | qty=5 and Local_carrier_cost = 400, International_c_cost = 200
#                    total qty=20
#                    20 ---------100%
#                    10 --------  ?  
#                    totA = 100*10/20= 50% for Product A.
#                    totB = 100*5/20= 25% for Product B.
#                    totC = 100*5/20= 25% for Product C.
#                    
#                    Unit carrier cost = totA / qty
#            """
#        total_qty = []
#        print "*****@@@@@@@@@@@@@@", self
#        for mov in self:
#            if mov.picking_id:
#                for mo_line in mov.picking_id.move_lines:
#                    total_qty.append(mo_line.product_uom_qty)
#        print "Total_qty:>>>>", total_qty
#        for mov in self:
#            if mov.picking_id:
#                for line in mov.picking_id.move_lines:
#                    a = ((mov.picking_id.carrier_cost *((100 * line.product_uom_qty) /sum(total_qty)))/100)
#                    b = ((mov.picking_id.l_carrier_cost *((100 * line.product_uom_qty) /sum(total_qty)))/100)
#                    line.unit_inter_c_cost = a/line.product_uom_qty
#                    line.unit_local_c_cost = b/line.product_uom_qty
#        return True

    @api.multi
    def _get_carrier_cost(self):
        """
            suppose Product A | qty=10
                    Product B | qty=5
                    Product C | qty=5 and Local_carrier_cost = 400, International_c_cost = 200
                    total qty=20
                    20 ---------100%
                    10 --------  ?  
                    totA = 100*10/20= 50% for Product A.
                    totB = 100*5/20= 25% for Product B.
                    totC = 100*5/20= 25% for Product C.
                    
                    Unit carrier cost = totA / qty

                Channges:
                 Product A | Qty=10 price=100 total=1000 discount=10 net total=990
                 Product A | Qty=10 price=50 total=500 discount=10 net total=490
                 
                 total net total=1480
                 100/1480*990=66.89
                 100/1480*490=33.11
            """
        total_qty = []
        all_id = []
        all_ids = []
        total_net_total = []
        for move_data in self:
            for mo_line in move_data.picking_id.move_lines:
                if mo_line.id not in all_id: 
                    all_id.append(mo_line.id)
                    total_qty.append(mo_line.product_uom_qty)
                    total_net_total.append(mo_line.product_uom_qty*mo_line.product_id.standard_price)
        for data in self:
            for mo_line in data.picking_id.move_lines:
                if mo_line.id not in all_ids: 
                    inter = (((mo_line.product_uom_qty*mo_line.product_id.standard_price) * \
                            data.picking_id.i_carrier_cost) / sum(total_net_total))
                    local = (((mo_line.product_uom_qty*mo_line.product_id.standard_price) * \
                            data.picking_id.l_carrier_cost) / sum(total_net_total))
                    lc = (((mo_line.product_uom_qty*mo_line.product_id.standard_price) * \
                            data.picking_id.lc_cost) * sum(total_net_total))
                    mo_line.unit_local_c_cost = local
                    mo_line.unit_inter_c_cost = inter
                    mo_line.unit_lc_cost = lc
        return True
        
   

    @api.multi
    @api.depends('product_id','move_lines')
    def onchange_product_id(self,prod_id=False, loc_id=False, loc_dest_id=False, partner_id=False):
        res = super(stock_move, self).onchange_product_id(prod_id=prod_id, loc_id=loc_id, loc_dest_id=loc_dest_id, partner_id=partner_id)
        p = self.env['product.product'].browse(prod_id).product_tmpl_id
        suppliers =[]
        for a in p.seller_ids:
            suppliers.append(a.name.id)
#        print "suppliers:>>>>", suppliers
        if res:
            res['value'].update({'supplier_ids':suppliers})
        return res

    
#    def action_consume(self, cr, uid, ids, product_qty, location_id=False, restrict_lot_id=False, restrict_partner_id=False,
#                       consumed_for=False, context=None):
#        """ Consumed product with specific quantity from specific source location.
#        @param product_qty: Consumed/produced product quantity (= in quantity of UoM of product)
#        @param location_id: Source location
#        @param restrict_lot_id: optionnal parameter that allows to restrict the choice of quants on this specific lot
#        @param restrict_partner_id: optionnal parameter that allows to restrict the choice of quants to this specific partner
#        @param consumed_for: optionnal parameter given to this function to make the link between raw material consumed and produced product, for a better traceability
#        @return: New lines created if not everything was consumed for this line
#        """
#        if context is None:
#            context = {}
#        res = []
#        production_obj = self.pool.get('mrp.production')

#        if product_qty <= 0:
#            raise osv.except_osv(_('Warning!'), _('Please provide proper quantity.'))
##        #because of the action_confirm that can create extra moves in case of phantom bom, we need to make 2 loops
#        ids2 = []
#        for move in self.browse(cr, uid, ids, context=context):
#            if move.state == 'draft':
#                ids2.extend(self.action_confirm(cr, uid, [move.id], context=context))
#            else:
#                ids2.append(move.id)

#        prod_orders = set()
#        for move in self.browse(cr, uid, ids2, context=context):
#            prod_orders.add(move.raw_material_production_id.id or move.production_id.id)
#            move_qty = move.product_qty
###            product_uom_obj = self.pool.get('product.uom')
###            uom_record = product_uom_obj.browse(cr, uid, move.product_uom.id, context=context)
###            compare_qty = float_compare(move.product_id.virtual_available, move.product_qty, precision_rounding=uom_record.rounding)
###            print "compare_qty", compare_qty
###            if compare_qty == -1:
###                print "move.product_id.qty_available:", move.product_id.qty_available,move.product_id.name
####            if move.product_qty > move.product_id.qty_available:
###                raise osv.except_osv(_('Warning!'), _('Not Enaugh Stock! Cannot consume product, less quantity,Please contact to Purchase manager.'))
###            print "move.product_qty", move.product_id, move.product_id.qty_available, move.product_qty
#            if move_qty <= 0:
#                raise osv.except_osv(_('Error!'), _('Cannot consume a move with negative or zero quantity.'))
#            quantity_rest = move_qty - product_qty
##            # Compare with numbers of move uom as we want to avoid a split with 0 qty
#            quantity_rest_uom = move.product_uom_qty - self.pool.get("product.uom")._compute_qty_obj(cr, uid, move.product_id.uom_id, product_qty, move.product_uom)
#            if float_compare(quantity_rest_uom, 0, precision_rounding=move.product_uom.rounding) != 0:
#                new_mov = self.split(cr, uid, move, quantity_rest, context=context)
#                res.append(new_mov)
#            vals = {'restrict_lot_id': restrict_lot_id,
#                    'restrict_partner_id': restrict_partner_id,
#                    'consumed_for': consumed_for}
#            if location_id:
#                vals.update({'location_id': location_id})
#            self.write(cr, uid, [move.id], vals, context=context)
##        # Original moves will be the quantities consumed, so they need to be done
#        self.action_done(cr, uid, ids2, context=context)
#        if res:
#            self.action_assign(cr, uid, res, context=context)
#        if prod_orders:
#            production_obj.signal_workflow(cr, uid, list(prod_orders), 'button_produce')
#        return res
