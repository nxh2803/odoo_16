from odoo import api, fields, models, _


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    equipment_id = fields.Many2one('maintenance.equipment', string='Thiết bị')


class EquipmentLocation(models.Model):
    _name = 'equipment.location'
    _description = 'Địa điểm'
    _order = 'name'

    name = fields.Char(string='Tên địa điểm', required=True)

    location = fields.Char(string='Tọa độ')

    district_id = fields.Many2one('res.country.district', string='District', domain="[('state_id', '=', state_id)]")
    ward_id = fields.Many2one('res.country.ward', string='Ward', domain="[('district_id', '=', district_id)]")
    state_id = fields.Many2one("res.country.state", string='State', ondelete='restrict', copy=False,
                               domain="[('country_id', '=', country_id)]")
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict', copy=False, default=241)