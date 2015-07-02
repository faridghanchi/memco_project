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


#crm.AVAILABLE_STATES.append(('design','Design'))
#crm.AVAILABLE_STATES.append(('des_ready','Design Ready'))
#crm.AVAILABLE_STATES.append(('p_compliance','OK(TMC)'))
#crm.AVAILABLE_STATES.append(('f_compliance','OK(TLC)'))
class memco_comm_line(models.Model):
    """
    """
    _name = 'memco.comm.line'
    project_id = fields.Many2one('product.product',"Project")
    contract_id = fields.Many2one('account.analytic.account')
    comm_id = fields.Many2one('memco.commission')
    
class memco_commission(models.Model):
    """
    """
    _name = 'memco.commission'
    _rec_name = 'create_date'
    
    delivery_id = fields.Many2one('stock.picking')
    user_id = fields.Many2one('res.users', 'Received By')
    received_date = fields.Datetime()
    create_date = fields.Datetime()
    state = fields.Selection([('draft','New'),('confirmed','Confirmed'),('signed','Signed')], "Status")
    line_id = fields.One2many('memco.comm.line','comm_id')
    notes = fields.Text('Comments')
    
    @api.multi
    def button_approval(self):
        self.state = 'confirmed'

    @api.multi
    def button_received_certifcate(self):
        print "self:>",self
        self.received_date = fields.Date.context_today(self)
        now = datetime.strptime(fields.Date.context_today(self), "%Y-%m-%d")
        warranty_date = (now + timedelta(12*365/12)).isoformat()
#        warranty_date = w_date.strftime('%Y-%m-%d')
        print "Warranty Date", warranty_date
        
        for line in self.line_id:
            if warranty_date <= line.contract_id.date:
                line.contract_id.date = warranty_date
        self.state = 'signed'
        self.user_id = self.env.uid


