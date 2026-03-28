import os
from odoo import models, fields, api
from datetime import datetime


class ErpHealthOdooLog(models.Model):
    _name = 'erp.health.odoo.log'
    _description = 'Odoo Server Logs'
    _order = 'timestamp desc'

    timestamp = fields.Datetime(string='Timestamp', readonly=True)
    level = fields.Selection([
        ('DEBUG', 'Debug'),
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('CRITICAL', 'Critical'),
    ], string='Level', readonly=True)
    logger = fields.Char(string='Logger', readonly=True)
    message = fields.Text(string='Message', readonly=True)

    @api.model
    def refresh_logs(self, lines=500):
        """Read last N lines from Odoo log file"""
        try:
            # Find Odoo log file
            log_file = self._get_log_file_path()
            
            if not log_file or not os.path.exists(log_file):
                _logger.warning(f"Log file not found: {log_file}")
                return False

            # Read last N lines
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
                last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

            # Clear old logs
            self.search([]).unlink()

            # Parse and store logs
            for line in last_lines:
                log_data = self._parse_log_line(line)
                if log_data:
                    self.create(log_data)

            return True

        except Exception as e:
            _logger.error(f"Error reading logs: {e}")
            return False

    def _get_log_file_path(self):
        """Get Odoo log file path"""
        import odoo
        # Common log file locations
        possible_paths = [
            odoo.tools.config.get('logfile'),
            '/var/log/odoo/odoo.log',
            '/var/log/odoo/odoo-server.log',
            'C:\\Program Files\\Odoo 18.0.20241126\\server\\odoo.log',
        ]
        
        for path in possible_paths:
            if path and os.path.exists(path):
                return path
        
        return None

    def _parse_log_line(self, line):
        """Parse Odoo log line format"""
        try:
            # Odoo log format: 2026-01-18 21:05:42,573 8816 INFO production odoo.addons...
            parts = line.split(' ', 6)
            if len(parts) < 6:
                return None

            date_str = f"{parts[0]} {parts[1].split(',')[0]}"
            timestamp = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            level = parts[3]
            logger = parts[5] if len(parts) > 5 else 'odoo'
            message = parts[6] if len(parts) > 6 else line

            return {
                'timestamp': timestamp,
                'level': level if level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] else 'INFO',
                'logger': logger.strip(),
                'message': message.strip(),
            }
        except Exception:
            return None