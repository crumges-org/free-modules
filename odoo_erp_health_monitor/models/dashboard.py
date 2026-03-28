from odoo import models, fields, api
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class ErpHealthDashboard(models.Model):
    _name = 'erp.health.dashboard'
    _description = 'ERP Health Dashboard Controller'
    _rec_name = 'id'

    # Display fields for dashboard stats
    cpu_percent = fields.Float(string='CPU Usage %', compute='_compute_dashboard_stats')
    ram_percent = fields.Float(string='RAM Usage %', compute='_compute_dashboard_stats')
    disk_percent = fields.Float(string='Disk Usage %', compute='_compute_dashboard_stats')
    
    total_crons = fields.Integer(string='Total Cron Jobs', compute='_compute_dashboard_stats')
    failed_crons = fields.Integer(string='Failed Crons', compute='_compute_dashboard_stats')
    slow_crons = fields.Integer(string='Slow Crons', compute='_compute_dashboard_stats')
    
    total_queries = fields.Integer(string='Total Slow Queries', compute='_compute_dashboard_stats')
    queries_today = fields.Integer(string='Queries Today', compute='_compute_dashboard_stats')
    
    total_locks = fields.Integer(string='Database Locks', compute='_compute_dashboard_stats')
    error_logs = fields.Integer(string='Error Logs', compute='_compute_dashboard_stats')
    
    last_update = fields.Datetime(string='Last Update', compute='_compute_dashboard_stats')
    
    # Health status indicators
    cpu_status = fields.Selection([
        ('good', 'Good'),
        ('warning', 'Warning'),
        ('critical', 'Critical')
    ], string='CPU Status', compute='_compute_health_status')
    
    ram_status = fields.Selection([
        ('good', 'Good'),
        ('warning', 'Warning'),
        ('critical', 'Critical')
    ], string='RAM Status', compute='_compute_health_status')
    
    disk_status = fields.Selection([
        ('good', 'Good'),
        ('warning', 'Warning'),
        ('critical', 'Critical')
    ], string='Disk Status', compute='_compute_health_status')

    @api.model
    def default_get(self, fields_list):
        """Override to ensure only one dashboard exists"""
        res = super().default_get(fields_list)
        # Check if dashboard already exists
        existing = self.search([], limit=1)
        if existing:
            # Return existing dashboard's default values
            return existing.read(fields_list)[0] if existing else res
        return res

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to ensure singleton pattern"""
        # Check if a dashboard already exists
        existing = self.search([], limit=1)
        if existing:
            return existing
        return super().create(vals_list)

    @api.depends_context('uid')
    def _compute_dashboard_stats(self):
        """Compute all dashboard statistics"""
        for record in self:
            today_start = datetime.combine(fields.Date.today(), datetime.min.time())
            
            # Server Metrics Stats
            latest_metric = self.env['erp.health.server.metrics'].search([], order='id desc', limit=1)
            record.cpu_percent = latest_metric.cpu_percent if latest_metric else 0
            record.ram_percent = latest_metric.ram_percent if latest_metric else 0
            record.disk_percent = latest_metric.disk_percent if latest_metric else 0
            record.last_update = latest_metric.timestamp if latest_metric else False
            
            # Cron Stats
            record.total_crons = self.env['erp.health.cron.log'].search_count([])
            record.failed_crons = self.env['erp.health.cron.log'].search_count([
                ('status', '=', 'failed'),
                ('execution_date', '>=', today_start)
            ])
            record.slow_crons = self.env['erp.health.cron.log'].search_count([
                ('is_slow', '=', True),
                ('execution_date', '>=', today_start)
            ])
            
            # Slow Query Stats
            record.total_queries = self.env['erp.health.slow.query'].search_count([])
            record.queries_today = self.env['erp.health.slow.query'].search_count([
                ('detected_at', '>=', today_start)
            ])
            
            # Database Locks
            record.total_locks = self.env['erp.health.database.lock'].search_count([
                ('detected_at', '>=', today_start)
            ])
            
            # Error Logs
            record.error_logs = self.env['erp.health.odoo.log'].search_count([
                ('level', 'in', ['ERROR', 'CRITICAL']),
                ('timestamp', '>=', today_start)
            ])

    @api.depends('cpu_percent', 'ram_percent', 'disk_percent')
    def _compute_health_status(self):
        """Compute health status based on usage percentages"""
        for record in self:
            # CPU Status
            if record.cpu_percent < 60:
                record.cpu_status = 'good'
            elif record.cpu_percent < 80:
                record.cpu_status = 'warning'
            else:
                record.cpu_status = 'critical'
            
            # RAM Status
            if record.ram_percent < 70:
                record.ram_status = 'good'
            elif record.ram_percent < 85:
                record.ram_status = 'warning'
            else:
                record.ram_status = 'critical'
            
            # Disk Status
            if record.disk_percent < 75:
                record.disk_status = 'good'
            elif record.disk_percent < 90:
                record.disk_status = 'warning'
            else:
                record.disk_status = 'critical'

    # Action buttons
    def action_collect_metrics(self):
        """Manually trigger server metrics collection"""
        try:
            self.env['erp.health.server.metrics'].collect_metrics()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': 'Server metrics collected successfully. Refreshing...',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error(f"Error collecting metrics: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': f'Failed to collect metrics: {str(e)}',
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def action_refresh_slow_queries(self):
        """Manually trigger slow query detection"""
        try:
            self.env['erp.health.slow.query'].refresh_slow_queries()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': 'Slow queries refreshed successfully',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error(f"Error refreshing queries: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': f'Failed to refresh queries: {str(e)}',
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def action_refresh_locks(self):
        """Manually trigger database lock detection"""
        try:
            self.env['erp.health.database.lock'].refresh_locks()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': 'Database locks refreshed successfully',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error(f"Error refreshing locks: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': f'Failed to refresh locks: {str(e)}',
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def action_refresh_logs(self):
        """Manually trigger log refresh"""
        try:
            self.env['erp.health.odoo.log'].refresh_logs()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': 'Odoo logs refreshed successfully',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error(f"Error refreshing logs: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': f'Failed to refresh logs: {str(e)}',
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def action_view_slow_queries(self):
        """Open slow queries view"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Slow Queries',
            'res_model': 'erp.health.slow.query',
            'view_mode': 'list,form',
            'context': {'search_default_today': 1},
            'target': 'current',
        }

    def action_view_cron_logs(self):
        """Open cron logs view"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cron Logs',
            'res_model': 'erp.health.cron.log',
            'view_mode': 'list,form',
            'context': {'search_default_today': 1},
            'target': 'current',
        }

    def action_view_server_metrics(self):
        """Open server metrics view"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Server Metrics',
            'res_model': 'erp.health.server.metrics',
            'view_mode': 'list,graph,form',
            'target': 'current',
        }

    def action_view_database_locks(self):
        """Open database locks view"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Database Locks',
            'res_model': 'erp.health.database.lock',
            'view_mode': 'list,form',
            'target': 'current',
        }

    def action_view_odoo_logs(self):
        """Open Odoo logs view"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Odoo Logs',
            'res_model': 'erp.health.odoo.log',
            'view_mode': 'list,form',
            'context': {'search_default_errors': 1},
            'target': 'current',
        }