# Part of Axoline Layout Editor. See LICENSE file for full copyright and licensing details.

import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

#: Store URL of the PRO add-on (see axoline_layout_editor_pro).
AXOLINE_PRO_STORE_URL = 'https://apps.odoo.com/apps/modules/18.0/axoline_layout_editor_pro'


class AxolineLayoutTemplate(models.Model):
    _name = 'axoline.layout.template'
    _description = 'Axoline Layout Template'
    _order = 'sequence, name'

    name = fields.Char(string='Name', required=True, translate=True)
    description = fields.Text(string='Description', translate=True)
    layout_json = fields.Text(
        string='Layout (JSON)',
        required=True,
        default='{"version":1,"blocks":[]}',
    )
    thumbnail = fields.Image(string='Thumbnail', max_width=400, max_height=300)
    is_system = fields.Boolean(string='System Template', default=False)
    category = fields.Selection(
        [
            ('classic', 'Classic'),
            ('modern', 'Modern'),
            ('compact', 'Compact'),
            ('custom', 'Custom'),
        ],
        string='Category',
        default='custom',
        required=True,
    )
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    axoline_is_locked = fields.Boolean(
        string='PRO Required',
        compute='_compute_axoline_is_locked',
        help='Technical flag: this system template is only available with the '
             'Axoline Layout Editor PRO add-on.',
    )

    @api.depends('is_system')
    def _compute_axoline_is_locked(self):
        is_pro = self.env['ir.actions.report']._axoline_is_pro()
        classic = self.env.ref(
            'axoline_layout_editor.template_classic', raise_if_not_found=False,
        )
        classic_id = classic.id if classic else False
        for rec in self:
            rec.axoline_is_locked = bool(
                not is_pro and rec.is_system and rec.id != classic_id
            )

    def action_axoline_open_pro_store(self):
        """Open the PRO add-on page on the Odoo App Store in a new tab."""
        return {
            'type': 'ir.actions.act_url',
            'url': AXOLINE_PRO_STORE_URL,
            'target': 'new',
        }

    @api.constrains('layout_json')
    def _check_layout_json(self):
        for rec in self:
            if not (rec.layout_json or '').strip():
                continue
            try:
                json.loads(rec.layout_json)
            except json.JSONDecodeError as e:
                raise ValidationError(_('Layout (JSON) is invalid: %s') % e) from e

    def action_open_visual_editor(self):
        """Open the OWL visual editor for this template."""
        self.ensure_one()
        if self.is_system:
            raise UserError(_('System templates cannot be edited in the editor.'))
        return {
            'type': 'ir.actions.client',
            'tag': 'axoline_layout_editor',
            'name': _('Template: %s') % self.name,
            'params': {
                'template_id': self.id,
            },
        }

    def write(self, vals):
        # Allow the module loader to (re)write system templates on
        # install/upgrade (install_mode); only block interactive edits.
        if not self.env.context.get('install_mode'):
            for rec in self:
                if rec.is_system:
                    raise UserError(_('System templates cannot be modified.'))
        return super().write(vals)

    def unlink(self):
        if not self.env.context.get('install_mode'):
            for rec in self:
                if rec.is_system:
                    raise UserError(_('System templates cannot be deleted.'))
        return super().unlink()
