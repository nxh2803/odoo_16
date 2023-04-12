# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class FleetAttendence(models.Model):
    _name = 'fleet.attendence'
    _rec_name = 'equipment_id'
    _order = 'start_date desc, create_date desc'
    _description = 'Điểm danh'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    user_id = fields.Many2one('res.users', string='lái xe', required=True)
    equipment_id = fields.Many2one('maintenance.equipment', string='Xe')
    location_id = fields.Many2one('equipment.location', 'Vị trí bắt đầu làm việc')
    location_dest_id = fields.Many2one('equipment.location', 'Vị trí kết thúc làm việc')
    date_process = fields.Date(string='Ngày thực hiện', required=True)
    odometer_start = fields.Integer('Số giờ máy xuất phát')
    odometer_end = fields.Integer('Số giờ máy điểm đích')
    state = fields.Selection([
        ('1_draft', 'Đang Chờ'),
        ('2_confirm', 'Bắt đầu'),
        ('3_done', 'Kết thúc')
    ], string='Trạng thái', default='1_draft')
    note = fields.Text(string='Ghi chú')
    start_date = fields.Datetime(string='Bắt đầu', readonly=True)
    end_date = fields.Datetime(string='Kết thúc', readonly=True)
    attachment_ids = fields.One2many('ir.attachment', 'res_id', string='Attachments')
    lat = fields.Char(string='Lat')
    long = fields.Char(string='Long')
    google_map = fields.Char(string='Vị trí thực tế', compute='_compute_google_map', store=True)

    @api.depends("lat", "long")
    def _compute_google_map(self):
        for rec in self:
            if not rec.lat or not rec.long:
                rec.google_map = False
            else:
                rec.google_map = f'http://maps.google.com/maps?z=12&t=m&q=loc:{rec.lat}+{rec.long}'

    def create_attendence_images(self, images):
        for image in images:
            self.env['ir.attachment'].create({
                'name': str(self.id),
                'type': 'url',
                'url': image,
                'res_model': 'fleet.attendence',
                'res_id': self.id,
            })
        return True

    def do_start_trip(self):
        self.start_date = fields.Datetime.now()
        self.state = '2_confirm'

    def do_end_trip(self):
        self.end_date = fields.Datetime.now()
        self.state = '3_done'

    def do_start(self, odometer_start, location, images):
        self.do_start_trip()
        self.odometer_start = odometer_start
        self.location_id = location
        if images:
            self.create_attendence_images(images)

    def do_end(self, odometer_end, location, images):
        self.do_end_trip()
        self.odometer_end = odometer_end
        self.location_id = location
        if images:
            self.create_attendence_images(images)

    def update_machine_location(self):
        for rec in self:
            location = rec.location_dest_id or rec.location_id
            if location:
                equipment_id = rec.env['maintenance.equipment'].sudo().search([("id", "=", rec.equipment_id.id)])
                if equipment_id:
                    equipment_id.write({'location_id': location.id})

    # def update_machine_attendence_time(self):
    #     for rec in self:
    #         if not rec.equipment_id:
    #             continue
            # if rec.equipment_id.machine_attendence_time and rec.odometer_end <= rec.equipment_id.machine_attendence_time:
            #     continue
        #     rec.equipment_id.update_machine_attendence_time()
        # return True

    @api.model
    def create(self, vals):
        res = super(FleetAttendence, self).create(vals)
        res.update_machine_location()
        # if res.equipment_id:
        #     res.equipment_id.update_machine_attendence_time()
        return res

    def write(self, vals):
        res =super(FleetAttendence, self).write(vals)
        location = vals.get("location_dest_id") or vals.get("location_id")
        odometer_end = vals.get("odometer_end")
        for rec in self:
            if location:
                rec.update_machine_location()
            if odometer_end and rec.equipment_id:
                rec.equipment_id.update_machine_attendence_time()
        return res

    def unlink(self):
        for rec in self:
            if not rec.equipment_id:
                continue
            rec.equipment_id.update_machine_attendence_time(rec.id)
        return super(FleetAttendence, self).unlink()


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'
    _order = 'name'
