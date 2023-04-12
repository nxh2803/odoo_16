# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class MulticompanyTransferStock(models.Model):
    _name = 'multicompany.transfer.stock'
    _rec_name = 'name'
    _description = 'Chuyển hàng nội bộ'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Tên phiếu', default=lambda self: _('New'))
    transfer_from = fields.Many2one('res.company', string='Công ty nguồn', required=True)
    transfer_to = fields.Many2one('res.company', string='Công ty đích', required=True)
    transfer_from_location = fields.Many2one('stock.location', string='Địa điểm nguồn', required=True)
    transfer_to_location = fields.Many2one('stock.location', string='Địa điểm đích', required=True)
    scheduled_date = fields.Datetime(string='Ngày dự kiến', default=fields.Datetime.now)
    note_for_transfer = fields.Text(string='Ghi chú')
    state = fields.Selection([
        ('draft', 'Khởi tạo'),
        ('posted', 'Hoàn thành')
    ], string='Trạng thái', default='draft')
    transfer_lines = fields.One2many('multicompany.transfer.stock.line', 'multicompany_transfer_id',
                                     string='Chi tiết điều chuyển')
    stock_picking_ids = fields.One2many('stock.picking', 'multicompany_transfer_id')

    def action_view_stock_picking(self):
        self = self.sudo()
        self.ensure_one()
        stock_picking_ids = self.stock_picking_ids.ids
        action = {
            'name': _('Phiếu điều chuyển của %s', self.name),
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
            'context': {'default_multicompany_transfer_id': self.id},
            'domain': [('id', 'in', stock_picking_ids)],
            'view_mode': 'tree,form',
        }
        return action

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            seq_date = None
            if 'schedule_date' in vals:
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['schedule_date']))
            vals['name'] = self.env['ir.sequence'].next_by_code('multicompany.transfer.stock', sequence_date=seq_date) or _('New')
        return super(MulticompanyTransferStock, self).create(vals)

    def get_value_for_picking(self, type):
        self = self.sudo()
        picking_type = self.env['stock.picking.type']
        transfer_from = self.transfer_from
        transfer_to = self.transfer_to
        location_id = self.transfer_from_location
        location_dest_id = self.transfer_to_location

        if type == 'internal':
            picking_type_id = picking_type.search(
                [('code', '=', 'internal'),
                 ('warehouse_id.company_id', '=', transfer_from.id),
                 ('default_location_src_id', '=', location_id.id)], limit=1)
            location_id = location_id.id
            location_dest_id = location_dest_id.id

        elif type == 'outgoing':
            picking_type_id = picking_type.search(
                [('code', '=', 'outgoing'),
                 ('warehouse_id.company_id', '=', transfer_from.id),
                 ('default_location_src_id', '=', location_id.id)], limit=1)
            location_id = location_id.id
            location_dest_id = self.env.ref('stock.stock_location_customers').id

        elif type == 'incoming':
            picking_type_id = picking_type.search(
                [('code', '=', 'incoming'),
                 ('warehouse_id.company_id', '=', transfer_to.id),
                 ('default_location_dest_id', '=', location_dest_id.id)], limit=1)
            location_id = self.env.ref('stock.stock_location_suppliers').id
            location_dest_id = location_dest_id.id
        else:
            raise ValueError('Không tìm thấy loại điều chuyển khả dụng!')

        vals = {
            'picking_type_id': picking_type_id.id,
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'scheduled_date': self.scheduled_date,
            'multicompany_transfer_id': self.id,
            'origin': self.name,
            'move_lines': [(0, 0, {
                'name': line.product_id.name,
                'product_id': line.product_id.id,
                'product_uom': line.product_uom_type.id,
                'product_uom_qty': line.qty_transfer,
                'quantity_done': line.qty_transfer,
                'location_id': location_id,
                'location_dest_id': location_dest_id,
                'picking_type_id': picking_type.id

            }) for line in self.transfer_lines]}
        return vals

    def confirm_inventory_transfer(self):
        self = self.sudo()
        stock_picking = self.env['stock.picking']
        if self.transfer_from.id == self.transfer_to.id:
            vals = self.get_value_for_picking('internal')
            picking = stock_picking.create(vals)
            picking.action_confirm()
            picking._action_done()
        else:
            vals_incoming = self.get_value_for_picking('incoming')
            picking_incoming = stock_picking.create(vals_incoming)
            picking_incoming.action_confirm()
            # picking_incoming._action_done()

            vals_outgoing = self.get_value_for_picking('outgoing')
            picking_outgoing = stock_picking.create(vals_outgoing)
            picking_outgoing.action_confirm()
            picking_outgoing._action_done()

        self.state = 'posted'


class MulticompanyTransferStockLine(models.Model):
    _name = 'multicompany.transfer.stock.line'

    multicompany_transfer_id = fields.Many2one('multicompany.transfer.stock', string='Phiếu điều chuyển')
    product_id = fields.Many2one('product.product', string='Sản phẩm', required=True)
    qty_availible = fields.Float(string='Số lượng có sẵn', compute='_get_availible_qty')
    qty_transfer = fields.Float(string='Số lượng chuyển', required=True)
    product_uom_type = fields.Many2one(related='product_id.uom_id', string='Đơn vị')

    equipment = fields.Char(related='product_id.equipment_id', string='Dùng cho')
    categ_id = fields.Many2one(related='product_id.categ_id', string='Nhóm sản phẩm')
    default_code = fields.Char(related='product_id.default_code', string='Mã nội bộ')
    qty_available = fields.Float(related='product_id.qty_available', string='SL thực tế')

    def _get_availible_qty(self):
        for rec in self:
            stock_quant = self.env['stock.quant']
            stock_location = rec.multicompany_transfer_id.transfer_from_location if rec.multicompany_transfer_id \
                else False
            if rec.product_id and stock_location:
                rec.qty_availible = stock_quant._get_available_quantity(rec.product_id, stock_location)
            else:
                rec.qty_availible = False