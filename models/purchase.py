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

#from openerp.osv import osv, fields
#from datetime import datetime, timedelta
#import time
#from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
#import openerp.addons.decimal_precision as dp
#from openerp.tools.float_utils import float_compare
#from openerp.tools.translate import _

from openerp import models, fields, api, _
from openerp.tools import float_compare,DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.osv import osv
import openerp.addons.decimal_precision as dp
from datetime import datetime, timedelta
import time
from datetime import timedelta
from datetime import datetime

class purchase_order_line(models.Model):
    """
    This POL coverd information about bom
    """
    _inherit = 'purchase.order.line'
    source_ref = fields.Char()
    avail_qty = fields.Float(string='Qty available')
    incoming_qty = fields.Float(string='Incoming')
    forecast_qty = fields.Float(string='Forecast qty')
    
    
    def onchange_product_id(self, cr, uid, ids, pricelist_id, product_id, qty, uom_id,
            partner_id, date_order=False, fiscal_position_id=False, date_planned=False,
            name=False, price_unit=False, state='draft', context=None):
        """
        onchange handler of product_id.
        """
        
        if context is None:
            context = {}

        res = {'value': {'price_unit': price_unit or 0.0, 
                            'name': name or '', 
                            'product_uom' : uom_id or False,
                            }}
        
        if not product_id:
            return res

        product_product = self.pool.get('product.product')
        product_uom = self.pool.get('product.uom')
        res_partner = self.pool.get('res.partner')
        product_pricelist = self.pool.get('product.pricelist')
        account_fiscal_position = self.pool.get('account.fiscal.position')
        account_tax = self.pool.get('account.tax')

        # - check for the presence of partner_id and pricelist_id
        #if not partner_id:
        #    raise osv.except_osv(_('No Partner!'), _('Select a partner in purchase order to choose a product.'))
        #if not pricelist_id:
        #    raise osv.except_osv(_('No Pricelist !'), _('Select a price list in the purchase order form before choosing a product.'))

        # - determine name and notes based on product in partner lang.
        context_partner = context.copy()
        if partner_id:
            lang = res_partner.browse(cr, uid, partner_id).lang
            context_partner.update( {'lang': lang, 'partner_id': partner_id} )
        product = product_product.browse(cr, uid, product_id, context=context_partner)
        #call name_get() with partner in the context to eventually match name and description in the seller_ids field
        dummy, name = product_product.name_get(cr, uid, product_id, context=context_partner)[0]
        if product.description_purchase:
            name += '\n' + product.description_purchase
        res['value'].update({'name': name,'avail_qty':0.0,
                            'incoming_qty':1.0,
                            'forecast_qty':2.0})

        # - set a domain on product_uom
        res['domain'] = {'product_uom': [('category_id','=',product.uom_id.category_id.id)]}

        # - check that uom and product uom belong to the same category
        product_uom_po_id = product.uom_po_id.id
        if not uom_id:
            uom_id = product_uom_po_id

        if product.uom_id.category_id.id != product_uom.browse(cr, uid, uom_id, context=context).category_id.id:
            if context.get('purchase_uom_check') and self._check_product_uom_group(cr, uid, context=context):
                res['warning'] = {'title': _('Warning!'), 'message': _('Selected Unit of Measure does not belong to the same category as the product Unit of Measure.')}
            uom_id = product_uom_po_id

        res['value'].update({'product_uom': uom_id})

        # - determine product_qty and date_planned based on seller info
        if not date_order:
            date_order = fields.datetime.now()


        supplierinfo = False
        precision = self.pool.get('decimal.precision').precision_get(cr, uid, 'Product Unit of Measure')
        for supplier in product.seller_ids:
            if partner_id and (supplier.name.id == partner_id):
                supplierinfo = supplier
                if supplierinfo.product_uom.id != uom_id:
                    res['warning'] = {'title': _('Warning!'), 'message': _('The selected supplier only sells this product by %s') % supplierinfo.product_uom.name }
                min_qty = product_uom._compute_qty(cr, uid, supplierinfo.product_uom.id, supplierinfo.min_qty, to_uom_id=uom_id)
                if float_compare(min_qty , qty, precision_digits=precision) == 1: # If the supplier quantity is greater than entered from user, set minimal.
                    if qty:
                        res['warning'] = {'title': _('Warning!'), 'message': _('The selected supplier has a minimal quantity set to %s %s, you should not purchase less.') % (supplierinfo.min_qty, supplierinfo.product_uom.name)}
                    qty = min_qty
        dt = self._get_date_planned(cr, uid, supplierinfo, date_order, context=context).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        qty = qty or 1.0
        res['value'].update({'date_planned': date_planned or dt})
        if qty:
            res['value'].update({'product_qty': qty})

        price = price_unit
        if price_unit is False or price_unit is None:
            # - determine price_unit and taxes_id
            if pricelist_id:
                date_order_str = datetime.strptime(date_order, DEFAULT_SERVER_DATETIME_FORMAT).strftime(DEFAULT_SERVER_DATE_FORMAT)
                price = product_pricelist.price_get(cr, uid, [pricelist_id],
                        product.id, qty or 1.0, partner_id or False, {'uom': uom_id, 'date': date_order_str})[pricelist_id]
            else:
                price = product.standard_price

        taxes = account_tax.browse(cr, uid, map(lambda x: x.id, product.supplier_taxes_id))
        fpos = fiscal_position_id and account_fiscal_position.browse(cr, uid, fiscal_position_id, context=context) or False
        taxes_ids = account_fiscal_position.map_tax(cr, uid, fpos, taxes)
        
        
        res['value'].update({'price_unit': price, 'taxes_id': taxes_ids,'avail_qty':product.qty_available,
                            'incoming_qty':product.incoming_qty,
                            'forecast_qty':product.virtual_available})

        return res


class purchase_order(models.Model):
    _inherit = 'purchase.order'

    pr_name= fields.Char('PR Name')
    pr_priority = fields.Selection([('1', 'High'),('2', 'Normal'),('3', 'Very High')],string="Priority")
#    approved_gm = fields.Boolean(string="Approved by GM")
    expected_days = fields.Integer()
    project = fields.Many2one('mrp.production', 'Project', copy=False)

    @api.onchange('expected_days','minimum_planned_date')
    def _onchange_expected_date(self):
        if self.expected_days:
            cu_date = time.strftime("%Y-%m-%d")
            now = datetime.strptime(cu_date, "%Y-%m-%d")
            
            exp_date = now + timedelta(days=self.expected_days)
            print "exp_date", exp_date
            self.minimum_planned_date = exp_date.strftime('%Y-%m-%d')

    def create(self, cr, uid, vals, context=None):
        if vals.get('name','/')=='/':
            vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'purchase.order') or '/'
        context = dict(context or {}, mail_create_nolog=True)
        order =  super(purchase_order, self).create(cr, uid, vals, context=context)
        model_obj = self.pool.get('ir.model.data')
        group_obj = self.pool.get('res.groups')
        user_obj = self.pool.get('res.users')
        view_model, m_id = model_obj.get_object_reference(cr, uid, 'purchase', 'group_purchase_manager')
        m_data = group_obj.browse(cr,uid,m_id)
        manager_list = []
        for user in m_data.users:
            partner = user_obj.browse(cr,uid,user.id, context).partner_id.id
            manager_list.append(partner)
        self.message_subscribe(cr, uid, [order], manager_list, context=context)
        self.message_post(cr, uid, [order], type = 'comment', subtype = "mail.mt_comment", 
                                    body=_("New Purchase Request created :%s") % vals.get('name','/'), context=context)
        return order

    def wkf_confirm_order(self, cr, uid, ids, context=None):
        todo = []
        for po in self.browse(cr, uid, ids, context=context):
            if not po.order_line:
                raise osv.except_osv(_('Error!'),_('You cannot confirm a purchase order without any purchase order line.'))
            if po.invoice_method == 'picking' and not any([l.product_id and l.product_id.type in ('product', 'consu') for l in po.order_line]):
                raise osv.except_osv(
                    _('Error!'),
                    _("You cannot confirm a purchase order with Invoice Control Method 'Based on incoming shipments' that doesn't contain any stockable item."))
#            if not po.approved_gm:
#                raise osv.except_osv(_('Warning'),_("Please approved Purchase Order by GM"))
            for line in po.order_line:
                if line.state=='draft':
                    todo.append(line.id)        
        self.pool.get('purchase.order.line').action_confirm(cr, uid, todo, context)
        for id in ids:
            self.write(cr, uid, [id], {'state' : 'confirmed', 'validator' : uid})
        return True

#
#    def _prepare_order_line_move(self, cr, uid, order, order_line, picking_id, group_id, context=None):
#        ''' prepare the stock move data from the PO line. This function returns a list of dictionary ready to be used in stock.move's create()'''
#        product_uom = self.pool.get('product.uom')
#        price_unit = order_line.price_unit
#        if order_line.product_uom.id != order_line.product_id.uom_id.id:
#            price_unit *= order_line.product_uom.factor / order_line.product_id.uom_id.factor
#        if order.currency_id.id != order.company_id.currency_id.id:
#            #we don't round the price_unit, as we may want to store the standard price with more digits than allowed by the currency
#            price_unit = self.pool.get('res.currency').compute(cr, uid, order.currency_id.id, order.company_id.currency_id.id, price_unit, round=False, context=context)
#        res = []
#        move_template = {
#            'name': order_line.name or '',
#            'product_id': order_line.product_id.id,
#            'product_uom': order_line.product_uom.id,
#            'product_uos': order_line.product_uom.id,
#            'date': order.date_order,
#            'date_expected': fields.date.date_to_datetime(self, cr, uid, order_line.date_planned, context),
#            'location_id': order.partner_id.property_stock_supplier.id,
#            'location_dest_id': order.location_id.id,
#            'picking_id': picking_id,
#            'partner_id': order.dest_address_id.id or order.partner_id.id,
#            'move_dest_id': False,
#            'state': 'draft',
#            'purchase_line_id': order_line.id,
#            'company_id': order.company_id.id,
#            'price_unit': price_unit,
#            'picking_type_id': order.picking_type_id.id,
#            'group_id': group_id,
#            'procurement_id': False,
#            'origin': order.name,
#            'route_ids': order.picking_type_id.warehouse_id and [(6, 0, [x.id for x in order.picking_type_id.warehouse_id.route_ids])] or [],
#            'warehouse_id':order.picking_type_id.warehouse_id.id,
#            'invoice_state': order.invoice_method == 'picking' and '2binvoiced' or 'none',
#        }

#        print "order_line.product_id,", order_line.product_id, order_line.product_id.qty_available
#        
#        diff_quantity = order_line.product_qty
#        if order_line.product_id.qty_available > diff_quantity:
#            w = order_line.product_id.qty_available - diff_quantity
#        print "diff_quantity", diff_quantity
#        for procurement in order_line.procurement_ids:
#            procurement_qty = product_uom._compute_qty(cr, uid, procurement.product_uom.id, procurement.product_qty, to_uom_id=order_line.product_uom.id)
#            tmp = move_template.copy()
#            tmp.update({
#                'product_uom_qty': min(procurement_qty, diff_quantity),
#                'product_uos_qty': min(procurement_qty, diff_quantity),
#                'move_dest_id': procurement.move_dest_id.id,  #move destination is same as procurement destination
#                'group_id': procurement.group_id.id or group_id,  #move group is same as group of procurements if it exists, otherwise take another group
#                'procurement_id': procurement.id,
#                'invoice_state': procurement.rule_id.invoice_state or (procurement.location_id and procurement.location_id.usage == 'customer' and procurement.invoice_state=='2binvoiced' and '2binvoiced') or (order.invoice_method == 'picking' and '2binvoiced') or 'none', #dropship case takes from sale
#                'propagate': procurement.rule_id.propagate,
#            })
#            diff_quantity -= min(procurement_qty, diff_quantity)
#            res.append(tmp)
#        #if the order line has a bigger quantity than the procurement it was for (manually changed or minimal quantity), then
#        #split the future stock move in two because the route followed may be different.
#        if float_compare(diff_quantity, 0.0, precision_rounding=order_line.product_uom.rounding) > 0:
#            move_template['product_uom_qty'] = diff_quantity
#            move_template['product_uos_qty'] = diff_quantity
#            res.append(move_template)
#        res1 = []
#        for a in res:
#            print 'res:>>>.',res, a.get('product_id')
#            product = self.pool.get('product.product').browse(cr,uid,a.get('product_id'))
#            print "\n product.qty_available", product.qty_available, a.get('product_uos_qty')
#            if a.get('product_uos_qty') > product.qty_available:
#                qty = a.get('product_uos_qty') - product.qty_available
#                print "qqqqqqqq", qty
#                a.update({'product_uos_qty':qty,'product_uom_qty':qty})
#                res1.append(a)
#            if a.get('product_uos_qty') < product.qty_available:
#                qty = a.get('product_uos_qty') - product.qty_available
#                print "qqqqqqqq", qty
#                a.update({'product_uos_qty':0.00, 'product_uom_qty':0.00})
#                res1.append(a)
#        print "@@@@@@@", res1
#        return res1
        
        
    
