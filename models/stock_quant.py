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
from openerp.tools.float_utils import float_compare, float_round
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp import SUPERUSER_ID, api
import openerp.addons.decimal_precision as dp
from datetime import date, datetime
from dateutil import relativedelta
from openerp.osv import osv

class stock_quant(models.Model):

    _name = 'stock.quant'
    _inherit = 'stock.quant'
    local_carrier_cost = fields.Float()
    international_c_cost = fields.Float(string='International Carrier Cost')
    unit_lc_cost = fields.Float(string='LC cost')
    total_cost = fields.Float('Total Cost',compute='_get_total')

    @api.multi
    def _get_total(self):
        if self.local_carrier_cost and self.international_c_cost:
            self.total_cost = self.local_carrier_cost + self.international_c_cost + self.unit_lc_cost


    def move_quants_write(self, cr, uid, quants, move, location_dest_id, dest_package_id, context=None):
        res = super(stock_quant, self).move_quants_write(cr, uid, quants, move, location_dest_id,  dest_package_id, context=context)
        if move.product_id.valuation == 'real_time':
            self._account_entry_move(cr, uid, quants, move, context=context)
        return res
    def move_quants_write(self, cr, uid, quants, move, location_dest_id, dest_package_id, context=None):
        context=context or {}
#        vals = {'location_id': location_dest_id.id,
#                'history_ids': [(4, move.id)],
#                'reservation_id': False}
        l_cost = []
        i_cost = []
        i = 0
        for quant in quants:
            i+=1
            l_cost.append(quant.local_carrier_cost/quant.qty)
            i_cost.append(quant.international_c_cost/quant.qty)
        self.pool.get('stock.move').write(cr, uid, [move.id], {'l_cost': sum(l_cost)/i, 'i_cost': sum(i_cost)/i})
#        if not context.get('entire_pack'):
#            vals.update({'package_id': dest_package_id})
#        self.write(cr, SUPERUSER_ID, [q.id for q in quants], vals, context=context)
        return super(stock_quant, self).move_quants_write(cr, uid, quants, move, location_dest_id,  dest_package_id, context=context)
        
#    def move_quants_write(self, cr, uid, quants, move, location_dest_id, dest_package_id, context=None):
#        context=context or {}
#        vals = {'location_id': location_dest_id.id,
#                'history_ids': [(4, move.id)],
#                'reservation_id': False}
#        l_cost = []
#        i_cost = []
#        i = 0
#        for quant in quants:
#            i+=1
#            l_cost.append(quant.local_carrier_cost/quant.qty)
#            i_cost.append(quant.international_c_cost/quant.qty)
#        self.pool.get('stock.move').write(cr, uid, [move.id], {'l_cost': sum(l_cost)/i, 'i_cost': sum(i_cost)/i})
#        if not context.get('entire_pack'):
#            vals.update({'package_id': dest_package_id})
#        self.write(cr, SUPERUSER_ID, [q.id for q in quants], vals, context=context)
        
    def _quant_create(self, cr, uid, qty, move, lot_id=False, owner_id=False, src_package_id=False, dest_package_id=False,
                      force_location_from=False, force_location_to=False, context=None):
        '''Create a quant in the destination location and create a negative quant in the source location if it's an internal location.
        '''
        if context is None:
            context = {}
        price_unit = self.pool.get('stock.move').get_price_unit(cr, uid, move, context=context)
        location = force_location_to or move.location_dest_id
        rounding = move.product_id.uom_id.rounding
        vals = {
            'product_id': move.product_id.id,
            'location_id': location.id,
            'qty': float_round(qty, precision_rounding=rounding),
            'cost': price_unit,
            'history_ids': [(4, move.id)],
            'in_date': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'company_id': move.company_id.id,
            'lot_id': lot_id,
            'owner_id': owner_id,
            'package_id': dest_package_id,
            'local_carrier_cost': move.unit_local_c_cost * qty or '',
            'international_c_cost':move.unit_inter_c_cost * qty or '',
            'unit_lc_cost':move.unit_lc_cost * qty or '',
        }
        self.pool.get('product.product').write(cr,uid,move.product_id.id,{'local_carrier_cost':move.unit_local_c_cost,'international_c_cost':move.unit_inter_c_cost,'unit_lc_cost':move.unit_lc_cost})

        if move.location_id.usage == 'internal':
            #if we were trying to move something from an internal location and reach here (quant creation),
            #it means that a negative quant has to be created as well.
            negative_vals = vals.copy()
            negative_vals['location_id'] = force_location_from and force_location_from.id or move.location_id.id
            negative_vals['qty'] = float_round(-qty, precision_rounding=rounding)
            negative_vals['cost'] = price_unit
            negative_vals['negative_move_id'] = move.id
            negative_vals['package_id'] = src_package_id
            negative_quant_id = self.create(cr, SUPERUSER_ID, negative_vals, context=context)
            vals.update({'propagated_from_id': negative_quant_id})

        #create the quant as superuser, because we want to restrict the creation of quant manually: we should always use this method to create quants
        quant_id = self.create(cr, SUPERUSER_ID, vals, context=context)
        return self.browse(cr, uid, quant_id, context=context)

