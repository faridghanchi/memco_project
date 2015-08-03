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
from openerp.exceptions import Warning
from openerp.osv import osv


class sale_order(models.Model):

    _inherit = 'sale.order'


    @api.model
    def _user_get(self):
        user_id = self.env['res.users'].search([('id', '=', self.env.uid)], limit=1)
        if user_id:
            return user_id
        return False
    
    memco_project_id = fields.Many2one('mrp.bom',string='Project')
    memco_lead_id = fields.Many2one('crm.lead',string='Lead')
    estimated_date = fields.Date()
    send_to_all = fields.Boolean()
    users = fields.Many2many('res.users',string='Users', default=_user_get)
    standard_project_id = fields.Many2one('mrp.bom',string='Standard Project')
    tag = fields.Selection([('machine','Machine'),('raw_material','Raw Material'),('services','Services')],string="Tag")
    account = fields.Many2one('account.account','Account')
    journal_id = fields.Many2one('account.journal', 'Account Journal')
    state = fields.Selection([
            ('draft', 'Draft Quotation'),
            ('sent', 'Quotation Sent'),
            ('cancel', 'Cancelled'),
            ('waiting_date', 'Waiting Schedule'),
            ('progress', 'Sales Order'),
            ('manual', 'Sale to Invoice'),
            ('shipping_except', 'Shipping Exception'),
            ('invoice_except', 'Invoice Exception'),
            ('done', 'Done'),('re_design', 'Re-Design'),('joborder_sent', 'Job Order sent'),
            ], 'Status', readonly=True, copy=False, help="Gives the status of the quotation or sales order.\
              \nThe exception status is automatically set when a cancel operation occurs \
              in the invoice validation (Invoice Exception) or in the picking list process (Shipping Exception).\nThe 'Waiting Schedule' status is set when the invoice is confirmed\
               but waiting for the scheduler to run on the order date.", select=True)
#    remain_qty = fields.Float(string='Remaining Qty')
#    qty_hand = fields.Float(string='On hand Qty')
#    in_way = fields.Float(string='In way Qty')



    @api.v7
    def _prepare_invoice(self, cr, uid, order, lines, context=None):
        """Prepare the dict of values to create the new invoice for a
           sales order. This method may be overridden to implement custom
           invoice generation (making sure to call super() to establish
           a clean extension chain).

           :param browse_record order: sale.order record to invoice
           :param list(int) line: list of invoice line IDs that must be
                                  attached to the invoice
           :return: dict of value to create() the invoice
        """
        if context is None:
            context = {}
        journal_ids = self.pool.get('account.journal').search(cr, uid,
            [('type', '=', 'sale'), ('company_id', '=', order.company_id.id)],
            limit=1)
        if not journal_ids:
            raise osv.except_osv(_('Error!'),
                _('Please define sales journal for this company: "%s" (id:%d).') % (order.company_id.name, order.company_id.id))
        invoice_vals = {
            'name': order.client_order_ref or '',
            'origin': order.name,
            'type': 'out_invoice',
            'reference': order.client_order_ref or order.name,
            'account_id': order.partner_invoice_id.property_account_receivable.id,
            'partner_id': order.partner_invoice_id.id,
            'journal_id': journal_ids[0],
            'invoice_line': [(6, 0, lines)],
            'currency_id': order.pricelist_id.currency_id.id,
            'comment': order.note,
            'payment_term': order.payment_term and order.payment_term.id or False,
            'fiscal_position': order.fiscal_position.id or order.partner_invoice_id.property_account_position.id,
            'date_invoice': context.get('date_invoice', False),
            'company_id': order.company_id.id,
            'user_id': order.user_id and order.user_id.id or False,
            'section_id' : order.section_id.id,
            'sale_id':order.id,
        }

        # Care for deprecated _inv_get() hook - FIXME: to be removed after 6.1
        invoice_vals.update(self._inv_get(cr, uid, order, context=context))
        return invoice_vals
    
    @api.one
    def button_get_bom_project(self):
        product = self.standard_project_id.product_tmpl_id.id
        qty = self.standard_project_id.product_qty
        uom = self.standard_project_id.product_uom.id
        if self.standard_project_id.sub_products:
            for line in self.standard_project_id.sub_products:
                sol_dir = {
                'product_id':line.product_id.id,
                'product_uom_qty':line.product_qty,
                'name':line.product_id.name,
                'order_id':self.id
                }
                create_id = self.env['sale.order.line'].create(sol_dir)
                self.order_line = [(4, 0, create_id)]
#        if not self.standard_project_id.sub_products:
#            sol_dir = {
#            'product_id':product,
#            'product_uom_qty':qty,
#            'name':self.standard_project_id.product_tmpl_id.name,
#            'order_id':self.id
#            }
#            create_id = self.env['sale.order.line'].create(sol_dir)
#            self.order_line = [(4, 0, create_id)]
        return True

    @api.one
    def action_button_re_design(self):
        self.write({ 'state' : 're_design', })
        self.memco_project_id.state = 're_design'
        self.memco_project_id.sub_tech_spe = False
        crm_case_obj = self.env['crm.case.stage']
        stage_id = crm_case_obj.search([('name', '=', 'Re-Design')])
        if self.memco_lead_id:
            self.memco_lead_id.stage_id = stage_id
        self.message_post(body=_("Please Re-Design"))
        return True
    
    @api.one
    def action_button_joborder_sent(self):
        if not self.send_to_all:
             raise Warning(_('Alert'),'Please Job Order Send to all')
        self.write({ 'state' : 'joborder_sent'})
        if self.memco_project_id:
            self.memco_project_id.state = 'joborder'
        crm_case_obj = self.env['crm.case.stage']
        stage_id = crm_case_obj.search([('name', '=', 'Job Order Sent')])
        if self.memco_lead_id:
            self.memco_lead_id.stage_id = stage_id
        self.message_post(body=_("Job Order send"))
        return True
        
        
    def action_sent(self, cr, uid, ids, context=None):
        context = context or {}
        for o in self.browse(cr, uid, ids):
            crm_case_obj = self.pool.get('crm.case.stage')
            lead_obj = self.pool.get('crm.lead')
            stage_id = crm_case_obj.search(cr,uid,[('name', '=', 'Quotation Sent')])[0]
            if o.memco_lead_id:
                lead_obj.write(cr, uid, o.memco_lead_id.id, {'stage_id': stage_id}, context=context)
            self.write(cr,uid,ids,{'state':'sent'})
            self.message_post(cr, uid, ids, body=_("Quotation sent to Customer"), context=context)
        return True

    def action_button_create_jobcard(self, cr, uid, ids, context=None):
        '''
        This function opens a window to compose an email, with the edi sale template message loaded by default
        '''
        assert len(ids) == 1, 'This option should only be used for a single id at a time.'
        ir_model_data = self.pool.get('ir.model.data')
        try:
            template_id = ir_model_data.get_object_reference(cr, uid, 'memco_project', 'email_template_department_jobcard')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference(cr, uid, 'mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False 
        ctx = dict()
        ctx.update({
            'default_model': 'sale.order',
            'default_res_id': ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True
        })
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
        
        
#    @api.multi
#    def action_button_confirm(self):
#        template_obj = self.env['email.template']
#        template_inst = template_obj.search([('name','=','Job card specification - Send by Email')])
#        template1 = self.env.ref('memco_project.email_template_department_jobcard')
##        template_id = template_obj.browse(cr, uid, template_inst)
#        print "users", self.users
#        if not self.users:
#            raise Warning("Please choose anyone Users")
#        for user in self.users:
##            if user.partner_id not in self.message_follower_ids:
##                self.message_subscribe([user.partner_id.id])
#            self.sudo().message_subscribe_users(user_ids=user.partner_id.id)
#            if user.partner_id:
#                print "user.partner_id", user.partner_id
#                print "template_inst", template_inst
#                template_inst.email_to = user.partner_id.email
#                action = template_obj.send_mail(template_inst)
#        if self.memco_project_id:
#            self.memco_project_id.state = 'joborder'
#        if self.memco_lead_id:
#            crm_case_obj = self.env['crm.case.stage']
#            stage_id = crm_case_obj.search([('name', '=', 'Quotation Sent')])
#            self.memco_lead_id.stage_id = stage_id
#        template1.send_mail(self.id, True)
#        return super(sale_order, self).action_button_confirm()

    @api.v7
    def action_button_confirm(self, cr, uid, ids, context=None):
        # fetch the users's partner_id and subscribe the partner to the sale order
        assert len(ids) == 1
        so_obj = self.browse(cr, uid, ids[0], context=context)
        users = so_obj.users
        template_obj = self.pool.get('email.template')
        template_inst = template_obj.search(cr,uid,[('name','=','Job card specification - Send by Email')])[0]
        template_id = template_obj.browse(cr, uid, template_inst)
        if not users:
            raise osv.except_osv(('Warning'), ('Please choose anyone Users'))
        for user in users:
            if user.partner_id not in so_obj.message_follower_ids:
                self.message_subscribe(cr, uid, ids, [user.partner_id.id], context=context)
        
            if user.partner_id:
                template_obj.write(cr, uid, template_inst, {'email_to':user.partner_id.email}, context=context)
                action = template_obj.send_mail(cr,uid, template_inst, so_obj.id, context)
        if so_obj.memco_project_id:
            self.pool.get('mrp.bom').write(cr,uid,so_obj.memco_project_id.id,{'state':'joborder'})
        if so_obj.memco_lead_id:
            crm_case_obj = self.pool.get('crm.case.stage')
            stage_id = crm_case_obj.search(cr,uid,[('name', '=', 'Quotation Sent')])[0]
            self.pool.get('crm.lead').write(cr,uid,so_obj.memco_lead_id.id,{'stage_id':stage_id})
            
#        self._ac_entry_project(cr,uid,ids,context=context)
        return super(sale_order, self).action_button_confirm(cr, uid, ids, context=context)

    @api.multi
    def _ac_entry_project(self):
#        property_account_receivable
#        account

        ctx = dict(self._context)
        ctx.update({'date': self.date_order})
        period_obj = self.env['account.period']
        currency_obj = self.env['res.currency']
        period_ids = period_obj.find(self.date_order)
        
        
        acc_move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        company_currency = self.company_id.currency_id
        current_currency = self.pricelist_id.currency_id
        amount = current_currency.compute(self.amount_total, company_currency)
        if not self.journal_id or not self.account:
            raise Warning(_('Alert'),'Please set Account / journal so accounting entry create')
        entry = {
        'journal_id':self.journal_id.id,
        'period_id':period_ids.id,
        'date':self.date_order,
        'ref':self.name,
        }
        if self.journal_id.type == 'sale':
            sign = 1
        else:
            sign = -1
            
        move_id = acc_move_obj.create(entry)
        data_credit ={
                'name': 'Project start entry',
                'ref': self.name,
                'move_id': move_id.id,
                'account_id': self.account.id,
                'debit': 0.0,
                'credit': amount,
                'period_id': period_ids.id and period_ids.id or False,
                'journal_id': self.journal_id.id,
                'partner_id': self.partner_id.id,
                'currency_id': company_currency.id <> current_currency.id and current_currency.id or False,
                'amount_currency': company_currency.id <> current_currency.id and -sign * self.amount_total or 0.0,
                'date': self.date_order,
            }
        
        data_debit = {
                'name': 'Project start entry',
                'ref': self.name,
                'move_id': move_id.id,
                'account_id': self.partner_id.property_account_receivable.id,
                'credit': 0.0,
                'debit': amount,
                'period_id': period_ids and period_ids.id or False,
                'journal_id': self.journal_id.id,
#                'partner_id': self.bank_id.id,
                'currency_id': company_currency.id <> current_currency.id and current_currency.id or False,
                'amount_currency': company_currency.id <> current_currency.id and sign * self.amount_total or 0.0,
                'date': self.date_order,
#                'analytic_account_id' : self.analytic_account_id.id
            }
        qw2=move_line_obj.create(data_debit)
        qw1 = move_line_obj.create(data_credit)
        print "qw2", qw2, qw1
        
#    def mail_send_to_pm(self, cr, uid, ids, context=None):
#        self_obj = self.browse(cr, uid, ids)[0]
#        template_obj = self.pool.get('email.template')
#        template_inst = template_obj.search(cr,uid,[('name','=','Detail send to PM - Send by Email')])[0]
#        template_id = template_obj.browse(cr, uid, template_inst)
#        try:
#            action = template_obj.send_mail(cr,uid, template_inst, self_obj.id, context)
#        except:
#            raise osv.except_osv(('Warning'), ('Not configure Email' ) )
#        return True
        
#    def _prepare_order_line_procurement(self, cr, uid, order, line, group_id=False, context=None):
#        """ create procurement here we add just two fields add quant_id and lot_id"""
##        super(sale_order,self)._prepare_order_line_procurement(cr, uid, order, line, group_id, context=context)
#        product_uom_obj = self.pool.get('product.uom')
#        print "line", line, line.product_id.name
#        date_planned = self._get_date_planned(cr, uid, order, line, order.date_order, context=context)
#        uom_record = product_uom_obj.browse(cr, uid, line.product_uom.id, context=context)
#        compare_qty = float_compare(line.product_id.virtual_available, line.product_uom_qty, precision_rounding=uom_record.rounding)
#        if compare_qty == -1:
#            template_obj = self.pool.get('email.template')
#            template_inst = template_obj.search(cr,uid,[('name','=','Detail send to PM - Send by Email')])[0]
#            template_id = template_obj.browse(cr, uid, template_inst)
#            action = template_obj.send_mail(cr,uid, template_inst,order.id, context)
#            print "action", action
##            self.message_post(cr, uid, order, body=_("%s produced") % self._description, context=context)
#            raise osv.except_osv(('Warning'),('Not Enaugh Stock please contact to Purchase Manager'))
#        res = {
#            'name': line.name,
#            'origin': order.name,
#            'date_planned': date_planned,
#            'product_id': line.product_id.id,
#            'product_qty': line.product_uom_qty,
#            'product_uom': line.product_uom.id,
#            'product_uos_qty': (line.product_uos and line.product_uos_qty) or line.product_uom_qty,
#            'product_uos': (line.product_uos and line.product_uos.id) or line.product_uom.id,
#            'company_id': order.company_id.id,
#            'group_id': group_id,
#            'invoice_state': (order.order_policy == 'picking') and '2binvoiced' or 'none',
#            'sale_line_id': line.id,
#        }
#        return res
#class sale_order_line(osv.osv):
#    _inherit = 'sale.order.line'
    
#    def product_id_change_with_wh(self, cr, uid, ids, pricelist, product, qty=0,
#            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
#            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, warehouse_id=False, context=None):
#        print "ids", ids, dir(self)
#        context = context or {}
#        print "context",context,context.get('field_parent', []),
#        product_uom_obj = self.pool.get('product.uom')
#        product_obj = self.pool.get('product.product')
#        warehouse_obj = self.pool['stock.warehouse']
#        warning = {}
#        #UoM False due to hack which makes sure uom changes price, ... in product_id_change
#        res = self.product_id_change(cr, uid, ids, pricelist, product, qty=qty,
#            uom=False, qty_uos=qty_uos, uos=uos, name=name, partner_id=partner_id,
#            lang=lang, update_tax=update_tax, date_order=date_order, packaging=packaging, fiscal_position=fiscal_position, flag=flag, context=context)

#        if not product:
#            res['value'].update({'product_packaging': False})
#            return res

#        #update of result obtained in super function
#        product_obj = product_obj.browse(cr, uid, product, context=context)
#        res['value'].update({'product_tmpl_id': product_obj.product_tmpl_id.id, 'delay': (product_obj.sale_delay or 0.0)})

#        # Calling product_packaging_change function after updating UoM
#        res_packing = self.product_packaging_change(cr, uid, ids, pricelist, product, qty, uom, partner_id, packaging, context=context)
#        res['value'].update(res_packing.get('value', {}))
#        warning_msgs = res_packing.get('warning') and res_packing['warning']['message'] or ''

#        if product_obj.type == 'product':
#            #determine if the product is MTO or not (for a further check)
#            isMto = False
#            if warehouse_id:
#                warehouse = warehouse_obj.browse(cr, uid, warehouse_id, context=context)
#                for product_route in product_obj.route_ids:
#                    if warehouse.mto_pull_id and warehouse.mto_pull_id.route_id and warehouse.mto_pull_id.route_id.id == product_route.id:
#                        isMto = True
#                        break
#            else:
#                try:
#                    mto_route_id = warehouse_obj._get_mto_route(cr, uid, context=context)
#                except:
#                    # if route MTO not found in ir_model_data, we treat the product as in MTS
#                    mto_route_id = False
#                if mto_route_id:
#                    for product_route in product_obj.route_ids:
#                        if product_route.id == mto_route_id:
#                            isMto = True
#                            break

#            #check if product is available, and if not: raise a warning, but do this only for products that aren't processed in MTO
#            if not isMto:
#                uom_record = False
#                if uom:
#                    uom_record = product_uom_obj.browse(cr, uid, uom, context=context)
#                    if product_obj.uom_id.category_id.id != uom_record.category_id.id:
#                        uom_record = False
#                if not uom_record:
#                    uom_record = product_obj.uom_id
#                compare_qty = float_compare(product_obj.virtual_available, qty, precision_rounding=uom_record.rounding)
#                if compare_qty == -1:
#                    warn_msg = _('You plan to sell %.2f %s but you only have %.2f %s available !\nThe real stock is %.2f %s. (without reservations)') % \
#                        (qty, uom_record.name,
#                         max(0,product_obj.virtual_available), uom_record.name,
#                         max(0,product_obj.qty_available), uom_record.name)
#                    warning_msgs += _("Not enough stock ! : ") + warn_msg + "\n\n"

#        #update of warning messages
#        if warning_msgs:
#            template_obj = self.pool.get('email.template')
#            template_inst = template_obj.search(cr,uid,[('name','=','Detail send to PM - Send by Email')])[0]
#            template_id = template_obj.browse(cr, uid, template_inst)
#            print "template_inst", template_inst, product_obj.id
#            action = template_obj.send_mail(cr,uid, template_inst,product_obj.id, context)
#            print "\n\naction", action
#            warning = {
#                       'title': _('Configuration Error!'),
#                       'message' : warning_msgs
#                    }
#        res.update({'warning': warning})
#        return res


