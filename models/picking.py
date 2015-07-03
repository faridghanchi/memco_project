from openerp import models, fields, api, _
from openerp.tools import float_compare
from openerp.osv import osv
from openerp.tools.float_utils import float_compare, float_round
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp import SUPERUSER_ID, api
import openerp.addons.decimal_precision as dp


#class carrier_extra_cost_line(models.Model):

#    _name = 'carrier.extra.cost.line'
#    product = fields.Many2one('product.product',domain="[('type','=','service')]")
#    cost = fields.Float()
#    extra_cost_id = fields.Many2one('carrier.extra.cost')

#class carrier_extra_cost(models.Model):

#    """
#    This ml coverd information about bom
#    """
#    _name = 'carrier.extra.cost'
#    
#    @api.depends('total_cost','m_cost_line')
#    def _get_cost_line(self):
#            self.total_cost = sum(line.cost for line in self.m_cost_line)
#    
#    #m_carrier_id = fields.Many2one("res.partner","Carrier")
#    carrier_company = fields.Many2one("res.partner","Carrier Company")
##    state = fields.Selection([('draft','Draft'),('done','Done'),('cancel','Cancel')],string='Stage', default='draft')
#    m_volume = fields.Float('Volume', copy=False)
#    m_carrier_tracking_ref = fields.Char('Carrier Tracking Ref', copy=False)
#    m_number_of_packages = fields.Integer('Number of Packages', copy=False)
#    m_cost_line = fields.One2many('carrier.extra.cost.line','extra_cost_id')
#    
#    total_cost = fields.Float('Total Cost', compute=_get_cost_line)
#    i_picking_id = fields.Many2one('stock.picking', 'Picking')
#    l_picking_id = fields.Many2one('stock.picking', 'Picking')
#    

    
    
    
class stock_picking(models.Model):

    _inherit = 'stock.picking'
    _name = 'stock.picking'
    _order = 'date'
#    @api.multi
#    def do_ready_shipping(self):
#        print '#######',self.state
#        self.state = 'ready_to_shipping'
#        print '#######aftre',self.state
#    @api.one
#    def do_shipping_process(self):
#        print '#######',self.state
#        self.state = 'shipping_process'

    @api.depends('i_carrier_cost','i_carrier_extra_cost')
    def _total_inter_cost(self):
        self.i_carrier_cost = sum(line.total_cost for line in self.i_carrier_extra_cost)

    @api.depends('l_carrier_cost','l_carrier_extra_cost')
    def _total_local_cost(self):
            self.l_carrier_cost = sum(line.total_cost for line in self.l_carrier_extra_cost)

#    done_carrier_invoice = fields.Boolean(string="Done International Carrier Invoice")
#    done_l_carrier_invoice = fields.Boolean(string="Done Local Carrier Invoice")
    
    i_carrier_extra_cost = fields.One2many('carrier.extra.cost','i_picking_id')
    l_carrier_extra_cost = fields.One2many('carrier.extra.cost','l_picking_id')
    
    i_carrier_cost = fields.Float(string='Carrier Cost',compute=_total_inter_cost)
    l_carrier_cost = fields.Float(string='Carrier Cost',compute=_total_local_cost)
    lc_cost = fields.Float(string='LC cost')
    
    description = fields.Text(string='Description')
    color = fields.Integer('Color Index', default=0)
    po_id = fields.Many2one('memco.lcform', 'Purchase Order')

    @api.cr_uid_ids_context
    def do_prepare_partial(self, cr, uid, picking_ids, context=None):
        context = context or {}
        pack_operation_obj = self.pool.get('stock.pack.operation')
        #used to avoid recomputing the remaining quantities at each new pack operation created
        ctx = context.copy()
        ctx['no_recompute'] = True

        #get list of existing operations and delete them
        existing_package_ids = pack_operation_obj.search(cr, uid, [('picking_id', 'in', picking_ids)], context=context)
        if existing_package_ids:
            pack_operation_obj.unlink(cr, uid, existing_package_ids, context)
        for picking in self.browse(cr, uid, picking_ids, context=context):
            forced_qties = {}  # Quantity remaining after calculating reserved quants
            picking_quants = []
            #Calculate packages, reserved quants, qtys of this picking's moves
            for move in picking.move_lines:
                if move.state not in ('assigned', 'confirmed','shipping_process'):
                    continue
                move_quants = move.reserved_quant_ids
                picking_quants += move_quants
                forced_qty = (move.state in ('assigned','shipping_process')) and move.product_qty - sum([x.qty for x in move_quants]) or 0
                #if we used force_assign() on the move, or if the move is incoming, forced_qty > 0
                if float_compare(forced_qty, 0, precision_rounding=move.product_id.uom_id.rounding) > 0:
                    if forced_qties.get(move.product_id):
                        forced_qties[move.product_id] += forced_qty
                    else:
                        forced_qties[move.product_id] = forced_qty
            print "@@@@@@2",picking_quants, forced_qties
            for vals in self._prepare_pack_ops(cr, uid, picking, picking_quants, forced_qties, context=context):
                pack_operation_obj.create(cr, uid, vals, context=ctx)
        #recompute the remaining quantities all at once
        self.do_recompute_remaining_quantities(cr, uid, picking_ids, context=context)
        self.write(cr, uid, picking_ids, {'recompute_pack_op': False}, context=context)



#class stock_picking(models.Model):

#    _inherit = 'stock.picking'

#    done_carrier_invoice = fields.Boolean(string="Done International Carrier Invoice")
#    carrier_cost = fields.Float(string='Carrier Cost')
#    carrier_extra_cost = fields.One2many('carrier.extra.cost','picking_id')

#    #for local carrier
#    done_l_carrier_invoice = fields.Boolean(string="Done Local Carrier Invoice")
#    l_carrier_id = fields.Many2one("delivery.carrier","Carrier")
#    l_volume = fields.Float('Volume', copy=False)

#    l_carrier_tracking_ref = fields.Char('Carrier Tracking Ref', copy=False)
#    l_number_of_packages = fields.Integer('Number of Packages', copy=False)
##    l_weight_uom_id = fields.Many2one('product.uom', 'Unit of Measure', required=True,readonly="1",help="Unit of measurement for Weight")

#    l_done_carrier_invoice = fields.Boolean()
#    l_carrier_cost = fields.Float(string='Carrier Cost')
#    l_carrier_extra_cost = fields.One2many('carrier.extra.cost','l_picking_id')

#    @api.onchange('carrier_cost','l_carrier_cost', 'carrier_extra_cost', 'l_carrier_extra_cost')
#    def _onchange_total_cost(self):
#            self.carrier_cost = sum(line.cost for line in self.carrier_extra_cost)
#            self.l_carrier_cost = sum(line.cost for line in self.l_carrier_extra_cost)

##    @api.multi
##    def _get_extra_cost(self):
##        if self.carrier_extra_cost:
##            self.carrier_cost = sum(line.cost for line in self.carrier_extra_cost)

##    @api.multi
##    def _get_l_extra_cost(self):
##        if self.l_carrier_extra_cost:
##            self.l_carrier_cost = sum(line.cost for line in self.l_carrier_extra_cost)
