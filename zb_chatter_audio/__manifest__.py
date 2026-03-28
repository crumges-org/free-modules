# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2025 ZestyBeanz Technologies.
#    (http://wwww.zbeanztech.com)
#    contact@zbeanztech.com
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    "name": "Chatter Audio Message",
    "summary": """
        Chatter Audio Message.
    """,
    "version": "18.0.0.1",
    "description": """
        Chatter Audio Message
    """,    
    "author": 'ZestyBeanz Technologies',
    "maintainer": 'ZestyBeanz Technologies',
    "support": 'support@zbeanztech.com',
    "license": 'LGPL-3',
    "website": "http://www.zbeanztech.com/",
    "category": "Discuss",
    'icon': "/zb_chatter_audio/static/description/icon.png",
    'images': ['static/description/banners/banner.gif',],
    "depends": [
        "mail",
    ],
    "data": [],
    "assets": {
        "web.assets_backend": [
            "/zb_chatter_audio/static/src/js/*.*",
        ],
    },
    "installable": True,
    "application": True,
}
