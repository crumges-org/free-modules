{
    "name": "Project Kanban Pro",
    "version": "18.0.1.0.0",
    "summary": "Jira-style productivity kanban for Project tasks",
    "author": "TwenTIC",
    "website": "https://www.twentic.com",
    "category": "Project",
    "license": "LGPL-3",
    "depends": [
        "project",
        "mail",
        "web",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/kanban_rule_views.xml",
        "views/res_config_settings_views.xml",
        "views/project_task_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "project_kanban_pro/static/src/js/*.js",
            "project_kanban_pro/static/src/xml/*.xml",
            "project_kanban_pro/static/src/scss/*.scss",
        ],
    },
    'images': ['static/description/main_screenshot.png'],
    "installable": True,
    "application": False,
    "auto_install": False,
}
