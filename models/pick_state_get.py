from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time
import logging
from openerp import pooler
from openerp import models, fields as new_fields, api
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
import openerp.addons.decimal_precision as dp
from openerp import netsvc

_logger = logging.getLogger(__name__)

#class stock_picking_type(osv.osv):

#    _inherit = 'stock.picking.type'
#    _name = 'stock.picking.type'

#    def _get_picking_count(self, cr, uid, ids, field_names, arg, context=None):
#        obj = self.pool.get('stock.picking')
#        domains = {
#            'count_picking_draft': [('state', '=', 'draft')],
#            'count_picking_waiting': [('state', '=', 'confirmed')],
#            'count_picking_ready': [('state', 'in', ('assigned', 'partially_available'))],
#            'count_picking': [('state', 'in', ('assigned', 'waiting', 'confirmed', 'partially_available'))],
#            'count_picking_late': [('min_date', '<', time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)), ('state', 'in', ('assigned', 'waiting', 'confirmed', 'partially_available'))],
#            'count_picking_backorders': [('backorder_id', '!=', False), ('state', 'in', ('confirmed', 'assigned', 'waiting', 'partially_available'))],
#            'count_ready_shipping': [('state', '=', 'ready_to_shipping')],
#            'count_shipping_process': [('state', '=', 'shipping_process')],
#        }
#        result = {}
#        for field in domains:
#            data = obj.read_group(cr, uid, domains[field] +
#                [('state', 'not in', ('done', 'cancel')), ('picking_type_id', 'in', ids)],
#                ['picking_type_id'], ['picking_type_id'], context=context)
#            count = dict(map(lambda x: (x['picking_type_id'] and x['picking_type_id'][0], x['picking_type_id_count']), data))
#            for tid in ids:
#                result.setdefault(tid, {})[field] = count.get(tid, 0)
#        for tid in ids:
#            if result[tid]['count_picking']:
#                result[tid]['rate_picking_late'] = result[tid]['count_picking_late'] * 100 / result[tid]['count_picking']
#                result[tid]['rate_picking_backorders'] = result[tid]['count_picking_backorders'] * 100 / result[tid]['count_picking']
#            else:
#                result[tid]['rate_picking_late'] = 0
#                result[tid]['rate_picking_backorders'] = 0
#        return result

#    _columns = {
#    'count_shipping_process': fields.function(_get_picking_count,
#            type='integer', multi='_get_picking_count'),
#    'count_ready_shipping': fields.function(_get_picking_count,
#            type='integer', multi='_get_picking_count'),
#    }




class stock_picking(osv.osv):

    _inherit = 'stock.picking'
    _name = 'stock.picking'
    
    
    @api.v7
    def _state_get(self, cr, uid, ids, field_name, arg, context=None):
        '''The state of a picking depends on the state of its related stock.move
            draft: the picking has no line or any one of the lines is draft
            done, draft, cancel: all lines are done / draft / cancel
            confirmed, waiting, assigned, partially_available depends on move_type (all at once or partial)
        '''
        res = {}
        for pick in self.browse(cr, uid, ids, context=context):
            if (not pick.move_lines) or any([x.state == 'draft' for x in pick.move_lines]):
                res[pick.id] = 'draft'
                continue
            if all([x.state == 'cancel' for x in pick.move_lines]):
                res[pick.id] = 'cancel'
                continue
            if all([x.state in ('cancel', 'done') for x in pick.move_lines]):
                res[pick.id] = 'done'
                continue

            order = {'confirmed': 0, 'waiting': 1, 'assigned': 2, 'ready_to_shipping': 3, 'shipping_process': 4}#probuse
                                   
            order_inv = {0: 'confirmed', 1: 'waiting', 2: 'assigned',3: 'ready_to_shipping',4: 'shipping_process'}#probuse
            lst = [order[x.state] for x in pick.move_lines if x.state not in ('cancel', 'done')]
            if pick.move_type == 'one':
                res[pick.id] = order_inv[min(lst)]
            else:
                #we are in the case of partial delivery, so if all move are assigned, picking
                #should be assign too, else if one of the move is assigned, or partially available, picking should be
                #in partially available state, otherwise, picking is in waiting or confirmed state
                res[pick.id] = order_inv[max(lst)]
                if not all(x == 2 for x in lst):
                    if any(x == 2 for x in lst):
                        res[pick.id] = 'partially_available'
                    else:
                        #if all moves aren't assigned, check if we have one product partially available
                        for move in pick.move_lines:
                            if move.partially_available:
                                res[pick.id] = 'partially_available'
                                break
        return res

    def _get_pickings(self, cr, uid, ids, context=None):
        res = set()
        for move in self.browse(cr, uid, ids, context=context):
            if move.picking_id:
                res.add(move.picking_id.id)
        return list(res)

    _columns = {
        'state': fields.function(_state_get, type="selection", copy=False,
            store={
                'stock.picking': (lambda self, cr, uid, ids, ctx: ids, ['move_type'], 20),
                'stock.move': (_get_pickings, ['state', 'picking_id', 'partially_available'], 20)},
            selection=[
                ('draft', 'Draft'),
                ('cancel', 'Cancelled'),
                ('waiting', 'Waiting Another Operation'),
                ('confirmed', 'Waiting Availability'),
                ('partially_available', 'Partially Available'),
                ('assigned', 'Ready to Transfer'),
                ('ready_to_shipping','Ready To Shipping'),
                ('shipping_process','Shipping Process'),
                ('done', 'Transferred'),
                ], string='Status', readonly=True, select=True, track_visibility='onchange',
            help="""
                * Draft: not confirmed yet and will not be scheduled until confirmed\n
                * Waiting Another Operation: waiting for another move to proceed before it becomes automatically available (e.g. in Make-To-Order flows)\n
                * Waiting Availability: still waiting for the availability of products\n
                * Partially Available: some products are available and reserved\n
                * Ready to Transfer: products reserved, simply waiting for confirmation.\n
                * Transferred: has been processed, can't be modified or cancelled anymore\n
                * Cancelled: has been cancelled, can't be confirmed anymore"""
        ),
        'notification_date': fields.date('Notification Date')
    }

    def do_shipping_process(self, cr, uid, ids, context=None):
        """ state=Accepted and probability=100 """
        move_obj = self.pool.get('stock.move')
        picking_ids = self.browse(cr,uid,ids,context=context)
        for p in picking_ids.move_lines:
            move_obj.write(cr,uid,p.id,{'state':'shipping_process'})
        self.write(cr,uid,ids,{'state':'shipping_process','description':'BAAAAAAAAAAAAAAA'})
        return True
#        
    def do_ready_shipping(self, cr, uid, ids, context=None):
        """ state=Accepted and probability=100 """
        move_obj = self.pool.get('stock.move')
        picking_ids = self.browse(cr,uid,ids,context=context)
        for p in picking_ids.move_lines:
            move_obj.write(cr,uid,p.id,{'state':'ready_to_shipping'})
        self.write(cr,uid,ids,{'state':'ready_to_shipping','description':'adadasdasdasdasd'})
        return True
        
    @api.cr_uid_ids_context
    def do_transfer(self, cr, uid, picking_ids, context=None):
        """
            If no pack operation, we do simple action_done of the picking
            Otherwise, do the pack operations
        """
        if not context:
            context = {}
        stock_move_obj = self.pool.get('stock.move')
        for picking in self.browse(cr, uid, picking_ids, context=context):
            if not picking.pack_operation_ids:
                self.action_done(cr, uid, [picking.id], context=context)
                continue
            else:
                need_rereserve, all_op_processed = self.picking_recompute_remaining_quantities(cr, uid, picking, context=context)
                #create extra moves in the picking (unexpected product moves coming from pack operations)
                todo_move_ids = []
                if not all_op_processed:
                    todo_move_ids += self._create_extra_moves(cr, uid, picking, context=context)

                #split move lines if needed
                toassign_move_ids = []
                for move in picking.move_lines:
                    remaining_qty = move.remaining_qty
                    if move.state in ('done', 'cancel'):
                        #ignore stock moves cancelled or already done
                        continue
                    elif move.state == 'draft':
                        toassign_move_ids.append(move.id)
                    if float_compare(remaining_qty, 0,  precision_rounding = move.product_id.uom_id.rounding) == 0:
                        if move.state in ('draft', 'assigned', 'confirmed','shipping_process'):
                            todo_move_ids.append(move.id)
                    elif float_compare(remaining_qty,0, precision_rounding = move.product_id.uom_id.rounding) > 0 and \
                                float_compare(remaining_qty, move.product_qty, precision_rounding = move.product_id.uom_id.rounding) < 0:
                        new_move = stock_move_obj.split(cr, uid, move, remaining_qty, context=context)
                        todo_move_ids.append(move.id)
                        #Assign move as it was assigned before
                        toassign_move_ids.append(new_move)
                if need_rereserve or not all_op_processed: 
                    if not picking.location_id.usage in ("supplier", "production", "inventory"):
                        self.rereserve_quants(cr, uid, picking, move_ids=todo_move_ids, context=context)
                    self.do_recompute_remaining_quantities(cr, uid, [picking.id], context=context)
                if todo_move_ids and not context.get('do_only_split'):
                    self.pool.get('stock.move').action_done(cr, uid, todo_move_ids, context=context)
                    if picking.picking_type_id.code == 'incoming':
                        self.send_mail_memco_department(cr,uid,todo_move_ids)
                elif context.get('do_only_split'):
                    context = dict(context, split=todo_move_ids)
            self._create_backorder(cr, uid, picking, context=context)
            if toassign_move_ids:
                stock_move_obj.action_assign(cr, uid, toassign_move_ids, context=context)
        return True
    
    def send_mail_memco_department(self,cr,uid,todo_move_ids):
        
        pur_obj = self.pool.get('purchase.order')
        move_rec = self.pool.get('stock.move').browse(cr,uid,todo_move_ids[0])
        
        
        
        template_obj = self.pool.get('email.template')
        template_inst = template_obj.search(cr,uid,[('name','=','Detail send to Production Manager - Send by Email')])[0]
        template_id = template_obj.browse(cr, uid, template_inst)
        if move_rec.origin:
            pr_id = pur_obj.search(cr,uid,[('name','=',move_rec.origin)])[0]
            mo_iddd = pur_obj.browse(cr,uid,pr_id).project
            if mo_iddd.user_id:
                template_obj.write(cr, uid, template_inst, {'email_to':mo_iddd.user_id.partner_id.email}, context=None)
                action = template_obj.send_mail(cr,uid, template_inst, mo_iddd.id, context=None)
            else:
                _logger.warning("Mail are not sent to any one because Project not assign in Purchase Order.")
        
    def run_mail_cron(self, cr, uid, automatic=False, use_new_cursor=False, context=None):

        
        now = datetime.now().strftime("%Y-%m-%d")
        get_ids = self.search(cr, uid, [('notification_date','=',now)], context=context)
        template_obj = self.pool.get('email.template')
        template_inst = template_obj.search(cr,uid,[('name','=','Notification Shipment - Send by Email')])[0]
        template_id = template_obj.browse(cr, uid, template_inst)
        for data in self.browse(cr,uid,get_ids):
            template_obj.write(cr, uid, template_inst, {'email_to':data.owner_id.email}, context=context)
            action = template_obj.send_mail(cr,uid, template_inst, data.id, context)
        return True
