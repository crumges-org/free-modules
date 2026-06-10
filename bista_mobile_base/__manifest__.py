# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Inc.
#    Copyright (C) 2026 (http://www.bistasolutions.com)
#
##############################################################################
{
    "name": "Bista Mobile Base",
    "description": "Bista Mobile Base",
    "version": "18.0.1.0.0",
    "author": "Bista Solutions Inc",
    "website": "http://www.bistasolutions.com",
    "category": "Hidden", # For Technical
    "summary": "Bista Mobile Base for Mobile App APIs",
    "depends": [
        "base",
        # "sale",
        # "delivery",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron_delete_expired_token.xml",
        "data/ir_attachment.xml",
        "data/server_env.xml",
        "views/res_users.xml",
        "views/access_token_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "external_dependencies": {"python": ["PyJWT", "google-auth"]},
    "license": "LGPL-3",
}
