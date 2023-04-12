from odoo import api, fields, models, _


class ProductTemplate(models.Model):
    _inherit = "product.template"

    equipment_id = fields.Char(string='Dùng cho')
    qr_code = fields.Char(string="Mã QR", related='product_variant_ids.qr_code', readonly=False)
    qr_code_img = fields.Binary(string="Hình ảnh QR", related='product_variant_ids.qr_code_img', readonly=False)

    template_start_qty = fields.Integer(string='Số lượng khởi tạo')
    template_location_id = fields.Many2one('stock.location',
                                           domain="[('usage', 'in', ['internal','transit'])]", string='Địa điểm')

    warehouse_quantity = fields.Float(compute='_get_warehouse_quantity', string='Tồn hiện có')

    def _get_warehouse_quantity(self):
        for record in self:
            location = self.env['stock.location'].search([
                ('company_id', '=', self.env.company.id), ('usage', '=', 'internal')], limit=1)
            if not location:
                record.warehouse_quantity = 0
                continue
            product_ids = self.env['product.product'].sudo().search([('product_tmpl_id', '=', record.id)])
            if not product_ids:
                record.warehouse_quantity = 0
                continue
            quant_ids = self.env['stock.quant'].sudo().search(
                    [('product_id', 'in', product_ids.ids), ('location_id', '=', location.id)])
            record.warehouse_quantity = sum([quant.quantity for quant in quant_ids])

    @api.model
    def create(self, vals_list):
        res = super(ProductTemplate, self).create(vals_list)
        if res.template_start_qty and res.template_start_qty > 0.0 and res.template_location_id:
            if not res.product_variant_id:
                return res
            product_id = res.product_variant_id.id
            self.env['stock.quant'].with_context(inventory_mode=True).create({
                'product_id': product_id,
                'location_id': res.template_location_id.id,
                'inventory_quantity': res.template_start_qty,
            })
        return res


    @api.onchange('qr_code')
    def onchange_qr_code(self):
        if self and self.qr_code:
            qr_code = self.qr_code
            self.qr_code_img = self.env['qr.generator'].get_qr_code(qr_code)
        else:
            self.qr_code = False
            self.qr_code_img = False


class ProductProduct(models.Model):
    _inherit = "product.product"

    qr_code = fields.Char(string="Mã QR", copy=False)
    qr_code_img = fields.Binary(string="Hình ảnh QR", copy=False)

    start_qty = fields.Integer(string='Số lượng khởi tạo')
    location_id = fields.Many2one('stock.location', domain="[('usage', 'in', ['internal','transit'])]")

    @api.model
    def create(self, vals_list):
        res = super(ProductProduct, self).create(vals_list)
        if res.start_qty and res.start_qty > 0.0 and res.location_id:
            self.env['stock.quant'].with_context(inventory_mode=True).create({
                'product_id': res.id,
                'location_id': res.location_id.id,
                'inventory_quantity': res.start_qty,
            })
        return res

    @api.onchange('qr_code')
    def onchange_qr_code(self):
        if self and self.qr_code:
            qr_code = self.qr_code
            self.qr_code_img = self.env['qr.generator'].get_qr_code(qr_code)
        else:
            self.qr_code = False
            self.qr_code_img = False

    def action_return_product_in_picking(self):
        stock_move = self.env['stock.move'].search([('picking_id.state', 'in', ['confirmed', 'assigned'])])
        product_ids = set(stock_move.mapped('product_id').ids)
        return {
            'name': 'Sản phẩm đang xử lí',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'product.product',
            'domain': [('id', 'in', list(product_ids))],
            'target': 'current'
        }