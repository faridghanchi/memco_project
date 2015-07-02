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
import time
from datetime import datetime, timedelta
from openerp import models, fields, api, _
from openerp.tools import float_compare
from openerp.osv import osv
from openerp.addons import crm


class memco_lesser_request(models.Model):
    """
    """
    _name = 'memco.lesser.request'
    _order = 'create_date'
    _rec_name = 'create_date'

#    @api.one
#    def _get_default_currency(self):
#        res = self.env['res.company'].search([('currency_id','=',self.company_id.id)])
#        return res and res[0] or False 

    product_id = fields.Many2one('product.product', 'Product')
    mo = fields.Char('Mo No')
    notes = fields.Text()
    qty = fields.Float('Quantity')
    request_user = fields.Many2one('res.users','Users')
    

    
