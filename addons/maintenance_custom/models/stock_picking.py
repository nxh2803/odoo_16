from odoo import fields, models, api, _
from odoo.tools import float_is_zero


class StockPicking(models.Model):
    _inherit = "stock.picking"

    equipment = fields.Char(string='Dùng cho thiết bị')
    multicompany_transfer_id = fields.Many2one('multicompany.transfer.stock')
    picking_type_code = fields.Selection(related='picking_type_id.code', store=True)
    move_line_nosuggest_ids = fields.One2many('stock.move.line', 'picking_id', domain=['|', ('product_qty', '=', 0.0), ('qty_done', '!=', 0.0)])

    def action_return_in_picking(self):
        default_immediate_tranfer = True
        if self.env['ir.config_parameter'].sudo().get_param('stock.no_default_immediate_tranfer'):
            default_immediate_tranfer = False
        picking_type_in = self.env['stock.picking.type'].search([('code', '=', 'incoming')], limit=1)
        if not picking_type_in:
            return False
        domain = [('picking_type_code', '=', 'incoming')]
        context = {
            # 'search_default_picking_type_id': [picking_type_in.id],
            'default_picking_type_id': picking_type_in.id,
            'default_immediate_transfer': default_immediate_tranfer,
            # 'invisible_in': True
            # 'search_default_available': 1
        }
        return {
            'name': 'Nhập kho',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'context': context,
            'domain': domain,
            'target': 'current'
        }

    def action_return_out_picking(self):
        default_immediate_tranfer = True
        if self.env['ir.config_parameter'].sudo().get_param('stock.no_default_immediate_tranfer'):
            default_immediate_tranfer = False
        picking_type_out = self.env['stock.picking.type'].search([('code', '=', 'outgoing')], limit=1)
        if not picking_type_out:
            return False
        domain = [('picking_type_code', '=', 'outgoing')]
        context = {
            # 'search_default_picking_type_id': [picking_type_out.id],
            'default_picking_type_id': picking_type_out.id,
            'default_immediate_transfer': default_immediate_tranfer,
            # 'invisible_out': True
            # 'search_default_available': 1
        }
        return {
            'name': 'Xuất kho',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'context': context,
            'domain': domain,
            'target': 'current'
        }

    # def update_value_picking(self):
    #     move_lines = self.env['stock.move.line'].search([])
    #     for move_line in move_lines:
    #         if move_line.state != 'done':
    #             continue
    #         move = move_line.move_id
    #         rounding = move.product_id.uom_id.rounding
    #         diff = move_line.qty_done
    #         if float_is_zero(diff, precision_rounding=rounding):
    #             continue
    #         move_line._create_correction_svl(move, diff)
    #     return True


class StockMove(models.Model):
    _inherit = "stock.move"

    equipment = fields.Char(related='product_id.equipment_id', string='Dùng cho', store=True)
    equipment_picking = fields.Char(compute='_get_equipment_picking', string='Dùng cho', store=True)
    categ_id = fields.Many2one(related='product_id.categ_id', string='Nhóm sản phẩm')
    default_code = fields.Char(related='product_id.default_code', string='Mã nội bộ')
    uom_id = fields.Many2one(related='product_id.uom_id', string='Đơn vị')
    qty_available = fields.Float(related='product_id.product_tmpl_id.warehouse_quantity', string='SL thực tế')

    # equipment_name = fields.Char(string='Dùng cho')

    @api.depends("move_line_ids")
    def _get_equipment_picking(self):
        for rec in self:
            if rec.move_line_ids:
                rec.equipment_picking = rec.move_line_ids[0].equipment_picking
            else:
                rec.equipment_picking = False

    @api.model
    def create(self, vals_list):
        res = super(StockMove, self).create(vals_list)
        if res.picking_id and res.picking_id.scheduled_date:
            res.date = res.picking_id.scheduled_date
        return res

    def write(self, vals):
        res = super(StockMove, self).write(vals)
        for rec in self:
            if not rec.picking_id or not rec.picking_id.scheduled_date:
                continue
            if rec.date == rec.picking_id.scheduled_date:
                continue
            rec.date = rec.picking_id.scheduled_date
        return res


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    equipment = fields.Char(related='product_id.equipment_id', string='Dùng cho')
    categ_id = fields.Many2one(related='product_id.categ_id', string='Nhóm sản phẩm')
    default_code = fields.Char(related='product_id.default_code', string='Mã nội bộ')
    uom_id = fields.Many2one(related='product_id.uom_id', string='Đơn vị')
    qty_available = fields.Float(related='product_id.product_tmpl_id.warehouse_quantity', string='SL thực tế')

    equipment_picking = fields.Char(string='Dùng cho')

    @api.model
    def create(self, vals_list):
        res = super(StockMoveLine, self).create(vals_list)
        if res.picking_id and res.picking_id.scheduled_date:
            res.date = res.picking_id.scheduled_date
        return res

    def write(self, vals):
        res = super(StockMoveLine, self).write(vals)
        for rec in self:
            if not rec.picking_id or not rec.picking_id.scheduled_date:
                continue
            if rec.date == rec.picking_id.scheduled_date:
                continue
            rec.date = rec.picking_id.scheduled_date
        return res
