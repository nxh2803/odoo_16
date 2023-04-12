{
    'name': 'Inventory Report',
    'summary': 'Inventory Report',
    'description': 'Inventory Report',
    'category': 'Inventory',
    'version': '14.0.1.0.0',
    'depends': ['maintenance_custom', 'uom'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/inventory_report.xml',
        'report/inventory_report.xml',
    ],
    'application': True,
}
