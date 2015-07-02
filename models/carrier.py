from openerp import models, fields, api, _
from openerp.tools import float_compare
from openerp.osv import osv
from openerp.tools.float_utils import float_compare, float_round
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp import SUPERUSER_ID, api
import openerp.addons.decimal_precision as dp


class carrier_extra_cost_line(models.Model):

    _name = 'carrier.extra.cost.line'
    product = fields.Many2one('product.product',domain="[('type','=','service')]")
    cost = fields.Float()
    extra_cost_id = fields.Many2one('carrier.extra.cost')

class carrier_extra_cost(models.Model):

    """
    This ml coverd information about bom
    """
    _name = 'carrier.extra.cost'
    
    @api.depends('total_cost','m_cost_line')
    def _get_cost_line(self):
            self.total_cost = sum(line.cost for line in self.m_cost_line)
    
    #m_carrier_id = fields.Many2one("res.partner","Carrier")
    carrier_company = fields.Many2one("res.partner","Carrier Company")
    state = fields.Selection([('draft','Draft'),('done','Done'),('cancel','Cancel')],string='Stage', default='draft')
    m_volume = fields.Float('Volume', copy=False)
    m_carrier_tracking_ref = fields.Char('Carrier Tracking Ref', copy=False)
    m_number_of_packages = fields.Integer('Number of Packages', copy=False)
    m_cost_line = fields.One2many('carrier.extra.cost.line','extra_cost_id')
    
    total_cost = fields.Float('Total Cost', compute=_get_cost_line)
    i_picking_id = fields.Many2one('stock.picking', 'Picking')
    l_picking_id = fields.Many2one('stock.picking', 'Picking')
    
    

#class carrier_extra_cost(models.Model):

#    """
#    This ml coverd information about bom
#    """
#    _name = 'carrier.extra.cost'
#    product = fields.Many2one('product.product',domain="[('type','=','service')]")
#    picking_id = fields.Many2one('stock.picking', 'Picking')
#    l_picking_id = fields.Many2one('stock.picking', 'Picking')
#    cost = fields.Float()

