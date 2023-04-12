
from .main import *


class ControllerREST(http.Controller):
    
    def define_schema_params(self, request, model_name, method):
        schema = pre_schema = default_vals = None
        cr, uid = request.cr, request.session.uid
        Model = request.env['ir.model'].sudo().search([('model', '=', model_name)], limit=1)
        ResModel = request.env(cr, uid)[model_name]
        if Model.rest_api_used:
            model_available = True
            read_schema_all = bool(request.env['ir.config_parameter'].sudo().get_param(
                'rest_api.rest_api_read_schema_all'))
            if method == 'read_all':
                # if read_schema_all:
                #     schema = tuple(ResModel._fields.keys())
                #     pre_schema = False
                # else:
                if 'name' in ResModel._fields.keys():
                    schema = ('id', 'name',)
                else:
                    schema = ('id',)
                pre_schema = False
            elif method == 'read_one':
                schema = tuple(ResModel._fields.keys())
                pre_schema = False
            elif method == 'create_one':
                if read_schema_all:
                    schema = tuple(ResModel._fields.keys())
                    pre_schema = False
                else:
                    schema = ('id',)
                    pre_schema = False
                default_vals = {}
        else:
            model_available = False
        return model_available, schema, pre_schema, default_vals
    
    # Read all (with optional filters, offset, limit, order, exclude_fields, include_fields):
    @http.route('/api/<string:model_name>', methods=['GET'], type='http', auth='none', cors=rest_cors_value)
    @check_permissions
    def api_model_name_GET(self, model_name, **kw):
        model_available, schema, pre_schema, _ = self.define_schema_params(request, model_name, 'read_all')
        if not model_available:
            return error_response_501_model_not_available()
        return wrap_resource_read_all(
            modelname=model_name,
            default_domain=[],
            success_code=200,
            OUT_fields=schema,
            pre_schema=pre_schema)
    
    # Read one (with optional exclude_fields, include_fields):
    @http.route('/api/<string:model_name>/<id>', methods=['GET'], type='http', auth='none', cors=rest_cors_value)
    @check_permissions
    def api_model_name_id_GET(self, model_name, id, **kw):
        model_available, schema, pre_schema, _ = self.define_schema_params(request, model_name, 'read_one')
        if not model_available:
            return error_response_501_model_not_available()
        return wrap_resource_read_one(
            modelname=model_name,
            id=id,
            success_code=200,
            OUT_fields=schema,
            pre_schema=pre_schema,)
    
    # Create one:
    @http.route('/api/<string:model_name>', methods=['POST'], type='http', auth='none',
                cors=rest_cors_value, csrf=False)
    @check_permissions
    def api_model_name_POST(self, model_name, **kw):
        model_available, schema, _, default_vals = self.define_schema_params(request, model_name, 'create_one')
        if not model_available:
            return error_response_501_model_not_available()
        return wrap_resource_create_one(
            modelname=model_name,
            default_vals=default_vals,
            success_code=200,
            OUT_fields=schema)
    
    # Update one:
    @http.route('/api/<string:model_name>/<id>', methods=['PUT'], type='http', auth='none',
                cors=rest_cors_value, csrf=False)
    @check_permissions
    def api_model_name_id_PUT(self, model_name, id, **kw):
        return wrap_resource_update_one(
            modelname=model_name,
            id=id,
            success_code=200)
    
    # Delete one:
    @http.route('/api/<string:model_name>/<id>', methods=['DELETE'], type='http', auth='none',
                cors=rest_cors_value, csrf=False)
    @check_permissions
    def api_model_name_id_DELETE(self, model_name, id, **kw):
        return wrap_resource_delete_one(modelname=model_name, id=id, success_code=200)
    
    # Call method (with optional parameters):
    @http.route('/api/<string:model_name>/<id>/<method>', methods=['PUT'], type='http', auth='none',
                cors=rest_cors_value, csrf=False)
    @check_permissions
    def api_model_name_id_method_PUT(self, model_name, id, method, **kw):
        return wrap_resource_call_method(
            modelname=model_name,
            id=id,
            method=method,
            success_code=200)
