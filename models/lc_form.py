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
from datetime import date
import time
from datetime import timedelta
from datetime import datetime
from openerp import models, fields, api, _
from openerp.tools import float_compare
from openerp.osv import osv
from openerp.addons import crm
from openerp.exceptions import Warning


class memco_lc_shipping(models.Model):
    """
    """
    _name = 'memco.lc.shipping'
    name = fields.Char('Name')
    notes = fields.Text('Description')

class lc_entry(models.Model):
    """
    """
    _name = 'lc.entry'
    name = fields.Char('Name')
    cost_type = fields.Selection([('not_cost','Not Cost'),('cost','Cost')],'Cost Type')
    account = fields.Many2one('account.account','Bank Account')
    entry_date = fields.Datetime()
    credit = fields.Float('Amount')
    local_amount = fields.Float('Local Amount')
    lc_id = fields.Many2one('memco.lcform')
    due_date = fields.Datetime()
    state = fields.Selection([('draft','Draft'),('account','Accounted')])
    
    @api.one
    #this method will convert the LC Amount in Local Currency from Supplier Currency
    @api.onchange('credit')
    def _compute_currancy_entry(self):
        lc = self.lc_id
        ctx = dict(self._context)
        ctx.update({'date': lc.lc_date})
        amount_to_convert = self.credit
        supplier_currency = lc.supplier_currency
        to_currency_id = lc.local_currency.id
        coverted_amount = 0.0
        currency_obj = self.env['res.currency']
        data_obj = self.env['ir.model.data']
        if supplier_currency and supplier_currency.id != to_currency_id:
            to_currency = currency_obj.browse(to_currency_id)
            rate = currency_obj._get_conversion_rate(supplier_currency, to_currency, context=ctx)
            coverted_amount = rate * amount_to_convert
            self.local_amount = coverted_amount
        elif supplier_currency.id == to_currency_id:
            self.local_amount = self.credit
    @api.one
    def ac_lc_entry(self):
        lc = self.lc_id
        ctx = dict(self._context)
        ctx.update({'date': lc.lc_date})
        period_obj = self.env['account.period']
        currency_obj = self.env['res.currency']
        period_ids = period_obj.find(lc.lc_date)
        
        
        acc_move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        company_currency = lc.local_currency
        current_currency = lc.supplier_currency
        entry = {
        'journal_id':lc.journal_id.id,
        'period_id':period_ids.id,
        'date':lc.lc_date,
        'ref':lc.lc_no,
        }
        if lc.journal_id.type == 'purchase':
            sign = 1
        else:
            sign = -1
            
        move_id = acc_move_obj.create(entry)
        print "move_id", move_id
        data_credit ={
                'name': 'LC ENTRY',
                'ref': lc.lc_no,
                'move_id': move_id.id,
                'account_id': lc.journal_id.default_credit_account_id.id,
                'debit': 0.0,
                'credit': self.local_amount if company_currency.id <> current_currency.id else self.credit,
                'period_id': period_ids.id and period_ids.id or False,
                'journal_id': lc.journal_id.id,
                'partner_id': lc.supplier.id,
                'currency_id': company_currency.id <> current_currency.id and current_currency.id or False,
#                'amount_currency': company_currency.id <> current_currency.id and self.total_not_cost or 0.0,
                'date': lc.lc_date,
            }
        print "data_credit", data_credit
        
        data_debit = {
                'name': 'LC ENTRY',
                'ref': lc.lc_no,
                'move_id': move_id.id,
                'account_id': lc.lc_account.id,
                'credit': 0.0,
                'debit': self.local_amount if company_currency.id <> current_currency.id else self.credit,
                'period_id': period_ids and period_ids.id or False,
                'journal_id': lc.journal_id.id,
#                'partner_id': self.bank_id.id,
                'currency_id': company_currency.id <> current_currency.id and current_currency.id or False,
#                'amount_currency': company_currency.id <> current_currency.id and self.total_not_cost or 0.0,
                'date': lc.lc_date,
#                'analytic_account_id' : self.analytic_account_id.id
            }
        qw2=move_line_obj.create(data_debit)
        qw1 = move_line_obj.create(data_credit)
        self.state = 'account'

class memco_lcform(models.Model):
    """
    """
    _name = 'memco.lcform'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = 'lc_no'
    _rec_name = 'lc_no'
    
    
#    @api.one
#    def _get_default_currency(self):
#        res = self.env['res.company'].search([('currency_id','=',self.company_id.id)])
#        return res and res[0] or False 
    @api.depends('total_cost_sar','total_not_cost_sar')
    def _calculate_amount(self):
        self.total_close_amount = self.total_cost_sar + self.total_not_cost_sar
    
    
    lc_no = fields.Char('LC No', required='1')
    po_no = fields.Many2one('purchase.order', 'PO No',required=True)
    supplier_amount = fields.Float(copy=False, string="LC amount")
    amount = fields.Float('Amount', copy=False)
    project = fields.Char('Project')#,required=True
    supplier_currency = fields.Many2one('res.currency','Supplier Currency')
    local_currency = fields.Many2one('res.currency', 'Company Currency',default=lambda self: self.env.user.company_id.currency_id)
    supplier = fields.Many2one('res.partner','Supplier', required=True)
    lc_account = fields.Many2one('account.account','LC Account', required=True)
    journal_id =  fields.Many2one('account.journal', 'Destination Journal', required=True)
    closed_journal_id =  fields.Many2one('account.journal', 'Closed Entry Journal')
    create_date = fields.Datetime(default=lambda self:time.strftime('%Y-%m-%d'))
    expiry_date = fields.Datetime()
    shipping_date = fields.Date()
    lc_date = fields.Datetime(default=lambda self:time.strftime('%Y-%m-%d'))
    shipping_method = fields.Many2one('memco.lc.shipping', 'Shipping Method')
    user_id = fields.Many2one('res.users', 'Users', readonly='1', default=lambda self: self.env.user)
    notes = fields.Text(placeholder="Description")
    bank = fields.Many2one('res.bank', 'Bank')
    state = fields.Selection([('new','New'),('open','Open'),('notclose','Not Close'),('close','Close')],string='Stage', default='new')
    total_cost = fields.Float('Total Cost')
    total_not_cost = fields.Float('Total Not Cost')
    total_cost_sar = fields.Float('Total Cost in SAR')
    total_not_cost_sar = fields.Float('Total Not Cost in SAR')
    total_close_amount = fields.Float('Total Closeing Amount',compute=_calculate_amount)#for close entry in journal
    cost_entry = fields.One2many('lc.entry','lc_id', 'Cost Entry')
    first_payment = fields.Float(default='20.00')
    second_payment = fields.Float(default='80.00')
    third_payment = fields.Float()
    f_remain = fields.Float(compute='_get_remain_payment')
    s_remain = fields.Float(compute='_get_remain_payment')
    t_remain = fields.Float(compute='_get_remain_payment')
    
    match_cost = fields.Boolean(compute='check_cost_close')
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    company_id= fields.Many2one(related='user_id.company_id',
                            string='Company',readonly=True)
    
    
    
        
        
    @api.one
    @api.onchange('cost_entry')
    def _get_total_cost(self):
        a = []
        for amt in self.cost_entry:
            if amt.cost_type == 'cost':
                a.append(amt.credit)
        self.total_cost = sum(a)

    @api.one
    @api.onchange('cost_entry')
    def _get_total_not_cost(self):
        a = []
        for amt in self.cost_entry:
            if amt.cost_type == 'not_cost':
                a.append(amt.credit)
        self.total_not_cost = sum(a)
        
    @api.one
    #this method will convert the LC total cost in company Currency from Supplier Currency
    @api.onchange('total_cost')
    def _compute_currancy_total_cost(self):
        ctx = dict(self._context)
        ctx.update({'date': self.lc_date})
        amount_to_convert = self.total_cost
        supplier_currency = self.supplier_currency
        to_currency_id = self.local_currency.id
        coverted_amount = 0.0
        currency_obj = self.env['res.currency']
        data_obj = self.env['ir.model.data']
        if supplier_currency and supplier_currency.id != to_currency_id:
            to_currency = currency_obj.browse(to_currency_id)
            rate = currency_obj._get_conversion_rate(supplier_currency, to_currency, context=ctx)
            coverted_amount = rate * amount_to_convert
            self.total_cost_sar = coverted_amount
        elif supplier_currency.id == to_currency_id:
            self.total_cost_sar = self.total_cost
    @api.one
    #this method will convert the LC total not cost in Company Currency from Supplier Currency
    @api.onchange('total_not_cost')
    def _compute_currancy_total_notcost(self):
        ctx = dict(self._context)
        ctx.update({'date': self.lc_date})
        amount_to_convert = self.total_not_cost
        supplier_currency = self.supplier_currency
        to_currency_id = self.local_currency.id
        coverted_amount = 0.0
        currency_obj = self.env['res.currency']
        data_obj = self.env['ir.model.data']
        if supplier_currency and supplier_currency.id != to_currency_id:
            to_currency = currency_obj.browse(to_currency_id)
            rate = currency_obj._get_conversion_rate(supplier_currency, to_currency, context=ctx)
            coverted_amount = rate * amount_to_convert
            self.total_not_cost_sar = coverted_amount
        elif supplier_currency.id == to_currency_id:
            self.total_not_cost_sar = self.total_not_cost
    @api.one
    #this method will convert the LC Amount in Local Currency from Supplier Currency
    @api.onchange('po_no','supplier_amount')
    def _compute_currancy(self):
        ctx = dict(self._context)
        ctx.update({'date': self.lc_date})
        amount_to_convert = self.supplier_amount
        supplier_currency = self.supplier_currency
        to_currency_id = self.local_currency.id
        coverted_amount = 0.0
        currency_obj = self.env['res.currency']
        data_obj = self.env['ir.model.data']
        if supplier_currency and supplier_currency.id != to_currency_id:
            to_currency = currency_obj.browse(to_currency_id)
            rate = currency_obj._get_conversion_rate(supplier_currency, to_currency, context=ctx)
            coverted_amount = rate * amount_to_convert
            self.amount = coverted_amount
        elif supplier_currency.id == to_currency_id:
            self.amount = self.supplier_amount
            
    @api.one
    def check_cost_close(self):
        if self.supplier_amount == self.total_not_cost:
            self.match_cost = True
        else:
            self.match_cost = False

    @api.onchange('po_no','amount')
    def _onchange_po(self):
        self.supplier_amount = self.po_no.amount_total
        self.supplier = self.po_no.partner_id.id
        self.project = self.po_no.pr_name
        self.supplier_currency = self.po_no.currency_id.id

    @api.one
    def _get_remain_payment(self):
        self.f_remain = (self.supplier_amount*self.first_payment)/100
        self.s_remain = (self.supplier_amount*self.second_payment)/100
        self.t_remain = (self.supplier_amount*self.third_payment)/100

    @api.multi
    def button_approval(self):
        self.state = 'open'

    @api.one
    def button_closed(self):
        ctx = dict(self._context)
        ctx.update({'date': self.lc_date})
        period_obj = self.env['account.period']
        currency_obj = self.env['res.currency']
        period_ids = period_obj.find(self.lc_date)
        print " Period_ids :>>>>>",period_ids
        
        company_currency = self.company_id.currency_id
        current_currency = self.supplier_currency
#        current_currency = self.supplier_currency
#        company_currency = self.company_id.currency_id
#        company_currency = self.company_id.currency_id
#        amount = current_currency.compute(self.supplier_amount, company_currency)
#        print "A`M`O`U`N`T :>>>>>", amount
        acc_move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        if not self.closed_journal_id:
            raise Warning('Please define Closed Journal')
        entry = {
        'journal_id':self.closed_journal_id.id,
        'period_id':period_ids.id,
        'date':self.lc_date,
        'ref':self.lc_no,
        }
        if self.journal_id.type == 'purchase':
            sign = 1
        else:
            sign = -1
                
        print "self.analytic_account_id", self.analytic_account_id
        move_id = acc_move_obj.create(entry)
        print "move_id", move_id
        data_credit ={
                'name': 'LC ENTRY',
                'ref': self.lc_no,
                'move_id': move_id.id,
                'account_id': self.journal_id.default_credit_account_id.id,
                'debit': self.total_close_amount,
                'credit':0.0,
                'period_id': period_ids.id and period_ids.id or False,
                'journal_id': self.journal_id.id,
                'partner_id': self.supplier.id,
                'currency_id': company_currency.id <> current_currency.id and current_currency.id or False,
#                'amount_currency': company_currency.id <> current_currency.id and self.total_not_cost or 0.0,
                'date': self.lc_date,
            }
        print "data_credit", data_credit
        
        data_debit = {
                'name': 'LC ENTRY',
                'ref': self.lc_no,
                'move_id': move_id.id,
                'account_id': self.lc_account.id,
                'credit': self.total_close_amount,
                'debit': 0.0,
                'period_id': period_ids and period_ids.id or False,
                'journal_id': self.journal_id.id,
#                'partner_id': self.bank_id.id,
                'currency_id': company_currency.id <> current_currency.id and current_currency.id or False,
#                'amount_currency': company_currency.id <> current_currency.id and self.total_not_cost or 0.0,
                'date': self.lc_date,
#                'analytic_account_id' : self.analytic_account_id.id
            }
        qw2=move_line_obj.create(data_debit)
        qw1 = move_line_obj.create(data_credit)
        
        #total cost value set in incoming shipment
        
        pick_obj = self.env['stock.picking']
        inids = pick_obj.search([('origin','=',self.po_no.name),('state','!=','done')])
        print "inids:>>>", inids
        for a in inids:
            a.write({'lc_cost':self.total_cost})
        
        self.write({'state':'close'})
        
        
    def run_cron_expiry_lcform(self, cr, uid, automatic=False, use_new_cursor=False, context=None):

        model_obj = self.pool.get('ir.model.data')
        res_obj = self.pool.get('res.groups')
        view_model, m_id = model_obj.get_object_reference(cr, uid, 'account', 'group_account_manager')
        now = datetime.now().strftime("%Y-%m-%d")
        now1 = datetime.strptime(now, "%Y-%m-%d")
        inf = now1 - timedelta(days=8)
        inform_date = inf.strftime('%Y-%m-%d')
        get_ids = self.search(cr, uid, [('shipping_date','=',inform_date)], context=context)
        print "get_ids", get_ids
        
        m_data = res_obj.browse(cr, uid, m_id)
        manager_list = []
        for user in m_data.users:
           manager_list.append(user.partner_id.id)
        for a in get_ids:
            lc_data = self.browse(cr, uid, a)
            self.message_post(cr, uid, a, 
                          body = _("Dear Sir, <br/><br/> LC FORM : %s.\
                           and Shipping date is %s." %(lc_data.lc_no,lc_data.shipping_date)) ,
                          type = 'comment',
                          subtype = "mail.mt_comment",context = context,
                          model = 'memco.lcform', res_id = lc_data.id, 
                          partner_ids = manager_list)
        #Send the message to all Budget Control Manager for reminder of PO Approval
#        print "\nget_ids", get_ids
#        template_obj = self.pool.get('email.template')
#        template_inst = template_obj.search(cr,uid,[('name','=','Expiry date for Shipment in LC - Send by Email')])[0]
#        print "template_inst", template_inst
#        template_id = template_obj.browse(cr, uid, template_inst)
#        for data in self.browse(cr,uid,get_ids):
#            print "data:>>>", data, data.owner_id.email
#            template_obj.write(cr, uid, template_inst, {'email_to':data.owner_id.email}, context=context)
#            action = template_obj.send_mail(cr,uid, template_inst, data.id, context)
        return True


        
