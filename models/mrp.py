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
from openerp import models, fields, api, _
from openerp.tools import float_compare
from openerp.osv import osv
from datetime import datetime
from openerp.exceptions import Warning

class mrp_bom(models.Model):

    def onchange_lead_id(self, cr, uid, ids, lead_id, context=None):
        res = {}
        if lead_id:
            obj = self.pool.get('crm.lead').browse(cr, uid, lead_id)
            res['customer'] = obj.partner_id.id
        return {'value': res}

    """
    This ml coverd information about bom
    """
    _name = 'mrp.bom'
    _inherit = 'mrp.bom'
    _rec_name = 'name'
    customer = fields.Many2one('res.partner',copy=False)
    user = fields.Many2one('res.users', 'Responsible', required=False,readonly=True)
    lead_id = fields.Many2one('crm.lead', 'Lead',copy=False)
    client_needs = fields.Text(related='lead_id.description',copy=False)
    state = fields.Selection([('new','New'),('design_ready','Design Ready'),('re_design','Re-Design'),('joborder','Customer Agree(Job Order)')], 'Stage',default='new')
    sub_tech_spe = fields.Boolean(string='Submit Technical Specification to GM',copy=False)
    ready_workshop_drawing = fields.Boolean(string='Ready Workshop Drawing',copy=False)
    code = fields.Char(string='Project Code',copy=False)
    standard_design = fields.Boolean()
    _defaults = {
        'user': lambda self, cr, uid, context=None: uid,
    }
    
    @api.one
    def action_button_design_done(self):
#        if not self.sub_tech_spe:
#             raise osv.except_osv(_('Alert'), _('Please submit the Technical specification to GM'))
        
        
        po_data = self
        model_obj = self.env['ir.model.data']
        res_obj = self.env['res.groups']
        lead_obj = self.env['crm.lead']
#        lead=lead_obj.browse(po_data.lead_id)
        print "lead :>>>", po_data,po_data.lead_id
        view_model, m_id = model_obj.get_object_reference('memco_project', 'group_g_manager')
        m_data = res_obj.browse(m_id)
        manager_list = []
        #find the partner related to Budget Control group
        for user in m_data.users:
           manager_list.append(user.partner_id.id)
        #Send the message to all Budget Control Manager for reminder of PO Approval
        print "manager_list", manager_list, po_data, po_data.lead_id
        self.message_post(body = _("Dear Sir, <br/><br/> Design is ready for  %s.\
                           <br/> Thank you, <br/> %s" %(po_data.lead_id.name, po_data.user.name)) ,
                          type = 'comment',
                          subtype = "mail.mt_comment",context = None,
                          model = 'mrp.bom', res_id = po_data.id, 
                          partner_ids = manager_list)
        
        self.write({ 'state' : 'design_ready', })
        crm_case_obj = self.env['crm.case.stage']
        stage_id = crm_case_obj.search([('name', '=', 'Design Ready')])
        if self.lead_id:
            self.lead_id.stage_id = stage_id
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
                
    def action_design_specification_gm(self, cr, uid, ids, context=None):
        print "aaaaaaaaaaaaaaaaa"
        '''
        This function opens a window to compose an email, with the edi sale template message loaded by default
        '''
        assert len(ids) == 1, 'This option should only be used for a single id at a time.'
        ir_model_data = self.pool.get('ir.model.data')
        try:
            template_id = ir_model_data.get_object_reference(cr, uid, 'memco_project', 'email_template_design_gm')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference(cr, uid, 'mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False 
        ctx = dict()
        ctx.update({
            'default_model': 'mrp.bom',
            'default_res_id': ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True
        })
        print "CTX", ctx
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }
    
    def name_get(self,cr,uid,ids,context=None):
        print "WWWWWWWWW"
        result = {}
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        res = []
        if not ids:
            return res
        for record in self.browse(cr, uid, ids, context=context):
            name = record.name
            if record.code:
                name = name + ' '+record.code
#            if context.get('special_shortened_wh_name'):
#                if record.warehouse_id:
#                    name = record.warehouse_id.name
#                else:
#                    name = _('Customer') + ' (' + record.name + ')'
            res.append((record.id, name))
        return res
        
class mrp_bom_line(models.Model):
    """
    This ml coverd information about bom
    """
    _inherit = 'mrp.bom.line'
    price = fields.Float()
    price_subtotal = fields.Float(string='Total')

    @api.multi
    @api.onchange('price','product_qty')
    def _total_price(self):
        print "alternative_product"
        alternate = []
        warning_msgs = ''
        warning = {}
        res ={}
        product_uom_obj = self.env["product.uom"]
        if self.product_id.alternative_product:
            for a in self.product_id.alternative_product:
                alternate.append(str(a.name))
#            uom_record = product_uom_obj.browse(cr, uid, prod.uom_id.id, context=context)
            compare_qty = float_compare(self.product_id.virtual_available, self.product_qty, precision_rounding=self.product_id.uom_id.rounding)
            if compare_qty == -1:
                warn_msg = _('You can choose alternative products %s') % (alternate)
                warning_msgs += _("Not enough stock ! : ") + warn_msg + "\n\n"
            if warning_msgs:
                warning = {
                           'title': _('Configuration Error!'),
                           'message' : warning_msgs
                        }
        
        self.price_subtotal = self.product_qty * self.price
        res.update({'warning': warning})
        return res
    
    def onchange_product_id(self, cr, uid, ids, product_id, product_qty=0, context=None):
        """ Changes UoM if product_id changes.
        @param product_id: Changed product_id
        @return:  Dictionary of changed values
        """
        res = {}
        if product_id:
            prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            res['value'] = {
                'product_uom': prod.uom_id.id,
                'product_uos_qty': 0,
                'product_uos': False,
                'price': prod.list_price,
            }
            if prod.uos_id.id:
                res['value']['product_uos_qty'] = product_qty * prod.uos_coeff
                res['value']['product_uos'] = prod.uos_id.id
                res['value']['price'] = prod.list_price
        return res
        
#    def onchange_product_qty(self, cr, uid, ids, product_id, product_qty,price, context=None):
#        """ Changes UoM if product_id changes.
#        @param product_id: Changed product_id
#        @return:  Dictionary of changed values
#        """
#        res = {} 
#        warning_msgs = ''
#        warning = {}
#        print "##############",product_qty,price
#        tot = product_qty*price
#        if product_id:
#            prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
#            product_uom_obj = self.pool.get('product.uom')
#            alternate = []
#            print ":>>>>>>", prod.virtual_available, product_qty
#            if prod.alternative_product:
#                for a in prod.alternative_product:
#                    alternate.append(str(a.name))
#                uom_record = product_uom_obj.browse(cr, uid, prod.uom_id.id, context=context)
#                compare_qty = float_compare(prod.virtual_available, product_qty, precision_rounding=uom_record.rounding)
#                if compare_qty == -1:
#                    warn_msg = _('You can choose alternative products %s') % (alternate)
#                    warning_msgs += _("Not enough stock ! : ") + warn_msg + "\n\n"
#    #                raise osv.except_osv(('Warning'),('Not Enaugh Stock please choose alternative products'))
#        
#        
#        
#        if warning_msgs:
#            warning = {
#                       'title': _('Configuration Error!'),
#                       'message' : warning_msgs
#                    }
#        res.update({'warning': warning,'price_subtotal':tot})
#        print "RES:>>>", res
#        return res


class mrp_production(models.Model):
    """
    This ml coverd information about bom
    """
    _inherit = 'mrp.production'
    pr_generate = fields.Boolean('PR Generate')
    lead = fields.Many2one(related='bom_id.lead_id')
#    move_lines = fields.One2many('stock.move', 'raw_material_production_id', 'Products to Consume',
#            domain=[('state', 'not in', ('done', 'cancel'))], readonly=True, states=dict.fromkeys(['draft', 'confirmed'], [('readonly', False)])),
#    move_lines = fields.One2many('stock.move', 'raw_material_production_id', 'Products to Consume',
#            domain=[('state', 'not in', ('done', 'cancel'))], readonly=True, states={'draft': [('readonly', False)]}),
    @api.v7
    def act_move_lines_mrp(self, cr, uid, ids, context=None):
        data = self.browse(cr, uid, ids, context)[0]
        move_ids = []
        
        for i in data.move_lines:
            move_ids.append(i.id)
        for i in data.move_lines2:
            move_ids.append(i.id)
    
        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'stock', 'view_move_form')
        form_id = form_res and form_res[1] or False
        tree_res = ir_model_data.get_object_reference(cr, uid, 'memco_project', 'view_tree_stock_move_memco')
        tree_id = tree_res and tree_res[1] or False
        return {
            'name': _('Moves'),
            'view_type': 'form',
            'view_mode': 'tree, form',
            'res_model': 'stock.move',
            'domain': "[('id','in', [" + ','.join(map(str, move_ids)) + "]),('state','in',['confirmed'])]",
            'views': [ (tree_id, 'tree'),(form_id, 'form')],
            'type': 'ir.actions.act_window',
        }
    @api.multi
    def create_pr(self):
        """
        Button create Purchse Request.
        supplier_dict= {}
        for x in t.line_ids:
            if x.supplier_ids:
                for sup in x.supplier_ids:
                    if sup.id not in supplier_dict:
                        supplier_dict[sup.id] = [x.id]
                    else:
                        supplier_dict[sup.id].append(x.id) 
        """
        warning = ''
        warning_msgs = []
        res = {}
        if self.pr_generate:
            raise Warning("Allready PR created for this Design")
            
        supplier_dict= {}
        for x in self.move_lines:
            if x.state == 'confirmed':
                if x.supplier_ids:
                    for sup in x.supplier_ids:
                        if sup.id not in supplier_dict:
                            supplier_dict[sup.id] = [x.id]
                        else:
                            if not x.genarate_pr:
                                supplier_dict[sup.id].append(x.id)
                else:
                    print "aaaaaaaaaaaaaaaaaaa"
                    raise Warning("Supplier are not configure in Product Consume line.\nSupplier set using <<Product to Move>> button")
                
#                warn_msg = _('Supplier are not set in this move line %s') % (x.product_id.name)
#                warning_msgs += _("Warning ! : ") + warn_msg + "\n\n"
#                if warning_msgs:
#                    warning = {
#                               'title': _('Configuration Error!'),
#                               'message' : warning_msgs
#                            }
#                    res.update({'warning': warning})
                
        for line in supplier_dict:
            supp = self.env['res.partner'].browse(line)
            oll = []
            for mo_l in supplier_dict[line]:
                stock_move = self.env['stock.move'].browse(mo_l)
                oll.append((0,False,{
                    'product_id':stock_move.product_id.id,
                    'name':stock_move.product_id.name,
                    'product_qty':stock_move.product_uom_qty,
                    'price_unit':stock_move.product_id.standard_price,
                    'date_planned':datetime.today(),
                    }))
                stock_move.genarate_pr = True
            print "self.bom_id.name"
            pr = {
                'partner_id':supp.id,
                'date_order':datetime.today(),
                'pr_name': self.bom_id.name + str(self.bom_id.code) or '',
                'order_line':oll,
                'location_id':self.location_src_id.id,
                'pricelist_id':supp.property_product_pricelist_purchase.id,
                'origin':self.name,
                'project': self.id
            }
            self.env['purchase.order'].create(pr)
        self.pr_generate = True
        return res
        
    @api.multi
    def _cost_raw_calculation(self, production):
        print "Production:>>."
        cost = 0.0
         
        for line in production.move_lines2:
            print "line.unit_local_c_cost", line.l_cost
            print "line.unit_inter_c_cost", line.i_cost
            p_cost = line.product_id.standard_price *line.product_uom_qty
            local_cost = line.l_cost * line.product_uom_qty
            inter_cost = line.i_cost * line.product_uom_qty
            lc_cost = line.lc_cost * line.product_uom_qty
            cost += p_cost + local_cost + inter_cost + lc_cost
            print "Cost:>>."
        production.product_id.standard_price = cost

    @api.multi
    def action_production_end(self):
        """ Changes production state to Finish and writes finished date.
        @return: True
        """
        for production in self:
            self._costs_generate(production)
            self._cost_raw_calculation(production)
        print "ffffffff", self.id
        self.state ='done'
        self.date_finished = time.strftime('%Y-%m-%d %H:%M:%S')
        # Check related procurements
        proc_obj = self.env["procurement.order"]
        procs = proc_obj.search([('production_id', 'in', [self.id])])
        proc_obj.check(procs)
        
        
    @api.v7
    def _make_consume_line_from_data(self, cr, uid, production, product, uom_id, qty, uos_id, uos_qty, context=None):
        stock_move = self.pool.get('stock.move')
        loc_obj = self.pool.get('stock.location')
        # Internal shipment is created for Stockable and Consumer Products
        if product.type not in ('product', 'consu'):
            return False
        # Take routing location as a Source Location.
        source_location_id = production.location_src_id.id
        prod_location_id = source_location_id
        prev_move= False
        if production.bom_id.routing_id and production.bom_id.routing_id.location_id and production.bom_id.routing_id.location_id.id != source_location_id:
            source_location_id = production.bom_id.routing_id.location_id.id
            prev_move = True

#        self_data  = self.browse(cr, uid, product.id, context=context)
        seller_ids_list = []
        for seller in product.seller_ids:
            print "___seller___",seller
            seller_ids_list.append(seller.name.id)



        print "::::::::::::::::seller_ids_list:::::::::",seller_ids_list
        
        destination_location_id = production.product_id.property_stock_production.id
       
        value = {
            'name': production.name,
            'date': production.date_planned,
            'product_id': product.id,
            'product_uom_qty': qty,
            'product_uom': uom_id,
            'product_uos_qty': uos_id and uos_qty or False,
            'product_uos': uos_id or False,
            'location_id': source_location_id,
            'location_dest_id': destination_location_id,
            'company_id': production.company_id.id,
            'procure_method': prev_move and 'make_to_stock' or self._get_raw_material_procure_method(cr, uid, product, location_id=source_location_id,
                                                                                                     location_dest_id=destination_location_id, context=context), #Make_to_stock avoids creating procurement
            'raw_material_production_id': production.id,
            #this saves us a browse in create()
            'price_unit': product.standard_price,
            'origin': production.name,
            'warehouse_id': loc_obj.get_warehouse(cr, uid, production.location_src_id, context=context),
            'group_id': production.move_prod_id.group_id.id,
            'supplier_ids': [(6, 0, seller_ids_list)] #kaushik
        }
        move_id = stock_move.create(cr, uid, value, context=context)
        
        if prev_move:
            prev_move = self._create_previous_move(cr, uid, move_id, product, prod_location_id, source_location_id, context=context)
            stock_move.action_confirm(cr, uid, [prev_move], context=context)
        return move_id
