# -*- coding: utf-8 -*-
# Part of Alien Software - aliensoftware.dev
{
    'name': 'Viet Nam Address',
    'category': 'ALSW',
    'summary': 'Viet Nam Address',
    'description': """
I) Description
Viet Nam Address
\t[+] Province\City
\t[+] District
\t[+] Ward
    """,
    'license': 'AGPL-3',
    'version': '14.0.1.1',
    'depends': [
        'base',
    ],
    'data': [
        'data/district.xml',
        'data/ward.xml',
        'views/province.xml',
        'views/district.xml',
        'views/ward.xml',
        'views/menu.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}