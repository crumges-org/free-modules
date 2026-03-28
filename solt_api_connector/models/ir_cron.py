from odoo import fields, models


class IrCron(models.Model):
    _inherit = 'ir.cron'

    server_action_to_import_id = fields.Many2one('ir.actions.server', string='Server action for import', readonly=True, )
    server_action_to_export_id = fields.Many2one('ir.actions.server', string='Server action for export', help="Server action used to run the initial export", )

    def method_direct_trigger(self):
        """Override to preserve server_action_id on manual trigger."""
        server_action_id = self.env.context.get('server_action_id', False)
        if server_action_id:
            self.write({'server_action_to_import_id': server_action_id})
        server_action_export_id = self.env.context.get('server_action_export_id', False)
        if server_action_export_id:
            self.write({'server_action_to_export_id': server_action_export_id})
        return super().method_direct_trigger()
