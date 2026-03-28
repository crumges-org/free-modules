{
    "name": "Git Source Manager",
    "version": "18.0.1.0.0",
    "category": "Technical",
    "summary": "Cross-platform Git repository management for Odoo with Windows & Linux support",
    "description": """
        Git Source Manager for Odoo 18
        ===============================
        
        Enterprise-grade Git repository management module for Odoo 18 that provides centralized 
        management of multiple Git repositories per entity, automated updates, and complete audit trails.
        
        Key Features:
        ------------
        - Multi-Repository Management: Manage unlimited Git repositories from GitHub, GitLab, 
          Bitbucket, or any Git server
        - Entity Linking: Link repositories to Odoo companies/entities with sequence ordering
        - Automated Updates: Schedule automatic repository updates via cron or trigger manually
        - Cross-Platform Support: Full Windows and Linux compatibility with automatic path normalization
        - Flexible Authentication: Support for public repos, HTTPS tokens, and SSH keys
        - Security: Role-based access control (Admin/User roles) with secure credential storage
        - Status Tracking: Real-time monitoring with status indicators (OK, Failed, Updating)
        - Update History: Complete audit trail with detailed logs and Git command output
        - Test Connectivity: Validate repository access before saving configurations
    """,
    "author": "Cyshield",
    "website": "https://www.cyshield.com",
    "license": "LGPL-3",
    "depends": ["base", "web", "mail", "mail_bot"],
    "images": [
        "static/description/icon.png",
        "static/description/cyshield.png",
        "static/description/RepositoryDetails.png",
        "static/description/RepositoryEntityLink.png",
        "static/description/RepositoryWorkspace.png",
    ],
    "data": [
        "security/git_manager_security.xml",
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "demo/git_source_repo_demo.xml",
        "views/git_source_repo_views.xml",
        "views/git_entity_link_views.xml",
        "views/git_workspace_views.xml",
        "views/git_update_log_views.xml",
        "views/git_manager_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "odoo_git_source_manager/static/src/js/git_update_widget.js",
            "odoo_git_source_manager/static/src/xml/git_update_widget.xml",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
}
