from . import models

def post_init_hook(env):
    """Post-install hook to initialize the connector system"""
    # Start the background job scheduler
    try:
        scheduler = env['connector.job.scheduler'].search([('active', '=', True)], limit=1)
        if scheduler:
            scheduler.start_scheduler()
    except Exception:
        # Log error but don't fail installation
        pass

def uninstall_hook(env):
    """Uninstall hook to clean up the connector system"""
    # Stop any running schedulers
    try:
        schedulers = env['connector.job.scheduler'].search([('active', '=', True)])
        for scheduler in schedulers:
            scheduler.write({'active': False})
    except Exception:
        # Log error but don't fail uninstallation
        pass 