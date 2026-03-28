# -*- coding: utf-8 -*-
# Copyright 2024 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)
{
    'name': 'Mexican Partner Address',
    'countries': ['mx'],
    'version': '18.0.1.0.2',
    'category': 'Soltein SA de CV/Hidden',
    'license': 'LGPL-3',
    'author': 'Soltein SA de CV',
    'website': 'https://soltein.mx/',
    'depends': ['base_setup', 'base_address_extended', 'l10n_mx_hr'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_employee.xml',
        'views/res_company.xml',
        'views/res_partner.xml',
        'views/res_country.xml',
        'views/res_locality.xml',
        'views/res_city_district_views.xml',
        'views/menus.xml',
        'data/res_country.xml',
    ],
    'installable': True,
    'post_init_hook': 'post_init_hook',
    'summary': 'Solt L10n Mx Partner Address for Odoo',
    'description': '''
Mexican Partner Address
-----------------------

This module extends the partner address fields to include Mexican-specific address fields.

Key Features:
* Colony field for Mexican addresses
* Locality field for Mexican addresses
* Integration with other Mexican localization modules

For more information, please contact Soltein SA de CV.
''',
}
