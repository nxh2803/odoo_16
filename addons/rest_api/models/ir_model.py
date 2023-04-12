
from odoo import models, fields


class IrModel(models.Model):
    _inherit = "ir.model"

    rest_api_used = fields.Boolean(string='Use in REST API', default=True)
    # rest_api_read_all_schema = fields.Text(string="'Read all' schema",
    #                                        help="'Read all' predefined response SCHEMA. "
    #                                             "If empty - will return 'id', 'name'.")
    # rest_api_read_one_schema = fields.Text(string="'Read one' schema",
    #                                        help="'Read one' predefined response SCHEMA. "
    #                                             "If empty - will return all fields (not hierarchical).")
    # rest_api_create_one_schema = fields.Text(string="'Create one' response schema",
    #                                          help="'Create one' predefined response SCHEMA. "
    #                                               "If empty - will return 'id'.")
    # rest_api_create_one_defaults = fields.Text(string="'Create one' defaults",
    #                                            help="'Create one' DEFAULTS values (dictionary)")
