# -*- coding: utf-8 -*-
import functools
import hashlib
import logging
import os
from ast import literal_eval
try:
    import simplejson as json
except ImportError:
    import json
import base64
from datetime import date, datetime, timedelta

import werkzeug.wrappers

import odoo
from odoo import http, SUPERUSER_ID, models, fields
from odoo.http import request# OpenERPSession
from odoo.modules.registry import Registry
from psycopg2.extensions import ISOLATION_LEVEL_READ_COMMITTED


def get_fields_values_from_model(modelname, domain, fields_list, offset=0, limit=None, order=None, pre_schema=True):
    cr, uid = request.cr, request.session.uid
    cr._cnx.set_isolation_level(ISOLATION_LEVEL_READ_COMMITTED)
    Model = request.env(cr, uid)[modelname]

    records = Model.search(domain, offset=offset, limit=limit, order=order)
    if not records:
        return []
    result = []
    for record in records:
        result += [get_fields_values_from_one_record(record, fields_list, pre_schema=pre_schema)]
    
    return result


def get_fields_values_from_one_record(record, fields_list, pre_schema=True):
    if not record:
        return None
    result = {}
    for field in fields_list:
        if type(field) == str:
            val = record[field]
            if pre_schema:
                # If many2one _plane_ field
                try:
                    val = val.id
                except:
                    pass
            
            # Convert Date/Datetime values to (old) string representation
            if isinstance(val, date):
                if isinstance(val, datetime):
                    val = fields.Datetime.to_string(val + timedelta(hours=7))
                else:
                    val = fields.Date.to_string(val+ timedelta(hours=7))
            
            if not isinstance(val, models.BaseModel):
                result[field] = val  if (val or '0' in str(val))  else None
            # for flat response:
            else:
                result[field] = record[field].ids or None
            if not pre_schema and isinstance(record[field], models.BaseModel) and record[field]:
                if record.env[record._name]._fields[field].type == 'many2one':
                    result[field] = {'id': record[field].id}
                    try:
                        result[field]['name'] = record[field].name
                    except:
                        pass
        else:
            # Sample for One2many field: ('bank_ids', [('id', 'acc_number', 'bank_bic')])
            f_name, f_list = field[0], field[1]
            
            if type(f_list) == list:
                # Many (list of) records
                f_list = f_list[0]
                result[f_name] = []
                recs = record[f_name]
                for rec in recs:
                    result[f_name] += [get_fields_values_from_one_record(rec, f_list)]
            else:
                # One record
                rec = record[f_name]
                # protection against only one item without a comma
                if type(f_list) == str:
                    f_list = (f_list,)
                result[f_name] = get_fields_values_from_one_record(rec, f_list)
            
    return result


def convert_values_from_jdata_to_vals(modelname, jdata, creating=True):
    cr, uid = request.cr, request.session.uid
    Model = request.env(cr, uid)[modelname]
    
    x2m_fields = [f  for f in jdata  if type(jdata[f])==list]
    f_props = Model.fields_get(x2m_fields)
    
    vals = {}
    for field in jdata:
        val = jdata[field]
        if type(val) != list:
            vals[field] = val
        else:
            # x2many
            # Sample for One2many field:
            # 'bank_ids': [{'acc_number': '12345', 'bank_bic': '6789'}, {'acc_number': '54321', 'bank_bic': '9876'}]
            vals[field] = []
            field_type = f_props[field]['type']
            # if updating of 'many2many'
            if (not creating) and (field_type == 'many2many'):
                # unlink all previous 'ids'
                vals[field].append((5,))
            
            for jrec in val:
                rec = {}
                for f in jrec:
                    rec[f] = jrec[f]
                
                if field_type == 'one2many':
                    if creating:
                        vals[field].append((0, 0, rec))
                    else:
                        if 'id' in rec:
                            id = rec['id']
                            del rec['id']
                            if len(rec):
                                # update record
                                vals[field].append((1, id, rec))
                            else:
                                # remove record
                                vals[field].append((2, id))
                        else:
                            # create record
                            vals[field].append((0, 0, rec))
                
                elif field_type == 'many2many':
                    # link current existing 'id'
                    vals[field].append((4, rec['id']))
    return vals


def wrap_resource_read_all(modelname, default_domain, success_code, OUT_fields, pre_schema=True, search_more=True, order_data=False):
    # Get request parameters from url
    args = {}
    for key, val in request.httprequest.args.items():
        try: val = literal_eval(val)
        except: pass
        args[key] = val
    # Get request parameters from body
    try:
        body = json.loads(request.httprequest.data)
    except:
        body = {}
    # Merge all parameters with body priority
    jdata = args.copy()
    jdata.update(body)
    # Default filter
    domain = default_domain or []
    # Get additional parameters
    if 'filters' in jdata:
        domain += jdata['filters']
    if 'offset' in jdata:
        offset = jdata['offset']
    else:
        offset = 0
    if 'limit' in jdata:
        limit = jdata['limit']
    else:
        limit = None
    if 'order' in jdata:
        order = jdata['order']
    elif order_data:
        order = order_data
    else:
        order = None
    # protection against only one item without a comma
    if type(OUT_fields) == str:
        OUT_fields = (OUT_fields,)
    # Dynamically exclude fields (from predefined schema)
    exclude_fields = jdata.get('exclude_fields')
    if exclude_fields:
        if type(exclude_fields) == str:
            exclude_fields = (exclude_fields,)
        if {'*', '__all_fields__'}.intersection(set(exclude_fields)):
            OUT_fields = ('id',)
        else:
            new_OUT_fields = ()
            for ff in OUT_fields:
                fk = ff[0] if type(ff) == tuple else ff
                if fk not in exclude_fields:
                    new_OUT_fields += (ff,)
            OUT_fields = new_OUT_fields
    # Dynamically append additional fields
    ##################################################################
    # include_fields = jdata.get('include_fields')
    # if include_fields:
    #     for fields in OUT_fields:
    #         if fields not in jdata.get('include_fields'):
    #             continue
    #         cr, uid = request.cr, request.session.uid
    #         Model = request.env(cr, uid)[modelname]
    #         sub_modelname = Model[fields]
    #         f_props = Model.fields_get(fields)
    #         try:
    #             field_type = f_props[fields]['type']
    #             if field_type in ['many2many', 'one2many']:
    #                 list_field = tuple(sub_modelname._fields.keys())
    #                 OUT_fields += ((fields, [list_field],),)
    #         except:
    #             continue
    include_fields = jdata.get('include_fields')
    if include_fields:
        if type(include_fields) == str:
            include_fields = (include_fields,)
        OUT_fields += tuple(include_fields)
    #################################################################
    # Reading object's data:
    try:
        Objects_Data = get_fields_values_from_model(modelname=modelname, domain=domain, offset=offset, limit=limit,
                                                    order=order, fields_list=OUT_fields, pre_schema=pre_schema)
    except Exception as e:
        return error_response_409_not_read_object_in_odoo(repr(e))

    if len(Objects_Data) > 1 and not search_more:
        return error_response_409_more_than_one_in_odoo()
    return successful_response(status=success_code,
                               dict_data={
                                   'count': len(Objects_Data),
                                   'results': Objects_Data})


def wrap_resource_read_one(modelname, id, success_code, OUT_fields, pre_schema=True):
    # Default search field
    search_field = 'id'
    search_field_type = 'integer'
    # Get request parameters from url
    args = {}
    for key, val in request.httprequest.args.items():
        try: val = literal_eval(val)
        except: pass
        args[key] = val
    # Get request parameters from body
    try:
        body = json.loads(request.httprequest.data)
    except:
        body = {}
    # Merge all parameters with body priority
    jdata = args.copy()
    jdata.update(body)
    # Is there a search field?
    if jdata.get('search_field'):
        search_field = jdata['search_field']
        # Get search field type:
        cr, uid = request.cr, request.session.uid
        Model = request.env(cr, uid)[modelname]
        search_field_type = Model.fields_get([search_field])[search_field]['type']
    # Сheck id
    obj_id = None
    if search_field_type == 'integer':
        try: obj_id = int(id)
        except: pass
    else:
        obj_id = id
    if not obj_id:
        return error_response_400_invalid_object_id()
    # protection against only one item without a comma
    if type(OUT_fields) == str:
        OUT_fields = (OUT_fields,)
    # Dynamically exclude fields (from predefined schema)
    exclude_fields = jdata.get('exclude_fields')
    if exclude_fields:
        if type(exclude_fields) == str:
            exclude_fields = (exclude_fields,)
        if {'*', '__all_fields__'}.intersection(set(exclude_fields)):
            OUT_fields = ('id',)
        else:
            new_OUT_fields = ()
            for ff in OUT_fields:
                fk = ff[0] if type(ff) == tuple else ff
                if fk not in exclude_fields:
                    new_OUT_fields += (ff,)
            OUT_fields = new_OUT_fields
    # Dynamically append additional fields
    ##################################################################
    include_fields = jdata.get('include_fields')
    # if include_fields:
    #     for fields in OUT_fields:
    #         if fields not in jdata.get('include_fields'):
    #             continue
    #         cr, uid = request.cr, request.session.uid
    #         Model = request.env(cr, uid)[modelname]
    #         sub_modelname = Model[fields]
    #         f_props = Model.fields_get(fields)
    #         try:
    #             field_type = f_props[fields]['type']
    #             if field_type in ['many2many', 'one2many']:
    #                 list_field = tuple(sub_modelname._fields.keys())
    #                 OUT_fields += ((fields, [list_field],),)
    #         except:
    #             continue
                # include_fields = jdata.get('include_fields')
    if include_fields:
        if type(include_fields) == str:
            include_fields = (include_fields,)
        OUT_fields += tuple(include_fields)
    ######################################################################
    # Reading object's data:
    try:
        Object_Data = get_fields_values_from_model(
            modelname=modelname,
            domain=[(search_field, '=', obj_id)],
            fields_list=OUT_fields,
            pre_schema=pre_schema,
        )
    except Exception as e:
        return error_response_409_not_read_object_in_odoo(repr(e))
    if Object_Data:
        return successful_response(success_code, Object_Data[0])
    else:
        return error_response_404_not_found_object_in_odoo()


def wrap_resource_create_one(modelname, default_vals, success_code, OUT_fields=('id',)):
    # Get request parameters from url
    args = {}
    for key, val in request.httprequest.args.items():
        try:
            val = literal_eval(val)
        except:
            pass
        args[key] = val
    # Get request parameters from body
    try:
        body = request.httprequest.form.to_dict()
        # body = json.loads(request.httprequest.data)
    except:
        body = {}
    # Merge all parameters with body priority
    jdata = args.copy()
    jdata.update(body)
    # Convert json data into Odoo vals:
    vals = convert_values_from_jdata_to_vals(modelname, jdata)
    # Set default fields:
    if default_vals:
        vals.update(default_vals)
    # Try create new object
    cr, uid = request.cr, request.session.uid
    cr._cnx.set_isolation_level(ISOLATION_LEVEL_READ_COMMITTED)
    Model = request.env(cr, uid)[modelname]
    try:
        new_id = Model.create(vals).id
        cr.commit()
        cr.close()
        request._cr = None
        # protection against only one item without a comma
        if type(OUT_fields) == str:
            OUT_fields = (OUT_fields,)
        # Handling of archived (non active) Odoo record:
        domain = [('id', '=', new_id)]
        if 'active' in vals:
            domain += [('active', '=', vals.get('active'))]
        
        response_json = get_fields_values_from_model(
            modelname=modelname,
            domain=domain,
            fields_list=OUT_fields
        )[0]
        return successful_response(success_code, response_json)
    except Exception as e:
        odoo_error = repr(e)
        if not cr.closed:
            cr.close()
            request._cr = None
        return error_response_409_not_created_object_in_odoo(odoo_error)


def wrap_resource_update_one(modelname, id, success_code):
    # Сheck id
    obj_id = None
    try:
        obj_id = [int(id)]
    except:
        try:
            obj_id = list(map(int, id.split(',')))
        except:
            pass
    if not obj_id:
        return error_response_400_invalid_object_id()
    # Get request parameters from url
    args = {}
    for key, val in request.httprequest.args.items():
        try:
            val = literal_eval(val)
        except:
            pass
        args[key] = val
    # Get request parameters from body
    try:
        body = json.loads(request.httprequest.data)
    except:
        body = {}
    # Merge all parameters with body priority
    jdata = args.copy()
    jdata.update(body)
    # Convert json data into Odoo vals:
    vals = convert_values_from_jdata_to_vals(modelname, jdata, creating=False)
    # Try update the object
    cr, uid = request.cr, request.session.uid
    cr._cnx.set_isolation_level(ISOLATION_LEVEL_READ_COMMITTED)
    Model = request.env(cr, uid)[modelname]
    try:
        Model.browse(obj_id).write(vals)
        cr.commit()
        cr.close()
        request._cr = None
        return successful_response(success_code, {})
    except Exception as e:
        odoo_error = repr(e)
        if not cr.closed:
            cr.close()
            request._cr = None
        return error_response_409_not_updated_object_in_odoo(odoo_error)


def wrap_resource_delete_one(modelname, id, success_code):
    # Сheck id
    obj_id = None
    try:
        obj_id = [int(id)]
    except:
        try:
            obj_id = list(map(int, id.split(',')))
        except:
            pass
    if not obj_id:
        return error_response_400_invalid_object_id()
    # Try delete the object
    cr, uid = request.cr, request.session.uid
    cr._cnx.set_isolation_level(ISOLATION_LEVEL_READ_COMMITTED)
    Model = request.env(cr, uid)[modelname]
    try:
        Model.browse(obj_id).unlink()
        cr.commit()
        cr.close()
        request._cr = None
        return successful_response(success_code, {})
    except Exception as e:
        odoo_error = repr(e)
        if not cr.closed:
            cr.close()
            request._cr = None
        return error_response_409_not_deleted_object_in_odoo(odoo_error)


def wrap_resource_call_method(modelname, id, method, success_code):
    try:
        obj_id = list(map(int, id.split(',')))
    except:
        obj_id = None
    if not obj_id:
        return error_response_400_invalid_object_id()
    # Get request parameters from url
    args = {}
    for key, val in request.httprequest.args.items():
        try: val = literal_eval(val)
        except: pass
        args[key] = val
    # Get request parameters from body
    try:
        body = json.loads(request.httprequest.data)
    except:
        body = {}
    # Merge all parameters with body priority
    jdata = args.copy()
    jdata.update(body)
    # Try call method of object
    cr, uid = request.cr, request.session.uid
    cr._cnx.set_isolation_level(ISOLATION_LEVEL_READ_COMMITTED)
    Model = request.env(cr, uid)[modelname]
    try:
        # Validate method of model
        Method_of_model = getattr(Model.browse(obj_id), method, None)
        if callable(Method_of_model):
            # Execute method of object
            res = Method_of_model(**jdata)
            cr.commit()
            cr.close()
            request._cr = None
            if isinstance(res, bytes) and res.startswith(b'%PDF-'):
                res = base64.encodebytes(res).decode('utf-8')
            elif isinstance(res, models.Model):
                try:
                    res = (res._name, res.ids)
                except:
                    res = (res._name, [])
            return successful_response(success_code, res)
        else:
            return error_response_501_method_not_exist_in_odoo()
    except Exception as e:
        odoo_error = repr(e)
        if not cr.closed:
            cr.close()
            request._cr = None
        return error_response_409_not_called_method_in_odoo(odoo_error)


def wrap_report_call_method(method, success_code):
    # Get request parameters from url
    args = {}
    for key, val in request.httprequest.args.items():
        try: val = literal_eval(val)
        except: pass
        args[key] = val
    # Get request parameters from body
    try:
        body = json.loads(request.httprequest.data)
    except:
        body = {}
    # Merge all parameters with body priority
    jdata = args.copy()
    jdata.update(body)
    # Try call method of report
    cr, uid = request.cr, request.session.uid
    cr._cnx.set_isolation_level(ISOLATION_LEVEL_READ_COMMITTED)
    # Attention! Current implemented report methods: 'get_pdf'.
    if method == 'get_pdf' and 'report_name' in jdata and 'ids' in jdata:
        try:
            report = request.env(cr, uid)['ir.actions.report']._get_report_from_name(jdata['report_name'])
            pdf = report._render_qweb_pdf(jdata['ids'])[0]
            res = base64.encodebytes(pdf).decode('utf-8')
            return successful_response(success_code, res)
        except Exception as e:
            odoo_error = repr(e)
            return error_response_409_not_called_method_in_odoo(odoo_error)
    else:
        error_descrip = "Report method not implemented!"
        error = 'report_method_not_implemented'
        return error_response(501, error, error_descrip)


def check_permissions(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        
        # Get access token from http header
        access_token = request.httprequest.headers.get('access_token')
        if not access_token:
            error_descrip = "No access token was provided in request header!"
            error = 'no_access_token'
            return error_response(400, error, error_descrip)
        
        # Validate access token
        access_token_data = token_store.fetch_by_access_token(request.env, access_token)
        if not access_token_data:
            return error_response_401_invalid_token()
        
        # Set session UID from current access token
        request.session.uid = access_token_data['user_id']
        # Set user's context
        user_context = request.env(request.cr, request.session.uid)['res.users'].context_get().copy()
        user_context['uid'] = request.session.uid
        request.session.context = request.context = user_context
        
        # The code, following the decorator
        return func(self, *args, **kwargs)
    return wrapper


def successful_response(status, dict_data):
    data_response = {
        'success': True,
        'data': dict_data,
        'errorData': {}
    }
    resp = werkzeug.wrappers.Response(
        status=status,
        content_type='application/json; charset=utf-8',
        #headers = None,
        response=json.dumps(data_response, ensure_ascii=u_escape_characters_for_unicode_in_responses))
    # Remove cookie session
    resp.set_cookie = lambda *args, **kwargs: None
    return resp


def error_response(status, error, error_descrip):
    resp = werkzeug.wrappers.Response(
        status=status,
        content_type='application/json; charset=utf-8',
        #headers = None,
        response=json.dumps({
            'success': False,
            'data': [],
            'errorData': {
                'error': error,
                'error_descrip': error_descrip,
            }
        }, ensure_ascii=u_escape_characters_for_unicode_in_responses),
    )
    # Remove cookie session
    resp.set_cookie = lambda *args, **kwargs: None
    return resp


def error_response_400_invalid_object_id():
    error_descrip = "Invalid object 'id'!"
    error = 'invalid_object_id'
    return error_response(400, error, error_descrip)


def error_response_401_invalid_token():
    error_descrip = "Token is expired or invalid!"
    error = 'invalid_token'
    return error_response(401, error, error_descrip)


def error_response_404_not_found_object_in_odoo():
    error_descrip = "Not found object(s) in Odoo!"
    error = 'not_found_object_in_odoo'
    return error_response(404, error, error_descrip)


def error_response_409_not_read_object_in_odoo(odoo_error):
    error_descrip = "Not read object in Odoo! ERROR: %s" % odoo_error
    error = 'not_read_object_in_odoo'
    return error_response(409, error, error_descrip)


def error_response_409_more_than_one_in_odoo():
    error_descrip = "Found more than 1 device"
    error = 'found_more_than_one_device'
    return error_response(409, error, error_descrip)


def error_response_409_not_created_object_in_odoo(odoo_error):
    error_descrip = "Not created object in Odoo! ERROR: %s" % odoo_error
    error = 'not_created_object_in_odoo'
    return error_response(409, error, error_descrip)


def error_response_409_not_updated_object_in_odoo(odoo_error):
    error_descrip = "Not updated object in Odoo! ERROR: %s" % odoo_error
    error = 'not_updated_object_in_odoo'
    return error_response(409, error, error_descrip)


def error_response_409_not_deleted_object_in_odoo(odoo_error):
    error_descrip = "Not deleted object in Odoo! ERROR: %s" % odoo_error
    error = 'not_deleted_object_in_odoo'
    return error_response(409, error, error_descrip)


def error_response_409_not_called_method_in_odoo(odoo_error):
    error_descrip = "Not called method in Odoo! ERROR: %s" % odoo_error
    error = 'not_called_method_in_odoo'
    return error_response(409, error, error_descrip)


def error_response_501_method_not_exist_in_odoo():
    error_descrip = "Method not exist in Odoo!"
    error = 'method_not_exist_in_odoo'
    return error_response(501, error, error_descrip)

def error_response_501_model_not_available():
    error_descrip = "This model is not available in REST API!"
    error = 'model_not_available'
    return error_response(501, error, error_descrip)


def generate_token(length=40):
    random_data = os.urandom(100)
    hash_gen = hashlib.new('sha512')
    hash_gen.update(random_data)
    return hash_gen.hexdigest()[:length]


# Read system parameters and setup token store:
db_name = odoo.tools.config.get('db_name')
if not db_name:
    print("ERROR: To proper setup OAuth2 and Token Store - it's necessary to set the "
          "parameter 'db_name' in Odoo config file!")
else:
    # Read system parameters...
    registry = Registry(db_name)
    with registry.cursor() as cr:
        cr.execute("SELECT value FROM ir_config_parameter \
            WHERE key = 'rest_api.cors_parameter_value_in_all_routes'")
        res = cr.fetchone()
        rest_cors_value = res and res[0].strip() or 'null'
        cr.execute("SELECT value FROM ir_config_parameter \
            WHERE key = 'rest_api.u_escape_characters_for_unicode_in_responses'")
        res = cr.fetchone()
        u_escape_characters_for_unicode_in_responses = res and res[0].strip()
        if u_escape_characters_for_unicode_in_responses in ('1', 'True', 'true'):
            u_escape_characters_for_unicode_in_responses = True
        else:
            u_escape_characters_for_unicode_in_responses = False
        # Token store settings:
        cr.execute("SELECT value FROM ir_config_parameter \
            WHERE key = 'rest_api.use_redis_token_store'")
        res = cr.fetchone()
        use_redis_token_store = res and res[0].strip()
        if use_redis_token_store in ('0', 'False', 'None', 'false'):
            use_redis_token_store = False
        if not use_redis_token_store:
            # Setup Simple token store
            from . import simple_token_store
            token_store = simple_token_store.SimpleTokenStore()
        else:
            # Setup Redis token store
            cr.execute("SELECT value FROM ir_config_parameter \
                WHERE key = 'rest_api.redis_host'")
            res = cr.fetchone()
            redis_host = res and res[0]
            cr.execute("SELECT value FROM ir_config_parameter \
                WHERE key = 'rest_api.redis_port'")
            res = cr.fetchone()
            redis_port = res and res[0]
            cr.execute("SELECT value FROM ir_config_parameter \
                WHERE key = 'rest_api.redis_db'")
            res = cr.fetchone()
            redis_db = res and res[0]
            cr.execute("SELECT value FROM ir_config_parameter \
                WHERE key = 'rest_api.redis_password'")
            res = cr.fetchone()
            redis_password = res and res[0]
            if redis_password in ('None', 'False'):
                redis_password = None
            if redis_host and redis_port:
                from . import redis_token_store
                token_store = redis_token_store.RedisTokenStore(
                                        host = redis_host,
                                        port = redis_port,
                                        db = redis_db,
                                        password = redis_password)
            else:
                print("WARNING: It's necessary to RESTART Odoo server after the installation of 'rest_api' module!")
        # Connect REST resources
        from . import resources
        from . import default_universal_controller
