from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ErpHealthSlowQuery(models.Model):
    _name = 'erp.health.slow.query'
    _description = 'Slow SQL Query Monitor'
    _order = 'duration desc, id desc'

    query_text = fields.Text(string='Query', readonly=True)
    duration = fields.Float(string='Duration (seconds)', readonly=True)
    database_user = fields.Char(string='Database User', readonly=True)
    query_state = fields.Char(string='State', readonly=True)
    detected_at = fields.Datetime(string='Detected At', readonly=True, default=fields.Datetime.now)
    pid = fields.Integer(string='Process ID', readonly=True)

    @api.model
    def refresh_slow_queries(self):
        """Fetch slow queries from PostgreSQL and store them"""
        threshold = self.env['ir.config_parameter'].sudo().get_param(
            'odoo_erp_health_monitor.slow_query_threshold', '2.0'
        )
        threshold = float(threshold)

        query = """
            SELECT 
                pid,
                usename as db_user,
                state,
                query,
                EXTRACT(EPOCH FROM (now() - query_start)) as duration
            FROM pg_stat_activity
            WHERE state = 'active'
              AND query NOT LIKE '%%pg_stat_activity%%'
              AND EXTRACT(EPOCH FROM (now() - query_start)) > %s
            ORDER BY duration DESC
            LIMIT 50
        """

        try:
            self.env.cr.execute(query, (threshold,))
            results = self.env.cr.dictfetchall()

            # Clear old records (keep last 1000)
            old_records = self.search([], order='id desc', offset=1000)
            if old_records:
                old_records.unlink()

            # Insert new slow queries
            for row in results:
                self.create({
                    'pid': row['pid'],
                    'database_user': row['db_user'],
                    'query_state': row['state'],
                    'query_text': row['query'][:5000],  # Trim to 5000 chars
                    'duration': row['duration'],
                })

            _logger.info(f"Detected {len(results)} slow queries (threshold: {threshold}s)")

        except Exception as e:
            _logger.error(f"Error fetching slow queries: {e}")