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

from openerp.osv import fields, osv
from openerp import models, fields, api, _

from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

class account_invoice(models.Model):

    _name = 'account.invoice'
    _inherit = 'account.invoice'
    
    @api.one#order_line.price_subtotal','amount_tax','amount_total','amount_untaxed','disc_amt'
    @api.depends('invoice_line.price_subtotal', 'tax_line.amount','amount_total','amount_untaxed','disc_amt')
    def _compute_amount(self):
        self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line)
        self.amount_tax = sum(line.amount for line in self.tax_line)
        self.amount_total = self.amount_untaxed + self.amount_tax - self.discount_amt
        
    @api.onchange('disc_method','disc_amt','amount_untaxed')
    def _onchange_amt_discount(self):
        if self.disc_method == 'per':
            self.discount_amt = (self.amount_untaxed * self.disc_amt)/100
            self.amount_total = self.amount_untaxed - self.discount_amt
        else:
            self.discount_amt = self.disc_amt
            self.amount_total = self.amount_untaxed - self.discount_amt
            
    @api.multi
    def action_move_create(self):
    
        res = super(account_invoice, self).action_move_create()
        print "res:>>>", res
        if self.sale_id:
            ctx = dict(self._context)
            ctx.update({'date': self.date_invoice})
            period_obj = self.env['account.period']
            currency_obj = self.env['res.currency']
            period_ids = period_obj.find(self.date_invoice)
            
            
            acc_move_obj = self.env['account.move']
            move_line_obj = self.env['account.move.line']
            company_currency = self.company_id.currency_id
            print "company_currency", company_currency.name
            current_currency = self.sale_id.pricelist_id.currency_id or False
            amount = current_currency.compute(self.amount_total, company_currency)
            entry = {
            'journal_id':self.journal_id.id,
            'period_id':period_ids.id,
            'date':self.date_invoice,
            'ref':self.number,
            }
            if self.sale_id.journal_id.type == 'sale':
                sign = 1
            else:
                sign = -1
            move_id = acc_move_obj.create(entry)
            print "move_id", move_id
            data_credit ={
                    'name': 'Project Close entry',
                    'ref': self.name,
                    'move_id': move_id.id,
                    'account_id': self.partner_id.property_account_receivable.id,
                    'debit': 0.0,
                    'credit': amount,
                    'period_id': period_ids.id and period_ids.id or False,
                    'journal_id': self.journal_id.id,
                    'partner_id': self.partner_id.id,
                    'currency_id': company_currency.id <> current_currency.id and current_currency.id or False,
                    'amount_currency': company_currency.id <> current_currency.id and -sign * self.amount_total or 0.0,
                    'date': self.date_invoice,
                }
            print "data_credit :>", data_credit
            
            data_debit = {
                    'name': 'Project start entry',
                    'ref': self.name,
                    'move_id': move_id.id,
                    'account_id': self.sale_id.account.id,
                    'credit': 0.0,
                    'debit': amount,
                    'period_id': period_ids and period_ids.id or False,
                    'journal_id': self.journal_id.id,
    #                'partner_id': self.bank_id.id,
                    'currency_id': company_currency.id <> current_currency.id and current_currency.id or False,
                    'amount_currency': company_currency.id <> current_currency.id and sign * self.amount_total or 0.0,
                    'date': self.date_invoice,
    #                'analytic_account_id' : self.analytic_account_id.id
                }
            print "data_debit :>", data_debit
            qw2=move_line_obj.create(data_debit)
            qw1 = move_line_obj.create(data_credit)
            print "sdsds",qw2,qw1
    
    
    tag = fields.Selection([('machine','Machine'),('raw_material','Raw Material'),('services','Services')],string="Tag")
    disc_method = fields.Selection([('per','Percentage'),('fix','Fixed')], 'Discount Method',
                             states={'confirmed': [('readonly',True)],
                                     'approved': [('readonly',True)],
                                     'done': [('readonly',True)]})
    disc_amt = fields.Float('Discount Amount',
                             states={'confirmed': [('readonly',True)],
                                     'approved': [('readonly',True)],
                                     'done': [('readonly',True)]})
    discount_amt = fields.Float(string='-Discount',help="The additional discount on untaxed amount.")
    sale_id = fields.Many2one('sale.order',string="Sale Order")
    
    
class account_invoice_line(models.Model):
    _inherit = 'account.invoice.line'
    
    @api.multi
    def _amount_line_disc(self):
        for line in self:
            if line.line_discount:
                line.price_nettotal = line.price_subtotal - line.line_discount
            else:
                line.price_nettotal = line.price_subtotal

    @api.multi
    @api.depends('invoice_id.discount_amt')
    def _compute_line_discount(self):
        for line in self:
            if line.price_subtotal:
                invoice_dicount_amt = line.invoice_id.discount_amt
                invoice_total_amt = line.invoice_id.amount_untaxed
                discount_perc = (line.price_subtotal * 100) / invoice_total_amt
                line_discount = (invoice_dicount_amt * discount_perc)/100
                line.line_discount = line_discount
    
    line_discount = fields.Float(compute= '_compute_line_discount',string='Discount')
    price_nettotal = fields.Float(compute='_amount_line_disc', string='Net Total', digits_compute= dp.get_precision('Account'))
