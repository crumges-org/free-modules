{
    'name': "HR Seniority",
    'author': 'Bac Ha Software',
    'category': 'HR',
    'version': '1.0',
    'summary': 'Add seniority to employee',
    'description': "Change note name when changing memo",
    'depends': ['base', 'hr_contract'],
    'data': [
        'views/seniority.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3'
}