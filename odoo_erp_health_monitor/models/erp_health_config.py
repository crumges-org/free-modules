from odoo import models, fields, api
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class ErpHealthConfig(models.Model):
    _name = 'erp.health.config'
    _description = 'ERP Health Monitor Configuration'
    _rec_name = 'id'

    # Data Retention Settings
    system_logs_retention = fields.Selection([
        ('7', 'Last 7 Days'),
        ('15', 'Last 15 Days'),
        ('30', 'Last Month'),
        ('90', 'Last 3 Months'),
        ('all', 'All Time'),
    ], string='System Logs Retention', default='30', required=True)
    
    slow_queries_retention = fields.Selection([
        ('7', 'Last 7 Days'),
        ('15', 'Last 15 Days'),
        ('30', 'Last Month'),
        ('90', 'Last 3 Months'),
        ('all', 'All Time'),
    ], string='Slow Queries Retention', default='30', required=True)
    
    server_metrics_retention = fields.Selection([
        ('7', 'Last 7 Days'),
        ('15', 'Last 15 Days'),
        ('30', 'Last Month'),
        ('90', 'Last 3 Months'),
        ('all', 'All Time'),
    ], string='Server Metrics Retention', default='30', required=True)
    
    database_locks_retention = fields.Selection([
        ('7', 'Last 7 Days'),
        ('15', 'Last 15 Days'),
        ('30', 'Last Month'),
        ('90', 'Last 3 Months'),
        ('all', 'All Time'),
    ], string='Database Locks Retention', default='15', required=True)
    
    cron_logs_retention = fields.Selection([
        ('7', 'Last 7 Days'),
        ('15', 'Last 15 Days'),
        ('30', 'Last Month'),
        ('90', 'Last 3 Months'),
        ('all', 'All Time'),
    ], string='Cron Logs Retention', default='30', required=True)
    
    # Auto cleanup settings
    auto_cleanup = fields.Boolean(string='Enable Auto Cleanup', default=True,
                                  help='Automatically clean old records based on retention settings')
    
    last_cleanup = fields.Datetime(string='Last Cleanup', readonly=True)

    @api.model
    def default_get(self, fields_list):
        """Override to ensure only one config exists"""
        res = super().default_get(fields_list)
        # Check if config already exists
        existing = self.search([], limit=1)
        if existing:
            # Return existing config's default values
            return existing.read(fields_list)[0] if existing else res
        return res

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to ensure singleton pattern"""
        # Check if a config already exists
        existing = self.search([], limit=1)
        if existing:
            return existing
        return super().create(vals_list)

    @api.model
    def get_config(self):
        """Get or create singleton config record"""
        config = self.search([], limit=1)
        if not config:
            config = self.create({})
        return config

    def _get_cutoff_date(self, retention_value):
        """Calculate cutoff date based on retention setting"""
        if retention_value == 'all':
            return None
        
        days = int(retention_value)
        return datetime.now() - timedelta(days=days)

    @api.model
    def cleanup_old_data(self):
        """Clean up old data based on retention settings"""
        config = self.get_config()
        
        if not config.auto_cleanup:
            _logger.info("Auto cleanup is disabled")
            return
        
        # System Logs cleanup
        cutoff = config._get_cutoff_date(config.system_logs_retention)
        if cutoff:
            old_logs = self.env['erp.health.odoo.log'].search([
                ('timestamp', '<', cutoff)
            ])
            count = len(old_logs)
            old_logs.unlink()
            _logger.info(f"Deleted {count} old system logs")
        
        # Slow Queries cleanup
        cutoff = config._get_cutoff_date(config.slow_queries_retention)
        if cutoff:
            old_queries = self.env['erp.health.slow.query'].search([
                ('detected_at', '<', cutoff)
            ])
            count = len(old_queries)
            old_queries.unlink()
            _logger.info(f"Deleted {count} old slow queries")
        
        # Server Metrics cleanup
        cutoff = config._get_cutoff_date(config.server_metrics_retention)
        if cutoff:
            old_metrics = self.env['erp.health.server.metrics'].search([
                ('timestamp', '<', cutoff)
            ])
            count = len(old_metrics)
            old_metrics.unlink()
            _logger.info(f"Deleted {count} old server metrics")
        
        # Database Locks cleanup
        cutoff = config._get_cutoff_date(config.database_locks_retention)
        if cutoff:
            old_locks = self.env['erp.health.database.lock'].search([
                ('detected_at', '<', cutoff)
            ])
            count = len(old_locks)
            old_locks.unlink()
            _logger.info(f"Deleted {count} old database locks")
        
        # Cron Logs cleanup
        cutoff = config._get_cutoff_date(config.cron_logs_retention)
        if cutoff:
            old_crons = self.env['erp.health.cron.log'].search([
                ('execution_date', '<', cutoff)
            ])
            count = len(old_crons)
            old_crons.unlink()
            _logger.info(f"Deleted {count} old cron logs")
        
        # Update last cleanup time
        config.write({'last_cleanup': fields.Datetime.now()})
        
        _logger.info("Data cleanup completed successfully")
        
        return True

    def action_cleanup_now(self):
        """Manual cleanup trigger"""
        try:
            self.cleanup_old_data()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': 'Old data cleaned up successfully based on retention settings',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error(f"Error during cleanup: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': f'Cleanup failed: {str(e)}',
                    'type': 'danger',
                    'sticky': True,
                }
            }