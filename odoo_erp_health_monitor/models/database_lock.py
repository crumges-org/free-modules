from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ErpHealthDatabaseLock(models.Model):
    _name = 'erp.health.database.lock'
    _description = 'Database Lock Monitor'
    _order = 'detected_at desc'

    detected_at = fields.Datetime(string='Detected At', readonly=True, default=fields.Datetime.now)
    pid = fields.Integer(string='Process ID', readonly=True)
    lock_type = fields.Char(string='Lock Type', readonly=True)
    relation = fields.Char(string='Table/Relation', readonly=True)
    mode = fields.Char(string='Lock Mode', readonly=True)
    query = fields.Text(string='Query', readonly=True)
    wait_time = fields.Float(string='Wait Time (seconds)', readonly=True)

    @api.model
    def refresh_locks(self):
        """Detect current database locks"""
        query = """
            SELECT 
                l.pid,
                l.locktype,
                l.relation::regclass::text as relation,
                l.mode,
                a.query,
                EXTRACT(EPOCH FROM (now() - a.query_start)) as wait_time
            FROM pg_locks l
            LEFT JOIN pg_stat_activity a ON l.pid = a.pid
            WHERE NOT l.granted
              AND a.query IS NOT NULL
            ORDER BY wait_time DESC
            LIMIT 50
        """

        try:
            self.env.cr.execute(query)
            results = self.env.cr.dictfetchall()

            # Clear old records
            old_records = self.search([], order='id desc', offset=500)
            if old_records:
                old_records.unlink()

            # Store new locks
            for row in results:
                self.create({
                    'pid': row['pid'],
                    'lock_type': row['locktype'],
                    'relation': row['relation'] or 'N/A',
                    'mode': row['mode'],
                    'query': row['query'][:5000] if row['query'] else '',
                    'wait_time': row['wait_time'] or 0,
                })

            _logger.info(f"Detected {len(results)} database locks")
            return True

        except Exception as e:
            _logger.error(f"Error detecting locks: {e}")
            return False