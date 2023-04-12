from odoo import api, fields, models, _
from odoo.exceptions import Warning, UserError, ValidationError
import pytz
from datetime import datetime
from datetime import timedelta
import itertools
from operator import itemgetter
import operator

FORMAT_DATE = "%Y-%m-%d"
TIMEZONE_ERROR = _("Set your timezone in preferences")


class InventoryReportWizard(models.TransientModel):
    _name = 'inventory.report.wizard'

    report_type = fields.Selection([
        ('inventory', 'Báo cáo tồn kho'),
        ('in', 'Báo cáo nhập kho'),
        ('out', 'Báo cáo xuất kho'),
    ], string='Loại báo cáo', default='inventory', required=True)
    location_id = fields.Many2one('stock.location', string='Địa điểm', required="1")
    start_date = fields.Date('Ngày bắt đầu')
    end_date = fields.Date('Ngày kết thúc')
    company_id = fields.Many2one('res.company', required="1", default=lambda self: self.env.user.company_id)

    def create_inventory_report(self, values, type=False):
        if not values:
            raise ValidationError('Không có dữ liệu!')
        report_obj = self.env['inventory.report']
        for line in values:
            if type == 'inventory':
                vals = {
                    'categ_name':  line.get("categ"), 'product_code': line.get("ref"), 'product_name': line.get("name"),
                    'uom_name': line.get("uom"), 'equipment_name': line.get("equipment"), 'start_qty': line.get("si"),
                    'in_qty': line.get("in"), 'out_qty': line.get("out"), 'finished_qty': line.get("fi")}
            else:
                product = self.env['product.product'].browse(line.get('product_id'))
                if not product:
                    continue
                product_code = product.product_tmpl_id.default_code
                categ_name = product.product_tmpl_id.categ_id.name if product.product_tmpl_id.categ_id else False
                equipment_name = product.product_tmpl_id.equipment_id if type == 'in' else line.get("equipment")
                uom_id = self.env['uom.uom'].browse(line.get('p_uom'))
                uom_name = uom_id.name if uom_id else False
                if line.get("date"):
                    date = datetime.strptime(line.get("date"), "%d-%m-%Y").strftime("%Y-%m-%d")
                else:
                    date = False
                vals = {'date': date, 'categ_name': categ_name, 'product_code': product_code,
                        'product_name': line.get("product"), 'uom_name': uom_name, 'equipment_name': equipment_name,
                        'in_qty': line.get("in_qty"), 'out_qty': line.get("out_qty")}
            report_obj.create(vals)

    @api.model
    def convert_utc_tz(self, utc_datetime):
        user_tz = self.env.user.tz
        if not user_tz:
            raise Warning(TIMEZONE_ERROR)
        local_tz = pytz.timezone(user_tz)
        date = datetime.strptime(str(utc_datetime), FORMAT_DATE)
        date = pytz.utc.localize(date, is_dst=None).astimezone(local_tz)
        return date.strftime(FORMAT_DATE)

    def action_generate_data(self):
        self.ensure_one()
        datas = {}
        datas['date_start'] = self.convert_utc_tz(self.start_date)
        datas['date_end'] = self.convert_utc_tz(self.end_date)
        datas['start'] = self.start_date
        datas['end'] = self.end_date
        datas['location_id'] = self.location_id.id
        datas['location_name'] = self.location_id.name
        datas['company_id'] = self.company_id.id
        self.env['inventory.report'].search([]).unlink()
        if self.report_type == 'inventory':
            values = self.get_values(datas)
            lines = values.get("lines")
            self.create_inventory_report(lines, type='inventory')
            name = f'Báo cáo tồn kho / {self.location_id.name} / {self.start_date} - {self.end_date} '
            view_id = self.env.ref('inventory_report.inventory_report_tree_view').id

        elif self.report_type == 'in':
            values = self.get_lines(type='in')
            self.create_inventory_report(values, type='in')
            name = f'Báo cáo nhập kho / {self.location_id.name} / {self.start_date} - {self.end_date} '
            view_id = self.env.ref('inventory_report.inventory_report_in_tree_view').id

        elif self.report_type == 'out':
            values = self.get_lines(type='out')
            self.create_inventory_report(values, type='out')
            name = f'Báo cáo xuất kho / {self.location_id.name} / {self.start_date} - {self.end_date} '
            view_id = self.env.ref('inventory_report.inventory_report_out_tree_view').id

        else:
            return False

        return {
            'type': 'ir.actions.act_window',
            'target': 'current',
            'name': name,
            'view_mode': 'tree',
            'view_id': view_id,
            # 'context': {'no_breadcrumbs': True},
            'search_view_id': self.env.ref('inventory_report.inventory_report_search_view').id,
            'res_model': 'inventory.report',
        }

    # inventory report

    def get_products_and_move(self, company_id, location_id, start, end):
        quant_domain = [('location_id', 'child_of', location_id), ('company_id', '=', company_id)]
        moves_domain = [
            ('date', '>=', start), ('date', '<=', end), ('state', '=', 'done'), ('company_id', '=', company_id), ('picking_id', '!=', False),
            '|', ('location_dest_id', 'child_of', location_id), ('location_id', 'child_of', location_id)]

        quants = self.env["stock.quant"].search(quant_domain)
        moves = self.env['stock.move'].search(moves_domain)

        location = self.env['stock.location'].browse(location_id)
        location_ids = self.env['stock.location'].search([
            ('parent_path', '=like', location.parent_path + "%")])

        mv_in = moves.filtered(
            lambda x: x.location_dest_id.id in location_ids.ids)
        mv_out = moves.filtered(
            lambda x: x.location_id.id in location_ids.ids)

        products = quants.mapped('product_id')
        products |= mv_in.mapped("product_id")
        products |= mv_out.mapped("product_id")

        return products, mv_in, mv_out, quants

    def get_line_sn(self, mvl_in_pro, mvl_out_pro, location_id, start, end, product, price):
        line_sn = {}
        # if not mvl_in_pro and not mvl_out_pro:
        #     return None
        product_uom = product.uom_id
        tot_in = 0
        for elt in mvl_in_pro:
            if product_uom.id != elt.product_uom_id.id:
                factor = product_uom.factor / elt.product_uom_id.factor
            else:
                factor = 1.0
            tot_in += elt.qty_done * factor

        tot_out = 0
        for elt in mvl_out_pro:
            if product_uom.id != elt.product_uom_id.id:
                factor = product_uom.factor / elt.product_uom_id.factor
            else:
                factor = 1.0
            tot_out += elt.qty_done * factor
        ctx = {
            'location': location_id,
            'to_date': end}
        actual_qty = product.with_context(ctx).qty_available

        line_sn['si'] = actual_qty - tot_in + tot_out
        line_sn['in'] = tot_in
        line_sn['out'] = tot_out
        line_sn['bal'] = tot_in - tot_out
        line_sn['fi'] = actual_qty
        line_sn['cost'] = price
        line_sn['value'] = price * actual_qty

        return line_sn

    def get_values(self, data):
        start = str(data['start']) + ' 00:00:00'
        end = str(data['end']) + ' 23:59:59'
        date_start = str(data['date_start']) + ' 00:00:00'
        date_end = str(data['date_end']) + ' 23:59:59'
        location_id = data['location_id']
        company_id = data['company_id']

        products, mv_in, mv_out, quants = self.get_products_and_move(company_id, location_id, start, end)
        datas = {}
        datas['location'] = data['location_name']
        datas['date_from'] = date_start
        datas['date_to'] = date_end
        result = []
        products = products.filtered(lambda product: product.active)
        for product in products.sorted(lambda r: r.name):
            line = {}
            line['name'] = product.name
            line['ref'] = product.default_code
            line['uom'] = product.uom_id.name
            line['categ'] = product.categ_id.name
            line['equipment'] = product.equipment_id

            price = product.standard_price
            mv_in_pro = mv_in.filtered(
                lambda x: x.product_id.id == product.id)
            mv_out_pro = mv_out.filtered(
                lambda x: x.product_id.id == product.id)
            quants_pro = quants.filtered(
                lambda x: x.product_id.id == product.id)

            lots = quants_pro.mapped('lot_id')
            lots |= mv_in_pro.mapped("move_line_ids.lot_id")
            lots |= mv_out_pro.mapped("move_line_ids.lot_id")

            mvl_in_pro = mv_in_pro.mapped("move_line_ids")
            mvl_out_pro = mv_out_pro.mapped("move_line_ids")
            elt = self.get_line_sn(mvl_in_pro, mvl_out_pro, location_id, start, end, product, price)
            if elt and any([elt[key] != 0 for key in elt]):
                line.update(elt)
                result.append(line)
        datas['lines'] = result
        return datas

    # in inventory report

    def get_product_ids(self):
        product_pool = self.env['product.product']
        product_ids = product_pool.search([('type', '=', 'product'), ('active', '=', True)])
        return product_ids.ids

    def in_lines(self, product_ids):
        start_date = str(self.start_date) + ' 00:00:00'
        end_date = str(self.end_date) + ' 23:59:59'
        state = ('draft', 'cancel')
        query = """select sm.date as date, sm.origin as origin, sm.reference as ref, pt.name as product,\
                  sm.product_uom_qty as in_qty, sm.product_uom as m_uom,pt.uom_po_id as p_uom, pp.id as product_id from stock_move as sm \
                  JOIN product_product as pp ON pp.id = sm.product_id \
                  JOIN product_template as pt ON pp.product_tmpl_id = pt.id \
                  where sm.date >= %s and sm.date <= %s \
                  and sm.location_dest_id = %s and sm.product_id in %s \
                  and sm.state not in %s and sm.company_id = %s and sm.picking_id is not NULL
                  """

        params = (start_date, end_date, self.location_id.id, tuple(product_ids), state, self.company_id.id)
        self.env.cr.execute(query, params)
        result = self.env.cr.dictfetchall()
        for res in result:
            f_date = ' '
            if res.get('date'):
                data_date = datetime.strptime(str(res.get('date')), '%Y-%m-%d %H:%M:%S') + timedelta(hours=7)
                f_date = data_date.strftime('%d-%m-%Y')
            if res.get('m_uom') and res.get('p_uom') and res.get('in_qty'):
                if res.get('m_uom') != res.get('p_uom'):
                    move_uom = self.env['uom.uom'].browse(res.get('m_uom'))
                    product_uom = self.env['uom.uom'].browse(res.get('p_uom'))
                    qty = move_uom._compute_quantity(res.get('in_qty'), product_uom)
                    res.update({
                        'in_qty': qty,
                        'date': f_date,
                    })
            res.update({
                'out_qty': 0.0,
                'date': f_date,
            })
        return result

    def out_lines(self, product_ids):
        state = ('draft', 'cancel')
        start_date = str(self.start_date) + ' 00:00:00'
        end_date = str(self.end_date) + ' 23:59:59'
        move_type = 'outgoing'
        m_type = ''
        if self.location_id:
            m_type = 'and sm.location_id = %s'

        query = """select sm.date as date, sm.origin as origin, sm.reference as ref, pt.name as product,\
                      sm.product_uom_qty as out_qty, sm.equipment_picking as equipment, sm.product_uom as m_uom,pt.uom_id as p_uom, pp.id as product_id\
                      from stock_move as sm JOIN product_product as pp ON pp.id = sm.product_id \
                      JOIN product_template as pt ON pp.product_tmpl_id = pt.id \
                      where sm.date >= %s and sm.date <= %s \
                      and sm.location_id = %s and sm.product_id in %s \
                      and sm.state not in %s and sm.company_id = %s and sm.picking_id is not NULL
                      """

        params = (start_date, end_date, self.location_id.id, tuple(product_ids), state, self.company_id.id)

        self.env.cr.execute(query, params)
        result = self.env.cr.dictfetchall()
        for res in result:
            f_date = ' '
            if res.get('date'):
                data_date = datetime.strptime(str(res.get('date')), '%Y-%m-%d %H:%M:%S') + timedelta(hours=7)
                f_date = data_date.strftime('%d-%m-%Y')
            if res.get('m_uom') and res.get('p_uom') and res.get('out_qty'):
                if res.get('m_uom') != res.get('p_uom'):
                    move_uom = self.env['uom.uom'].browse(res.get('m_uom'))
                    product_uom = self.env['uom.uom'].browse(res.get('p_uom'))
                    qty = move_uom._compute_quantity(res.get('out_qty'), product_uom)
                    res.update({
                        'out_qty': qty,
                        'date': f_date,
                    })
            res.update({
                'in_qty': 0.0,
                'date': f_date,
            })
        return result

    def get_lines(self, type=False):
        product_ids = self.get_product_ids()
        result = []
        if product_ids:
            if type == 'in':
                lines = self.in_lines(product_ids)
            else:
                lines = self.out_lines(product_ids)
            if lines:
                for line in lines:
                    result.append(line)
        return result

