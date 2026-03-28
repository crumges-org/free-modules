from odoo import fields, models
from odoo.addons.generic_mixin import post_create, post_write


class CrmLead(models.Model):
    _name = 'crm.lead'
    _inherit = ['crm.lead', 'generic.mixin.track.changes']

    kw_stage_history_ids = fields.One2many(
        comodel_name='kw.crm.stage.history',
        inverse_name='lead_id',
        string='Stage Change History',
    )

    @post_create()
    def _post_create_stage_history(self, changes):
        self._kw_create_stage_history(
            stage_from_id=False,
            stage_to_id=self.stage_id.id,
        )

    @post_write('stage_id')
    def _post_write_stage_history(self, changes):
        stage_change = changes.get('stage_id')
        if stage_change:
            self._kw_close_stage_history()
            self._kw_create_stage_history(
                stage_from_id=stage_change.old_val.id,
                stage_to_id=stage_change.new_val.id,
            )

    def _kw_create_stage_history(self, stage_from_id, stage_to_id):
        self.env['kw.crm.stage.history'].create({
            'lead_id': self.id,
            'stage_from_id': stage_from_id,
            'stage_to_id': stage_to_id,
            'date_in': fields.Datetime.now(),
            'date_in_by_id': self.env.uid,
        })

    def _kw_close_stage_history(self):
        last = self.env['kw.crm.stage.history'].search([
            ('lead_id', '=', self.id),
            ('date_out', '=', False),
        ], limit=1, order='date_in desc')
        if last:
            last.write({
                'date_out': fields.Datetime.now(),
                'date_out_by_id': self.env.uid,
            })
