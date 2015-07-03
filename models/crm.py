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
from openerp.addons import crm


#crm.AVAILABLE_STATES.append(('design','Design'))
#crm.AVAILABLE_STATES.append(('des_ready','Design Ready'))
#crm.AVAILABLE_STATES.append(('p_compliance','OK(TMC)'))
#crm.AVAILABLE_STATES.append(('f_compliance','OK(TLC)'))

class crm_lead(models.Model):
    """
    """
    _name = 'crm.lead'
    _inherit = 'crm.lead'
#    customer = fields.Many2one('res.partner')
#    user = fields.Many2one('res.users', 'Responsible', required=False)
    order_date = fields.Datetime()
    bom_ids = fields.One2many('mrp.bom','lead_id','BOM')
    project_design = fields.Boolean('Project Design')
    
    
    def case_project_design(self, cr, uid, ids, context=None):
        """ Mark the case as lost: state=cancel and probability=0
        """
        stages_leads = {}
        crm_case_obj = self.pool.get('crm.case.stage')
        model_obj = self.pool.get('ir.model.data')
        group_obj = self.pool.get('res.groups')
        user_obj = self.pool.get('res.users')
        view_model, m_id = model_obj.get_object_reference(cr, uid, 'memco_project', 'group_plant_manager')
        m_data = group_obj.browse(cr,uid,m_id)
        manager_list = []
        for lead in self.browse(cr, uid, ids, context=context):
#            print "lead :>>>", lead,lead.name
            stage_id = crm_case_obj.search(cr, uid, [('name', '=', 'Project Design')])[0]
            if stage_id:
                if stages_leads.get(stage_id):
                    stages_leads[stage_id].append(lead.id)
                else:
                    stages_leads[stage_id] = [lead.id]
            else:
                raise osv.except_osv(_('Warning!'),
                    _('To relieve your sales pipe and group all design opportunities, configure one of your sales stage as follow:\n'
                        'name = Project Design".\n'
                        'Create a specific stage or edit an existing one by editing columns of your opportunity pipe.'))
            
            for user in m_data.users:
                partner = user_obj.browse(cr,uid,user.id, context).partner_id.id
                manager_list.append(partner)
            self.message_subscribe(cr, uid, [lead.id], manager_list, context=context)
            self.message_post(cr, uid, [lead.id], type = 'comment', subtype = "mail.mt_comment", 
                                            body=_("New lead are raise please design this project :%s") % lead.name, context=context)
        for stage_id, lead_ids in stages_leads.items():
            self.write(cr, uid, lead_ids, {'stage_id': stage_id,'project_design':1}, context=context)
        
        
        return True
#    @api.model
#    def name_search(self, name, args=None, operator='ilike', limit=100):
#        args = args or []
#        recs = self.browse()
#        print '*******Name:>>>>>>>>.', name
#        if name:
#            recs = self.search([('name', '=', name)] + args, limit=limit)
#        if not recs:
#            recs = self.search([('code', operator, name)] + args, limit=limit)
#        print "recs:>>>", recs
#        return recs.name_get()
                
#    def name_get(self,cr,uid,ids,context=None):
#        print "WWWWWWWWW"
#        result = {}
#        if context is None:
#            context = {}
#        if not isinstance(ids, list):
#            ids = [ids]
#        res = []
#        if not ids:
#            return res
#        for record in self.browse(cr, uid, ids, context=context):
#            name = record.name
#            if record.code:
#                name = name + ' '+record.code
#            res.append((record.id, name))
#        return res
        
#class mrp_bom_line(models.Model):
#    """
#    This ml coverd information about bom
#    """
#    _inherit = 'mrp.bom.line'
#    price = fields.Float()
#    price_subtotal = fields.Float(string='Total')

#    @api.multi
#    @api.onchange('price','product_qty')
#    def _total_price(self):
#        print "alternative_product",self.product_id.alternative_product
#        alternate = []
#        warning_msgs = ''
#        warning = {}
#        res ={}
#        product_uom_obj = self.env["product.uom"]
#        if self.product_id.alternative_product:
#            for a in self.product_id.alternative_product:
#                alternate.append(str(a.name))
##            uom_record = product_uom_obj.browse(cr, uid, prod.uom_id.id, context=context)
#            compare_qty = float_compare(self.product_id.virtual_available, self.product_qty, precision_rounding=self.product_id.uom_id.rounding)
#            if compare_qty == -1:
#                warn_msg = _('You can choose alternative products %s') % (alternate)
#                warning_msgs += _("Not enough stock ! : ") + warn_msg + "\n\n"
#            if warning_msgs:
#                warning = {
#                           'title': _('Configuration Error!'),
#                           'message' : warning_msgs
#                        }
#        
#        self.price_subtotal = self.product_qty * self.price
#        res.update({'warning': warning})
#        return res
#    
#    def onchange_product_id(self, cr, uid, ids, product_id, product_qty=0, context=None):
#        """ Changes UoM if product_id changes.
#        @param product_id: Changed product_id
#        @return:  Dictionary of changed values
#        """
#        res = {}
#        if product_id:
#            prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
#            res['value'] = {
#                'product_uom': prod.uom_id.id,
#                'product_uos_qty': 0,
#                'product_uos': False,
#                'price': prod.list_price,
#            }
#            if prod.uos_id.id:
#                res['value']['product_uos_qty'] = product_qty * prod.uos_coeff
#                res['value']['product_uos'] = prod.uos_id.id
#                res['value']['price'] = prod.list_price
#        return res

