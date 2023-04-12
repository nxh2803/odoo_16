{
    'name': 'Odoo Rest Api',
    'summary': 'Odoo Rest Api',
    'description': 'Odoo Rest Api',
    'category': 'api',
    'version': '14.0.1.0.0',
    'depends': ['web', 'base'],
    'external_dependencies': {
        'python': ['simplejson', 'redis']
    },
    'data': [
        'data/ir_configparameter_data.xml',
        'data/ir_cron_data.xml',
        'security/ir.model.access.csv',
        'views/ir_model_view.xml',
    ],
    'application': True,
    'installable': True,
}
