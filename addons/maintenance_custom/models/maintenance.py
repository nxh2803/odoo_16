from odoo import api, fields, models, _
from datetime import datetime
import os


class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    code = fields.Char(string='Mã số thiết bị')
    so_khung = fields.Char(string='Số khung')

    qr_code = fields.Char(string="Mã QR", copy=False, compute='_get_qr_code')
    qr_code_img = fields.Binary(string="Hình ảnh QR", copy=False, compute='_get_qr_code')
    last_request = fields.Date(string='Yêu cầu gần nhất', compute='_get_last_request', store=True)
    machine_running_time = fields.Float(string='Giờ máy')
    machine_attendence_time = fields.Float(string='Giờ điểm danh cuối')
    location_id = fields.Many2one('equipment.location', string='Vị trí')
    attachment_ids = fields.One2many('ir.attachment', 'res_id', string='Attachments')
    manual_ids = fields.One2many('ir.attachment', 'res_id', string='User Manual', compute='compute_manual_ids')
    attendence_ids = fields.One2many('fleet.attendence', 'equipment_id', string='Danh sách điểm danh')

    _sql_constraints = [
        ('code_uniq', 'unique (code)', "Mã số đã tồn tại !"),
        ('so_khung_uniq', 'unique (so_khung)', "Số khung đã tồn tại !"),
    ]

    def compute_manual_ids(self):
        for rec in self:
            if rec.attachment_ids:
                rec.manual_ids = rec.attachment_ids.filtered(lambda r: os.path.splitext(r.name)[0] in [str(i) for i in range(100)])
            else:
                rec.manual_ids = False

    @api.depends('maintenance_ids', 'maintenance_ids.date_process')
    def _get_last_request(self):
        for rec in self:
            last_request = rec.maintenance_ids.filtered(lambda x: x.date_process)
            last_request = last_request.sorted(key=lambda r: r.date_process, reverse=True)
            rec.last_request = last_request[0].date_process if last_request else False

    def update_machine_attendence_time(self, attendence=False):
        for rec in self:
            if not rec.attendence_ids:
                rec.machine_attendence_time = 0.0
                continue
            domain = [('equipment_id', '=', rec.id), ('end_date', '!=', False)]
            if attendence:
                domain += [('id', '!=', attendence)]
            list_attendence = rec.env['fleet.attendence'].search(domain, order='end_date desc')
            if not list_attendence:
                continue
            if not list_attendence[0].odometer_end:
                continue
            rec.machine_attendence_time = list_attendence[0].odometer_end
        return True

    def update_machine_running_time(self, maintenance=False):
        for rec in self:
            if not rec.maintenance_ids:
                rec.machine_running_time = 0.0
                continue
            domain = [('equipment_id', '=', rec.id), ('date_process', '!=', False)]
            if maintenance:
                domain += [('id', '!=', maintenance)]
            list_maintenance = rec.env['maintenance.request'].search(domain, order='date_process desc')
            if not list_maintenance:
                continue
            if not list_maintenance[0].machine_running_time:
                continue
            rec.machine_running_time = list_maintenance[0].machine_running_time
        return True

    @api.depends('name', 'serial_no', 'code', 'so_khung', 'last_request')
    def _get_qr_code(self):
        for rec in self:
            if not rec.code and not rec.so_khung:
                rec.qr_code = False
                rec.qr_code_img = False
            else:
                qr_code = f'{rec.code or False}' + '|' + f'{rec.so_khung or False}'
            # qr_code = rec.name or ''
            # if rec.serial_no:
            #     qr_code += f'\nSerial: {rec.serial_no}'
            # if rec.code:
            #     qr_code += f'\nMã số: {rec.code}'
            # if rec.so_khung:
            #     qr_code += f'\nSố khung: {rec.so_khung}'
            # if rec.last_request:
            #     last_request = rec.last_request.strftime('%d/%m/%Y')
            #     qr_code += f'\nY/c gần nhất: {last_request}'
                rec.qr_code = qr_code
                rec.qr_code_img = rec.env['qr.generator'].get_qr_code(qr_code)

    def create_maintenance_request(self, note, machine_running_time, images):
        MT = self.env['maintenance.team']
        maintenance_team_id = self.maintenance_team_id or MT.search([])

        if not maintenance_team_id:
            maintenance_team_id = MT.create({"name": 'Đội bảo trì', 'company_id': self.company_id.id})

        vals = {
            'equipment_id': self.id,
            'name': f'Yêu cầu sửa chữa thiết bị {self.name}',
            'note': note,
            'machine_running_time': machine_running_time,
            'company_id': self.company_id.id,
            'maintenance_team_id': maintenance_team_id.id
        }
        maintenance_request = self.env['maintenance.request'].create(vals)
        for image in images:
            self.env['ir.attachment'].create({
                'name': str(maintenance_request.id),
                'type': 'url',
                'url': image,
                'res_model': 'maintenance.request',
                'res_id': maintenance_request.id,
            })
        return maintenance_request


class MaintenanceRequest(models.Model):
    _inherit = "maintenance.request"
    _order = "date_process desc, create_date desc"

    date_process = fields.Date(string='Ngày thực hiện')
    performer_id = fields.Many2one('hr.employee', string='Người thực hiện')
    machine_running_time = fields.Float(string='Giờ máy')
    note = fields.Text(string='Mô tả')
    attachment_ids = fields.One2many('ir.attachment', 'res_id', string='Attachments')

    # def update_machine_running_time(self):
    #     for rec in self:
    #         if not rec.equipment_id or not rec.machine_running_time:
    #             continue
    #         # if rec.equipment_id.machine_running_time and rec.machine_running_time <= rec.equipment_id.machine_running_time:
    #         #     continue
    #         rec.equipment_id.machine_running_time = rec.machine_running_time
    #     return True

    @api.model
    def create(self, vals):
        res = super(MaintenanceRequest, self).create(vals)
        # res.update_machine_running_time()
        return res
    
    def write(self, vals):
        res = super(MaintenanceRequest, self).write(vals)
        for rec in self:
            if not rec.equipment_id:
                continue
            rec.equipment_id.update_machine_running_time()
        return res

    def unlink(self):
        for rec in self:
            if not rec.equipment_id:
                continue
            rec.equipment_id.update_machine_running_time(rec.id)
        return super(MaintenanceRequest, self).unlink()
