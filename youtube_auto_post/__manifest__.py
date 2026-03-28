{
    'name': 'YouTube Video Auto Posting',
    'version': '1.0',
    'category': 'Marketing',
    'summary': 'Automate YouTube video uploads using a scheduler in Odoo',
    'description': """
        This module allows users to schedule and automate video uploads to YouTube using the YouTube Data API.
        Features:
        - Manage video uploads with metadata (title, description, tags, category, privacy).
        - Schedule uploads using Odoo's cron job.
        - Store videos as attachments and upload to YouTube automatically.
    """,
    'website':'https://devscodespace.com',
    'author': 'Ankit',
     'license': 'LGPL-3',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/youtube_cron.xml',
        'views/youtube_upload_views.xml',
        'views/youtube_settings_views.xml',
    ],
    'external_dependencies': {
        'python': ['google-api-python-client', 'google-auth-oauthlib', 'google-auth-httplib2'],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
}
