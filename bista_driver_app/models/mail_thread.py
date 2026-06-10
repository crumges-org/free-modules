from odoo import fields, models, api,_


class MailThread(models.AbstractModel):

    _inherit = 'mail.thread'


    def _message_compute_author(self, author_id=None, email_from=None, raise_on_email=True):
        """T2577: bypass email check for driver user type"""
        # if self.env.user and self.env.user.standard_template_integration_user_type == 'driver_user':
        if self.env.user and self.env.user.has_group('bista_driver_app.group_shipment_driver_user_access') and not self.env.user.has_group('bista_driver_app.group_shipment_dispatcher_access'):
            raise_on_email = False
        return super(MailThread, self)._message_compute_author(author_id=author_id, email_from=email_from, raise_on_email=raise_on_email)
