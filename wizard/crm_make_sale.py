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
from openerp.tools.translate import _

class new_project_line(osv.osv_memory):

    _name = "new.project.line"
    _columns = {
        'product_id': fields.many2one('product.template', 'Product', required=True),
        'qty':fields.float(string="Quantity"),
        'price':fields.float(string='Price'),
        'line_id':fields.many2one('crm.make.sale', 'line'),
        
    }

class crm_make_sale(osv.osv_memory):
    """ Make sale  order for crm """

    _inherit = "crm.make.sale"

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res = super(crm_make_sale, self).default_get(cr, uid, fields, context=context)
        active_ids = context.get('active_ids',[])
        pick = self.pool.get('crm.lead').browse(cr, uid, context['active_id'], context=context)
        pickk = []
        for p in pick.bom_ids:

            pickk.append((0, 0, {
                'product_id':p.product_tmpl_id.id,
                'qty':p.product_qty,
                'lead_id':active_ids
            }))
#        if 'partner_id' in fields:
#            res.update({'partner_id': pick.carrier_id.partner_id.id})
#        if 'ref' in fields:
#            res.update({'ref': pick.origin})
        print "fields", fields
        if 'line_id' in fields:
            res.update({'line_id': pickk})
        if 'memco_project_id' in fields and pick.bom_ids:
            res.update({'memco_project_id': pick.bom_ids[0].id or False})
        if 'memco_lead_id' in fields:
            res.update({'memco_lead_id': pick.id})
        print "Res:.....", res
        return res

    def makeOrder(self, cr, uid, ids, context=None):
        """
        This function  create Quotation on given case.
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of crm make sales' ids
        @param context: A standard dictionary for contextual values
        @return: Dictionary value of created sales order.
        """
        # update context: if come from phonecall, default state values can make the quote crash lp:1017353
        context = dict(context or {})
        context.pop('default_state', False)
        
        case_obj = self.pool.get('crm.lead')
        sale_obj = self.pool.get('sale.order')
        partner_obj = self.pool.get('res.partner')
        data = context and context.get('active_ids', []) or []

        for make in self.browse(cr, uid, ids, context=context):
            partner = make.partner_id
            partner_addr = partner_obj.address_get(cr, uid, [partner.id],
                    ['default', 'invoice', 'delivery', 'contact'])
            pricelist = partner.property_product_pricelist.id
            fpos = partner.property_account_position and partner.property_account_position.id or False
            payment_term = partner.property_payment_term and partner.property_payment_term.id or False
            new_ids = []
            ppick = []
            print "make.line_id", make.line_id
            for a in make.line_id:
                print "a.product_id", a.product_id
                pro = self.pool.get('product.product').search(cr,uid,[('product_tmpl_id','=',a.product_id.id)])[0]
                print "@@@@@@@@Product :>.....................", pro
                ppick.append((0, False, {
                    'product_id':pro,
                    'product_uom_qty':a.qty,
                    'name':a.product_id.name,
                }))

            for case in case_obj.browse(cr, uid, data, context=context):
                if not partner and case.partner_id:
                    partner = case.partner_id
                    fpos = partner.property_account_position and partner.property_account_position.id or False
                    payment_term = partner.property_payment_term and partner.property_payment_term.id or False
                    partner_addr = partner_obj.address_get(cr, uid, [partner.id],
                            ['default', 'invoice', 'delivery', 'contact'])
                    pricelist = partner.property_product_pricelist.id
                if False in partner_addr.values():
                    raise osv.except_osv(_('Insufficient Data!'), _('No address(es) defined for this customer.'))

                vals = {
                    'origin': _('Opportunity: %s') % str(case.id),
                    'section_id': case.section_id and case.section_id.id or False,
                    'categ_ids': [(6, 0, [categ_id.id for categ_id in case.categ_ids])],
                    'partner_id': partner.id,
                    'pricelist_id': pricelist,
                    'partner_invoice_id': partner_addr['invoice'],
                    'partner_shipping_id': partner_addr['delivery'],
                    'date_order': fields.datetime.now(),
                    'fiscal_position': fpos,
                    'payment_term':payment_term,
                    'order_line':ppick,
                    'memco_project_id':make.memco_project_id.id,
                    'memco_lead_id':make.memco_lead_id.id,
                }
                if partner.id:
                    vals['user_id'] = partner.user_id and partner.user_id.id or uid
                print "@@@@@@vals:>>", vals
                new_id = sale_obj.create(cr, uid, vals, context=context)
                sale_order = sale_obj.browse(cr, uid, new_id, context=context)
                case_obj.write(cr, uid, [case.id], {'ref': 'sale.order,%s' % new_id})
                new_ids.append(new_id)
                print "new_ids", new_ids
                message = _("Opportunity has been <b>converted</b> to the quotation <em>%s</em>.") % (sale_order.name)
                case.message_post(body=message)
#            if make.close:
#                case_obj.case_mark_won(cr, uid, data, context=context)
            crm_case_obj = self.pool.get('crm.case.stage')
            stage_id = crm_case_obj.search(cr,uid,[('name', '=', 'Quotation Ready')])[0]
            print "stage_id",stage_id, make.memco_lead_id
            self.pool.get('crm.lead').write(cr, uid, make.memco_lead_id.id, {'stage_id': stage_id}, context=context)
#            self.pool.get('crm.lead').write(cr, uid, make.memco_lead_id.id,{'stage_id':stage_id})
            if not new_ids:
                return {'type': 'ir.actions.act_window_close'}
            if len(new_ids)<=1:
                value = {
                    'domain': str([('id', 'in', new_ids)]),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'sale.order',
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'name' : _('Quotation'),
                    'res_id': new_ids and new_ids[0]
                }
            else:
                value = {
                    'domain': str([('id', 'in', new_ids)]),
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'sale.order',
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'name' : _('Quotation'),
                    'res_id': new_ids
                }
            return value
    _columns = {
        'line_id':fields.one2many('new.project.line','line_id',string="Line"),
        'memco_project_id':fields.many2one('mrp.bom', 'Project'),
        'memco_lead_id':fields.many2one('crm.lead', 'Lead'),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
