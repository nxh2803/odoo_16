# -*- coding: utf-8 -*-
from .main import *
import ast

OUT_maintenance_equipment_read_SUCCESS_CODE = 200

OUT_maintenance_equipment_schema = (
    "id",
    "name",
    "last_request",
    "model",
    "serial_no",
    "code",
    "so_khung",
    "machine_running_time",
    "machine_attendence_time",
    ("message_ids", [(
            "date",
            "body",
            ("author_id", (
                "id",
                "name"
            )),
        )]),
    ("manual_ids", [("id", "image_url")])
)

OUT_maintenance_request_read_SUCCESS_CODE = 200

OUT_maintenance_request_schema = (
    "id",
    "name",
    ("equipment_id", (
        "id",
        "name",
        "model",
        "serial_no",
        "code",
        "so_khung"
    )),
    "request_date",
    ("user_id", (
        "id",
        "name"
    )),
    ("create_uid", (
        "id",
        "name"
    )),
    ("performer_id", (
        "id",
        "name"
    )),
    ("company_id", (
        "id",
        "name"
    )),
    ("maintenance_team_id", (
        "id",
        "name"
    )),
    "note",
    ("stage_id", (
        "id",
        "name"
    )),
    "date_process",
    "schedule_date",
    "machine_running_time",
    ("attachment_ids", [("id", "url", "datas")]),
    ("message_ids", [(
        "date",
        "body",
        ("author_id", (
            "id",
            "name"
        )),
    )]),
)

OUT_model_res_user_create_one_SCHEMA = (
    "id",
    "name",
    "login",
)


OUT_model_res_user_read_one_SCHEMA = (
    "id",
    "name",
    "id",
    "street",
    "street2",
    "city",
    "function",
    ("state_id", (
        "id",
        "name"
    )),
    ("country_id", (
        "id",
        "name",
    )),
    "phone",
)

OUT_fleet_attendence_schema = (
    "id",
    ("user_id", ("id", "name")),
    ("equipment_id", ("id", "name", "model", "serial_no", "code", "so_khung")),
    ("location_id", ("id", "name", "location", ("district_id", ("id", "name")), ("ward_id", ("id", "name")),
                     ("state_id", ("id", "name")), ("country_id", ("id", "name")),)),
    ("location_dest_id", ("id", "name", "location", ("district_id", ("id", "name")), ("ward_id", ("id", "name")),
                     ("state_id", ("id", "name")), ("country_id", ("id", "name")),)),
    "date_process",
    "odometer_start",
    "odometer_end",
    "start_date",
    "end_date",
    "state",
    "note",
)

OUT_fleet_attendence_one_schema = (
    "id",
    ("user_id", ("id", "name")),
    ("equipment_id", ("id", "name", "model", "serial_no", "code", "so_khung")),
    ("location_id", ("id", "name", "location", ("district_id", ("id", "name")), ("ward_id", ("id", "name")),
                     ("state_id", ("id", "name")), ("country_id", ("id", "name")),)),
    ("location_dest_id", ("id", "name", "location", ("district_id", ("id", "name")), ("ward_id", ("id", "name")),
                     ("state_id", ("id", "name")), ("country_id", ("id", "name")),)),
    ("attachment_ids", [("id", "url", "datas")]),
    "date_process",
    "odometer_start",
    "odometer_end",
    "start_date",
    "end_date",
    "state",
    "note",
)

OUT_address_schema = (
    "id",
    "name",
)


OUT_equipment_location_schema = (
    "id", "name", "location",
    ("district_id", ("id", "name")),
    ("ward_id", ("id", "name")),
    ("state_id", ("id", "name")),
    ("country_id", ("id", "name"))
)



OUT_maintenance_equipment_call_method_SUCCESS_CODE = 200


class ControllerREST(http.Controller):

    @http.route('/api/res.users', methods=['POST'], type='http', auth='none', cors=rest_cors_value, csrf=False)
    @check_permissions
    def api_model_res_users_POST(self, **kw):
        company_id = http.request.env.ref('base.main_company').id
        return wrap_resource_create_one(
            modelname='res.users',
            default_vals={'company_id': company_id,
                          'company_ids': [(6, 0, [company_id])]},
            success_code=200,
            OUT_fields=OUT_model_res_user_create_one_SCHEMA
        )

    @http.route('/api/maintenance.equipment', methods=['GET'], type='http', auth='none', cors=rest_cors_value)
    @check_permissions
    def api_maintenance_equipment_GET(self, **kw):
        # domain_fields = ['code', 'so_khung']
        # domain_true = []
        domain = []
        for key, val in request.httprequest.args.items():
            try:
                val = literal_eval(val)
            except:
                pass
            # domain_true.append(key)
            domain += [(key, '=', val)]
        # for fields in domain_fields:
        #     if fields in domain_true:
        #         continue
        #     domain += [(fields, '=', False)]
        return wrap_resource_read_all(
            modelname='maintenance.equipment',
            default_domain=domain or [],
            success_code=OUT_maintenance_equipment_read_SUCCESS_CODE,
            OUT_fields=OUT_maintenance_equipment_schema,
            search_more=False)

    @http.route('/api/maintenance.equipment/<id>', methods=['GET'], type='http', auth='none', cors=rest_cors_value)
    @check_permissions
    def api_maintenance_equipment_id_GET(self, id, **kw):
        return wrap_resource_read_one(
            modelname='maintenance.equipment',
            id=id,
            success_code=OUT_maintenance_equipment_read_SUCCESS_CODE,
            OUT_fields=OUT_maintenance_equipment_schema
        )


    @http.route('/api/maintenance.request', methods=['GET'], type='http', auth='none', cors=rest_cors_value)
    @check_permissions
    def api_maintenance_request_GET(self, **kw):
        domain = []
        for key, val in request.httprequest.args.items():
            try:
                val = literal_eval(val)
            except:
                pass
            domain += [(key, '=', val)]
        return wrap_resource_read_all(
            modelname='maintenance.request',
            default_domain=domain or [],
            success_code=OUT_maintenance_request_read_SUCCESS_CODE,
            OUT_fields=OUT_maintenance_request_schema,
            order_data='date_process desc, create_date desc')

    @http.route('/api/maintenance.equipment/<id>/<method>', methods=['PUT'], type='http', auth='none',
                cors=rest_cors_value,
                csrf=False)
    @check_permissions
    def api_maintenance_equipment_method_PUT(self, id, method, **kw):
        return wrap_resource_call_method(
            modelname='maintenance.equipment',
            id=id,
            method=method,
            success_code=OUT_maintenance_equipment_call_method_SUCCESS_CODE
        )

    @http.route('/api/profile_info', methods=['GET'], type='http', auth='none', csrf=False, cors=rest_cors_value)
    @check_permissions
    def api_model_res_profile_info_id_GET(self, **kw):
        uid = request.session.uid
        return wrap_resource_read_one(
            modelname='res.users',
            id=uid,
            success_code=OUT_maintenance_equipment_call_method_SUCCESS_CODE,
            OUT_fields=OUT_model_res_user_read_one_SCHEMA
        )

    @http.route('/api/attendence', methods=['GET'], type='http', auth='none', csrf=False, cors=rest_cors_value)
    @check_permissions
    def api_model_attendence_info_id_GET(self, **kw):
        domain = []
        for key, val in request.httprequest.args.items():
            try:
                val = literal_eval(val)
            except:
                pass
            if not val:
                continue
            domain += [(key, '=', val)]
        uid = request.session.uid
        domain += [('user_id', '=', uid)]
        return wrap_resource_read_all(
            modelname="fleet.attendence",
            default_domain=domain or [],
            success_code=OUT_maintenance_request_read_SUCCESS_CODE,
            OUT_fields=OUT_fleet_attendence_schema,
            order_data='start_date desc',
        )

    @http.route('/api/attendence/<id>', methods=['GET'], type='http', auth='none', csrf=False, cors=rest_cors_value)
    @check_permissions
    def api_model_attendence_id_GET(self, id, **kw):
        return wrap_resource_read_one(
            modelname="fleet.attendence",
            id=id,
            success_code=OUT_maintenance_request_read_SUCCESS_CODE,
            OUT_fields=OUT_fleet_attendence_one_schema,
        )

    @http.route('/api/attendence', methods=['POST'], type='http', auth='none', csrf=False, cors=rest_cors_value)
    @check_permissions
    def api_model_attendence_info_POST(self, **kw):
        # try:
        uid = request.session.uid
        data = request.httprequest.form.to_dict()
        date_process = False
        if data.get("date_process"):
            date_process = ast.literal_eval(data.get("date_process"))
        vals = {
            'user_id': uid,
            'equipment_id': data.get("equipment_id"),
            'date_process': date_process,
            'odometer_start': data.get("odometer_start"),
            'location_id': data.get("location"),
            'lat': data.get("lat"),
            'long': data.get("long"),
        }
        attendence = http.request.env['fleet.attendence'].create(vals)
        if data.get("images"):
            images = ast.literal_eval(data.get("images"))
            attendence.sudo().create_attendence_images(images)
        attendence.sudo().do_start_trip()
        return successful_response(201, [])

        # except Exception as e:
        #     return error_response(400, "Error", str(e))

    @http.route('/api/attendence_ready', methods=['GET'], type='http', auth='none', csrf=False, cors=rest_cors_value)
    @check_permissions
    def api_model_attendence_ready_info_id_GET(self, **kw):
        domain = []
        domain_equipment = []
        for key, val in request.httprequest.args.items():
            try:
                val = literal_eval(val)
            except:
                pass
            if not val:
                continue
            if key == 'code':
                domain_equipment += [("code", "=", val)]
                continue
            if key == 'so_khung':
                domain_equipment += [("so_khung", "=", val)]
                continue
            domain += [(key, '=', val)]
        uid = request.session.uid
        domain += [('user_id', '=', uid), ('state', '!=', '3_done')]
        if domain_equipment:
            equipment_id = http.request.env['maintenance.equipment'].sudo().search(domain_equipment, limit=1)
            if equipment_id:
                domain += [("equipment_id", "=", equipment_id.id)]
        return wrap_resource_read_all(
            modelname="fleet.attendence",
            default_domain=domain or [],
            success_code=OUT_maintenance_request_read_SUCCESS_CODE,
            OUT_fields=OUT_fleet_attendence_schema,
            order_data='start_date desc',
        )

    @http.route('/api/fleet.attendence/<id>/<method>', methods=['PUT'], type='http', auth='none',
                cors=rest_cors_value,
                csrf=False)
    @check_permissions
    def api_model_fleet_attendence_method_PUT(self, id, method, **kw):
        return wrap_resource_call_method(
            modelname='fleet.attendence',
            id=id,
            method=method,
            success_code=OUT_maintenance_request_read_SUCCESS_CODE
        )

    @http.route('/api/province', methods=['GET'], type='http', auth='none', csrf=False, cors=rest_cors_value)
    @check_permissions
    def api_model_province_info_id_GET(self, **kw):
        return wrap_resource_read_all(
            modelname="res.country.state",
            default_domain=[('country_id', '=', 241)],
            success_code=OUT_maintenance_request_read_SUCCESS_CODE,
            OUT_fields=OUT_address_schema,
        )

    @http.route('/api/district', methods=['GET'], type='http', auth='none', csrf=False, cors=rest_cors_value)
    @check_permissions
    def api_model_district_info_id_GET(self, **kw):
        domain = []
        for key, val in request.httprequest.args.items():
            try:
                val = literal_eval(val)
            except:
                pass
            if not val:
                continue
            domain += [(key, '=', val)]
        return wrap_resource_read_all(
            modelname="res.country.district",
            default_domain=domain or [],
            success_code=OUT_maintenance_request_read_SUCCESS_CODE,
            OUT_fields=OUT_address_schema,
        )

    @http.route('/api/ward', methods=['GET'], type='http', auth='none', csrf=False, cors=rest_cors_value)
    @check_permissions
    def api_model_ward_info_id_GET(self, **kw):
        domain = []
        for key, val in request.httprequest.args.items():
            try:
                val = literal_eval(val)
            except:
                pass
            if not val:
                continue
            domain += [(key, '=', val)]
        return wrap_resource_read_all(
            modelname="res.country.ward",
            default_domain=domain or [],
            success_code=OUT_maintenance_request_read_SUCCESS_CODE,
            OUT_fields=OUT_address_schema,
        )

    @http.route('/api/equipment.location', methods=['GET'], type='http', auth='none', csrf=False, cors=rest_cors_value)
    @check_permissions
    def api_model_equipment_location_id_GET(self, **kw):
        domain = []
        for key, val in request.httprequest.args.items():
            try:
                val = literal_eval(val)
            except:
                pass
            if not val:
                continue
            domain += [(key, '=', val)]
        return wrap_resource_read_all(
            modelname="equipment.location",
            default_domain=domain or [],
            success_code=OUT_maintenance_request_read_SUCCESS_CODE,
            OUT_fields=OUT_equipment_location_schema,
        )

    @http.route('/api/equipment.location', methods=['POST'], type='http', auth='none', cors=rest_cors_value, csrf=False)
    @check_permissions
    def api_model_equipment_location_POST(self, **kw):
        return wrap_resource_create_one(
            modelname='equipment.location',
            default_vals={},
            success_code=200,
            OUT_fields=OUT_equipment_location_schema
        )

    @http.route('/api/fleet.attendence/<id>/<method>', methods=['PUT'], type='http', auth='none',
                cors=rest_cors_value,
                csrf=False)
    @check_permissions
    def api_model_fleet_attendence_method_PUT(self, id, method, **kw):
        return wrap_resource_call_method(
            modelname='fleet.attendence',
            id=id,
            method=method,
            success_code=200
        )