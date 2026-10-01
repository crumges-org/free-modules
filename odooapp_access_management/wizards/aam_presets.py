"""Turn one or more catalogue presets into real profiles and rules.

The catalogue itself lives in :mod:`..models.aam_preset_catalogue`; the
browsable index of it in :mod:`..models.aam_preset`. This wizard is only the
apply step: pick presets, optionally say who they are for, and get one profile
per preset with its rule already written.

Nothing here assumes the database has any particular app. Every model, field and
menu is resolved against the live registry and quietly dropped if it is missing,
and the wizard says up front what it will have to skip.
"""

from odoo import _, api, fields, models


class AamPresetWizard(models.TransientModel):
    _name = 'aam.preset.wizard'
    _description = 'Load Preset Profiles'

    preset_ids = fields.Many2many(
        'aam.preset', string='Presets', required=True,
        help="Each preset becomes its own profile, so you can assign them "
             "separately afterwards.")
    coverage = fields.Html(compute='_compute_coverage')
    profile_prefix = fields.Char(
        'Name Prefix',
        help="Optional. Prefixed to every profile created, which helps when you "
             "load the same preset for two departments.")
    group_ids = fields.Many2many(
        'res.groups', string='Assign to Groups',
        help="Optional. You can also assign the profile later.")
    user_ids = fields.Many2many('res.users', string='Assign to Users')

    @api.depends('preset_ids')
    def _compute_coverage(self):
        for wizard in self:
            wizard.coverage = wizard._coverage_html()

    def _coverage_html(self):
        """Say up front which parts of the selection this database can use."""
        if not self.preset_ids:
            return _("<p class='text-muted'>Pick one or more presets to see what "
                     "they will do here.</p>")
        wanted, missing = set(), set()
        catalogue = self.env['aam.preset']._catalogue()
        for preset in self.preset_ids:
            spec = catalogue.get(preset.key) or {}
            wanted |= {
                model for model in self.env['aam.preset']._spec_models(spec)
                if model in self.env
            }
            missing |= preset._missing_references()
        parts = []
        if wanted:
            parts.append(_("<p><b>Will be applied to:</b> %s</p>",
                           ', '.join(sorted(wanted))))
        if missing:
            parts.append(_(
                "<div class='alert alert-warning mb-0'><b>Skipped - not installed:</b> "
                "%s</div>", ', '.join(sorted(missing))))
        if not parts:
            parts.append(_("<p>These presets apply database-wide and need no "
                           "extra apps.</p>"))
        return ''.join(parts)

    # -- Apply --------------------------------------------------------------

    def action_apply(self):
        self.ensure_one()
        profiles = self.env['aam.profile']
        catalogue = self.env['aam.preset']._catalogue()
        for preset in self.preset_ids:
            profiles |= self._apply_one(catalogue[preset.key])

        if len(profiles) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'aam.profile',
                'res_id': profiles.id,
                'view_mode': 'form',
                'name': _("Preset applied"),
            }
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'aam.profile',
            'view_mode': 'list,form',
            'domain': [('id', 'in', profiles.ids)],
            'name': _("%s profiles created", len(profiles)),
        }

    def _apply_one(self, spec):
        name = spec['name']
        if self.profile_prefix:
            name = '%s %s' % (self.profile_prefix.strip(), name)

        profile = self.env['aam.profile'].create({
            'name': name,
            'description': spec['description'],
            'group_ids': [(6, 0, self.group_ids.ids)],
            'user_ids': [(6, 0, self.user_ids.ids)],
        })

        values = dict(spec.get('rule', {}))
        values.update({
            'name': _("%s rules", name),
            'target_type': 'profile',
            'profile_id': profile.id,
            'model_line_ids': [(0, 0, line) for line in self._model_lines(spec, 'model_lines')],
            'search_line_ids': [(0, 0, line) for line in self._model_lines(spec, 'search_lines')],
            'chatter_line_ids': [(0, 0, line) for line in self._model_lines(spec, 'chatter_lines')],
            'field_line_ids': [(0, 0, line) for line in self._field_lines(spec)],
            'menu_line_ids': [(0, 0, line) for line in self._menu_lines(spec)],
        })
        self.env['aam.rule'].create(values)
        return profile

    def _model_lines(self, spec, key):
        """Resolve any model-scoped line list, dropping models this DB lacks."""
        Model = self.env['ir.model'].sudo()
        out = []
        for line in spec.get(key, []):
            model_name = line['model']
            if model_name not in self.env:
                continue
            record = Model.search([('model', '=', model_name)], limit=1)
            if not record:
                continue
            values = {k: v for k, v in line.items() if k != 'model'}
            values['model_id'] = record.id
            out.append(values)
        return out

    def _field_lines(self, spec):
        Model = self.env['ir.model'].sudo()
        Field = self.env['ir.model.fields'].sudo()
        out = []
        for line in spec.get('field_lines', []):
            model_name, field_name = line['model'], line['field']
            if model_name not in self.env or field_name not in self.env[model_name]._fields:
                continue
            record = Model.search([('model', '=', model_name)], limit=1)
            field = Field.search(
                [('model', '=', model_name), ('name', '=', field_name)], limit=1)
            if not record or not field:
                continue
            values = {k: v for k, v in line.items() if k not in ('model', 'field', 'requires')}
            values.update({'model_id': record.id, 'field_id': field.id})
            out.append(values)
        return out

    def _menu_lines(self, spec):
        out = []
        for line in spec.get('menu_lines', []):
            menu = self.env.ref(line['xmlid'], raise_if_not_found=False)
            if not menu:
                continue
            values = {k: v for k, v in line.items() if k != 'xmlid'}
            values['menu_id'] = menu.id
            out.append(values)
        return out
