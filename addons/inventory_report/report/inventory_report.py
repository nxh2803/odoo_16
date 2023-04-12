from odoo import api, fields, models, _


class InventoryReport(models.TransientModel):
    _name = 'inventory.report'

    categ_name = fields.Char(string='Nhóm hàng', readonly=True)
    product_code = fields.Char(string='Mã hàng', index=True)
    product_name = fields.Char(string='Tên hàng', readonly=True)
    uom_name = fields.Char(string="ĐVT", readonly=True)
    equipment_name = fields.Char(string='Thiết bị', readonly=True)
    start_qty = fields.Float(string='Tồn đầu kì', readonly=True)
    in_qty = fields.Float(string='SL nhập', readonly=True)
    out_qty = fields.Float(string='SL xuất', readonly=True)
    finished_qty = fields.Float(string='Tồn cuối kì', readonly=True)
    date = fields.Date(string='Ngày', readonly=True)