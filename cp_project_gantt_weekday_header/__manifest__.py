# -*- coding: utf-8 -*-
#
#  ┌────────────────────────────────────────────────────────────────────┐
#  │   Developed by: CHEF PIXEL                                         │
#  │   Website: https://chef-pixel.fr                                   │
#  │   Support: hello@chef-pixel.fr                                     │
#  │   Description: Project Gantt - Show Weekday in Header              │
#  └────────────────────────────────────────────────────────────────────┘
#
#  📅 Show weekday names in Gantt view headers

{
    "name": "Project Gantt - Weekday Header",
    "version": "18.0.1.0.0",
    "summary": "Enhances Gantt view with full weekday names in group headers",
    "description": """
        Project Gantt - Weekday Header
        ==============================

        Gantt View Enhancement:
        --------------------------
        - Displays full weekday in Gantt view group headers
        - Format: Thursday, 10 July 2025

        Ideal for:
        - Project managers and planners
        - Gantt users who want clearer temporal context
    """,
    "author": "CHEF PIXEL",
    "maintainer": "CHEF PIXEL",
    "support": "support@chef-pixel.fr",
    "company": "CHEF PIXEL",
    "website": "https://www.chef-pixel.fr",
    "category": "Project",
    "license": "LGPL-3",
    "depends": ["industry_fsm", "web_gantt"],
    "data": [],
    "assets": {
        "web.assets_backend_lazy": [
            "cp_project_gantt_weekday_header/static/src/**/*",
        ],
    },
    "images": ["static/description/banner.png"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
