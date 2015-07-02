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
#from openerp.tools.translate import _
#from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
from openerp import models, fields, api, _
from openerp.tools import float_compare
from openerp.osv import osv

class product_new_category(models.Model):
    """
    """
    _name = 'product.new.category'
    name = fields.Char()


class product_template(models.Model):
    _inherit = 'product.template'
#        'pro_category': fields.selection([
#            ('electic', 'Electric'),
#            ('mechanics', 'Mechanics'),
#            ('finish_pro', 'Finish Product'),
#            ('sheet', 'Sheet'),('motor','Motor')
#            ], 'Product Category'),
    pro_cat = fields.Many2one('product.new.category',string="Category")
#    standard_no = fields.Char('Standard no')
    alternative_product = fields.Many2many('product.template','product_alternative_rel1','src_id1','dest_id1', string='Alternative Products', help='Alternative Product')
    local_carrier_cost = fields.Float()
    international_c_cost = fields.Float(string='International Carrier Cost')
    unit_lc_cost = fields.Float(string='LC cost')
    total_cost = fields.Float(string='Total cost',compute='_get_total_cost')
    
    
    
    @api.multi
    #@api.depends('picking_id')
    def _get_total_cost(self):
        self.total_cost = self.local_carrier_cost + self.international_c_cost + self.standard_price + self.unit_lc_cost
    
