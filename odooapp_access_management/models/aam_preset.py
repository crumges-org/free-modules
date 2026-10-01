"""The browsable half of the preset catalogue.

``PRESETS`` in :mod:`aam_preset_catalogue` is the source of truth; this model is
a searchable index of it, so the library can be a normal kanban with a search
view, category grouping and an "available here" filter instead of a radio list
that stops being usable somewhere around the tenth entry.

Records are synced from Python in :meth:`init`, which Odoo calls on install and
on every ``-u`` of the module. They deliberately carry no external id: they are
a projection of code, not data an administrator edits, and regenerating them
must never conflict with a hand-modified copy.
"""

from odoo import _, api, fields, models

from .aam_preset_catalogue import LINE_FIELDS, PRESET_CATEGORIES, PRESETS


class AamPreset(models.Model):
    _name = 'aam.preset'
    _description = 'Access Preset'
    _order = 'category, sequence, name'

    key = fields.Char(
        required=True, index=True, readonly=True,
        help="Identifier of the entry in the shipped catalogue.")
    name = fields.Char(required=True, readonly=True, translate=True)
    category = fields.Selection(PRESET_CATEGORIES, required=True, readonly=True)
    sequence = fields.Integer(default=10, readonly=True)
    description = fields.Text(readonly=True, translate=True)
    apps = fields.Char(
        'Requires', readonly=True,
        help="Which Odoo apps this preset is written for.")
    restriction_count = fields.Integer('Restrictions', readonly=True)
    restriction_label = fields.Char(compute='_compute_restriction_label')
    model_names = fields.Char(
        'Models', readonly=True,
        help="Technical models this preset touches. Searchable, so you can find "
             "a preset by the model you are trying to lock down.")

    is_available = fields.Boolean(
        'Available Here', compute='_compute_availability',
        search='_search_is_available',
        help="Every model and field this preset needs exists in this database.")
    availability_note = fields.Char(compute='_compute_availability')

    _sql_constraints = [
        ('key_uniq',
         'UNIQUE (key)',
         'Each catalogue entry may only appear once.'),
    ]

    # -- Catalogue sync -----------------------------------------------------

    def init(self):
        """Mirror the Python catalogue into the table on install and update.

        Deferred with ``pool.post_init`` rather than run inline. ``init_models``
        walks the registry doing ``_auto_init()`` then ``init()`` one model at a
        time, and ``models/__init__.py`` imports ``inherits`` last - so at this
        point ``res.users`` has not been given its access-management columns
        (e.g. ``aam_password_write_date``) yet. Creating a record here reaches
        ``ir.default._get_model_defaults``, whose ormcache key is
        ``self.env.company.id``; resolving that fetches ``res.users`` with every
        stored column and dies on the one that does not exist yet. ``post_init``
        runs the sync after every model's ``_auto_init`` has completed, which is
        what this needs and what core itself uses for cross-model init work
        (``base/models/ir_model.py:460``).
        """
        self.pool.post_init(self._sync_catalogue)

    @api.model
    def _catalogue(self):
        """``{key: spec}`` of every preset this database offers.

        The shipped catalogue. A module that adds presets extends the result -
        a method rather than the module-level dict, so an addition belongs to
        the databases where that module is installed.
        """
        return dict(PRESETS)

    @api.model
    def _sync_catalogue(self):
        """Create, update and prune catalogue records to match :meth:`_catalogue`.

        Pruning is safe: a profile created from a preset is an ordinary
        ``aam.profile`` with its own rules and holds no reference back here, so
        retiring an entry never disturbs a database already using it.
        """
        stale = {rec.key: rec for rec in self.sudo().search([])}
        for index, (key, spec) in enumerate(self._catalogue().items()):
            values = {
                'name': spec['name'],
                'category': spec.get('category', 'general'),
                'sequence': (index + 1) * 10,
                'description': spec.get('description', ''),
                'apps': spec.get('apps', ''),
                'restriction_count': self._count_restrictions(spec),
                'model_names': ', '.join(sorted(self._spec_models(spec))),
            }
            record = stale.pop(key, None)
            if record:
                record.sudo().write(values)
            else:
                self.sudo().create(dict(values, key=key))
        if stale:
            self.sudo().browse([rec.id for rec in stale.values()]).unlink()

    @staticmethod
    def _count_restrictions(spec):
        """How many switches this preset actually throws, for the card."""
        total = sum(1 for value in spec.get('rule', {}).values() if value)
        for key in LINE_FIELDS:
            total += len(spec.get(key, []))
        return total

    @staticmethod
    def _spec_models(spec):
        models_used = set()
        for key in ('model_lines', 'field_lines', 'search_lines', 'chatter_lines'):
            for line in spec.get(key, []):
                models_used.add(line['model'])
        return models_used

    @api.depends('restriction_count')
    def _compute_restriction_label(self):
        """Cards said "1 restrictions". Pluralise in Python, not in the arch:
        QWeb cannot pick a plural form and translators need both strings."""
        for preset in self:
            preset.restriction_label = (
                _("1 restriction") if preset.restriction_count == 1
                else _("%s restrictions", preset.restriction_count))

    # -- Availability -------------------------------------------------------

    @api.depends('key')
    def _compute_availability(self):
        for preset in self:
            missing = preset._missing_references()
            preset.is_available = not missing
            preset.availability_note = (
                _("Needs an app this database does not have: %s",
                  ', '.join(sorted(missing)))
                if missing else _("Applies fully to this database."))

    def _missing_references(self):
        """Every model, field or menu the preset names that is not here."""
        self.ensure_one()
        spec = self._catalogue().get(self.key)
        if spec is None:
            # The record outlived its catalogue entry - only reachable inside a
            # transaction that has not yet run the sync.
            return {self.key or ''}
        missing = set()
        for key in ('model_lines', 'search_lines', 'chatter_lines'):
            for line in spec.get(key, []):
                if line['model'] not in self.env:
                    missing.add(line['model'])
        installed = None
        for line in spec.get('field_lines', []):
            model = line['model']
            if line.get('requires'):
                # Optional line: only counts when the app that adds it is here.
                if installed is None:
                    installed = set(self.env['ir.module.module'].sudo().search(
                        [('state', '=', 'installed')]).mapped('name'))
                if line['requires'] not in installed:
                    continue
            if model not in self.env:
                missing.add(model)
            elif line['field'] not in self.env[model]._fields:
                missing.add('%s.%s' % (model, line['field']))
        for line in spec.get('menu_lines', []):
            if not self.env.ref(line['xmlid'], raise_if_not_found=False):
                missing.add(line['xmlid'])
        return missing

    def _search_is_available(self, operator, value):
        """Let the Preset Library filter on a computed, unstored flag."""
        if operator not in ('=', '!=') or not isinstance(value, bool):
            raise NotImplementedError(
                "is_available only supports = and != against a boolean.")
        available = self.search([]).filtered(lambda p: not p._missing_references())
        wanted = value if operator == '=' else not value
        return [('id', 'in' if wanted else 'not in', available.ids)]

    # -- Actions ------------------------------------------------------------

    def action_use(self):
        """Open the wizard with this preset - and any others selected - preloaded."""
        presets = self | self.browse(self.env.context.get('active_ids', []))
        return {
            'type': 'ir.actions.act_window',
            'name': _("Create Profiles from Presets"),
            'res_model': 'aam.preset.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': dict(self.env.context, default_preset_ids=presets.ids),
        }
