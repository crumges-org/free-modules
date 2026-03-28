from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ErpHealthServerMetrics(models.Model):
    _name = 'erp.health.server.metrics'
    _description = 'Server Health Metrics'
    _order = 'timestamp desc'

    timestamp = fields.Datetime(string='Timestamp', readonly=True, default=fields.Datetime.now)
    cpu_percent = fields.Float(string='CPU Usage (%)', readonly=True)
    ram_percent = fields.Float(string='RAM Usage (%)', readonly=True)
    ram_used_gb = fields.Float(string='RAM Used (GB)', readonly=True)
    ram_total_gb = fields.Float(string='RAM Total (GB)', readonly=True)
    disk_percent = fields.Float(string='Disk Usage (%)', readonly=True)
    disk_used_gb = fields.Float(string='Disk Used (GB)', readonly=True)
    disk_total_gb = fields.Float(string='Disk Total (GB)', readonly=True)
    load_average_1m = fields.Float(string='Load Avg (1m)', readonly=True)
    load_average_5m = fields.Float(string='Load Avg (5m)', readonly=True)
    load_average_15m = fields.Float(string='Load Avg (15m)', readonly=True)
    hour = fields.Integer(compute='_compute_hour', store=True)

    @api.depends('timestamp')
    def _compute_hour(self):
        for rec in self:
            if rec.timestamp:
                rec.hour = rec.timestamp.hour

    @api.model
    def collect_metrics(self):
        """Collect server metrics using psutil - Windows compatible"""
        try:
            import psutil
            
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)

            # RAM
            ram = psutil.virtual_memory()
            ram_percent = ram.percent
            ram_used_gb = ram.used / (1024 ** 3)
            ram_total_gb = ram.total / (1024 ** 3)

            # Disk (Windows compatible - use C: drive)
            try:
                disk = psutil.disk_usage('C:\\')
            except Exception as disk_error:
                _logger.warning(f"Could not get C:\\ disk usage: {disk_error}, trying /")
                try:
                    disk = psutil.disk_usage('/')
                except Exception as disk_error2:
                    _logger.error(f"Could not get disk usage: {disk_error2}")
                    disk = None
            
            if disk:
                disk_percent = disk.percent
                disk_used_gb = disk.used / (1024 ** 3)
                disk_total_gb = disk.total / (1024 ** 3)
            else:
                disk_percent = 0.0
                disk_used_gb = 0.0
                disk_total_gb = 0.0

            # Load average - Skip on Windows (causes the error)
            # Windows doesn't support getloadavg properly
            load_1m = load_5m = load_15m = 0.0
            
            # Try to get load average, but don't fail if it doesn't work
            try:
                load_avg = psutil.getloadavg()
                load_1m, load_5m, load_15m = load_avg
            except (AttributeError, OSError, RuntimeError) as e:
                # Expected on Windows - Performance counters issue
                _logger.debug(f"Load average not available (Windows): {e}")
                pass

            # Store metrics
            record = self.create({
                'cpu_percent': cpu_percent,
                'ram_percent': ram_percent,
                'ram_used_gb': ram_used_gb,
                'ram_total_gb': ram_total_gb,
                'disk_percent': disk_percent,
                'disk_used_gb': disk_used_gb,
                'disk_total_gb': disk_total_gb,
                'load_average_1m': load_1m,
                'load_average_5m': load_5m,
                'load_average_15m': load_15m,
            })

            _logger.info(f"✅ Server metrics collected successfully: CPU={cpu_percent}%, RAM={ram_percent}%, Disk={disk_percent}%")

            # Keep only last 1000 records
            old_records = self.search([], order='id desc', offset=1000)
            if old_records:
                old_records.unlink()
                
            return record

        except ImportError as e:
            _logger.error(f"psutil not installed: {e}")
            _logger.error("Install with: pip install psutil")
            return False
        except Exception as e:
            _logger.error(f"Error collecting server metrics: {e}")
            import traceback
            _logger.error(traceback.format_exc())
            return False