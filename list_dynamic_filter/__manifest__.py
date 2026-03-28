{
    "name": "Dynamic List Filters",
    "version": "18.0.1.0.2",
    "summary": "Configure dynamic filters for any list view",
    "author": "Mihran Thalhath",
    "website": "https://www.mihranthalhath.com",
    "license": "AGPL-3",
    "category": "Web",
    "depends": [
        "web",
        "base",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/list_filter_config_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "list_dynamic_filter/static/**/*.js",
            "list_dynamic_filter/static/**/*.scss",
        ],
    },
    "images": ["static/description/images/list_view_filter_19.png"],
    "installable": True,
    "auto_install": False,
    "application": False,
}
