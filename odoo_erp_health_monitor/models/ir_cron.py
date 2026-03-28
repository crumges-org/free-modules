from odoo import models, fields
import time
import logging

_logger = logging.getLogger(__name__)


class IrCronInherit(models.Model):
    _inherit = 'ir.cron'

    def method_direct_trigger(self):
        """Override direct trigger to track execution"""
        start_time = time.time()
        error_msg = None
        status = 'success'
        
        try:
            # Call original method
            result = super(IrCronInherit, self).method_direct_trigger()
            return result
        except Exception as e:
            status = 'failed'
            error_msg = str(e)
            raise
        finally:
            duration = time.time() - start_time
            
            # Log execution
            try:
                self.env['erp.health.cron.log'].sudo().create({
                    'cron_id': self.id,
                    'cron_name': self.name,
                    'execution_date': fields.Datetime.now(),
                    'duration': duration,
                    'status': status,
                    'error_message': error_msg,
                })
                self.env.cr.commit()
                _logger.info(f"✅ Cron log saved: {self.name}")
            except Exception as log_error:
                _logger.error(f"Failed to log cron execution: {log_error}")
