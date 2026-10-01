"""Version-portable export and import of access rules.

The problem this solves
-----------------------
The market leader's own listing tells customers to *uninstall the module before
upgrading the database*, and warns that re-imported rules may silently fail to
map. That is the loudest complaint in this category, and it comes from storing
rules by database id: ids do not survive a migration, so an export from 17.0
lands in 18.0 pointing at whatever happens to occupy those rows.

So we serialise by **external ID and technical name** - ``sale.order``,
``partner_id``, ``base.group_user`` - never by id. Those are stable across
databases and across versions.

Some references still will not resolve: a model that was renamed, a field that
was dropped, a group from an app the target database does not have. Silently
skipping those is how you end up with a half-applied security policy and no
idea which half. So import runs a **dry run first** and reports every reference
that will not resolve, before anything is written.
"""

import base64
import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError

#: Marks a reference that had no external id and falls back to matching by
#: name. Colon-terminated so it can never be mistaken for a dotted xmlid.
NAME_PREFIX = 'name:'

#: Fields present on every line but never worth exporting.
_SKIP = {
    'id', 'create_uid', 'create_date', 'write_uid', 'write_date',
    'rule_id', 'display_name', '__last_update',
}

#: One entry per restriction family: the o2m on aam.rule, its comodel, and the
#: reference fields that must be exported symbolically rather than as ids.
LINE_SPECS = {
    'menu_line_ids': {
        'comodel': 'aam.rule.menu',
        'refs': {'menu_id': ('ir.ui.menu', 'xmlid')},
    },
    'model_line_ids': {
        'comodel': 'aam.rule.model',
        'refs': {
            'model_id': ('ir.model', 'model'),
            'related_field_id': ('ir.model.fields', 'field'),
            'hierarchy_field_id': ('ir.model.fields', 'field'),
            'hide_view_ids': ('ir.ui.view', 'xmlid'),
            'hide_report_ids': ('ir.actions.report', 'xmlid'),
            'hide_action_ids': ('ir.actions.act_window', 'xmlid'),
            'hide_server_action_ids': ('ir.actions.server', 'xmlid'),
        },
    },
    'field_line_ids': {
        'comodel': 'aam.rule.field',
        'refs': {'model_id': ('ir.model', 'model'), 'field_id': ('ir.model.fields', 'field')},
    },
    'button_line_ids': {
        'comodel': 'aam.rule.button',
        'refs': {'model_id': ('ir.model', 'model')},
    },
    'search_line_ids': {
        'comodel': 'aam.rule.search',
        'refs': {'model_id': ('ir.model', 'model')},
    },
    'chatter_line_ids': {
        'comodel': 'aam.rule.chatter',
        'refs': {'model_id': ('ir.model', 'model')},
    },
}

#: Reference fields on aam.rule itself.
RULE_REFS = {
    'user_ids': ('res.users', 'login'),
    'group_ids': ('res.groups', 'xmlid'),
    'company_ids': ('res.company', 'name'),
}


class AamRulesIoMixin(models.AbstractModel):
    """Shared symbolic-reference resolution for both directions."""

    _name = 'aam.rules.io.mixin'
    _description = 'Access Rules Import/Export Helpers'

    # -- serialising -------------------------------------------------------

    @api.model
    def _rule_refs(self):
        """Reference fields on ``aam.rule`` carried in the file: ``{field: (comodel, kind)}``.

        A module that adds such a field to the rule extends the result.
        """
        return dict(RULE_REFS)

    @api.model
    def _ref_out(self, record, kind):
        """Turn one record into a portable string, or None if it cannot be."""
        if not record:
            return None
        if kind == 'xmlid':
            xmlid = record.get_external_id().get(record.id)
            if xmlid:
                return xmlid
            # Records created through the interface - the "Warehouse Crew" group
            # a customer made themselves - have no external id. Dropping them
            # would silently strip a rule's target, which is the exact failure
            # this format exists to avoid, so fall back to matching by name and
            # mark it so the reader can tell the two apart.
            return '%s%s' % (NAME_PREFIX, record.display_name)
        if kind == 'model':
            return record.model
        if kind == 'field':
            return '%s.%s' % (record.model, record.name)
        if kind == 'login':
            return record.login
        return record.display_name

    @api.model
    def _scalars_of(self, comodel, refs):
        """Exportable scalar field names of a line model."""
        Model = self.env[comodel]
        return [
            name for name, field in Model._fields.items()
            if name not in _SKIP
            and name not in refs
            and field.store
            and not field.related
            and field.type in ('boolean', 'char', 'text', 'integer', 'float', 'selection')
        ]

    # -- resolving ---------------------------------------------------------

    @api.model
    def _ref_in(self, value, comodel, kind, problems, context_label):
        """Resolve a portable string back to an id, recording failures."""
        if not value:
            return False
        Model = self.env[comodel].sudo()
        record = None
        if kind == 'xmlid':
            if value.startswith(NAME_PREFIX):
                record = Model.search(
                    [('name', '=', value[len(NAME_PREFIX):])], limit=1)
            else:
                record = self.env.ref(value, raise_if_not_found=False)
        elif kind == 'model':
            record = Model.search([('model', '=', value)], limit=1)
        elif kind == 'field':
            model_name, _sep, field_name = value.rpartition('.')
            record = Model.search(
                [('model', '=', model_name), ('name', '=', field_name)], limit=1)
        elif kind == 'login':
            record = Model.search([('login', '=', value)], limit=1)
        else:
            record = Model.search([('name', '=', value)], limit=1)

        if not record:
            problems.append({
                'reference': value,
                'target_model': comodel,
                'context': context_label,
            })
            return False
        return record.id


class AamRulesExport(models.TransientModel):
    _name = 'aam.rules.export'
    _inherit = ['aam.rules.io.mixin']
    _description = 'Export Access Rules'

    rule_ids = fields.Many2many('aam.rule', string='Rules',
                                help="Leave empty to export every rule.")
    profile_ids = fields.Many2many('aam.profile', string='Profiles',
                                   help="Leave empty to export every profile.")
    include_inactive = fields.Boolean('Include Archived', default=False)

    data = fields.Binary('File', readonly=True, attachment=False)
    filename = fields.Char(readonly=True)

    def action_export(self):
        self.ensure_one()
        payload = self._build_payload()
        raw = json.dumps(payload, indent=2, sort_keys=True, default=str).encode()
        self.write({
            'data': base64.b64encode(raw),
            'filename': 'access_rules_%s.json' % fields.Date.today().isoformat(),
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'aam.rules.export',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _build_payload(self):
        self.ensure_one()
        domain = [] if self.include_inactive else [('active', '=', True)]
        rules = self.rule_ids or self.env['aam.rule'].search(
            domain + ([] if self.include_inactive else []))
        profiles = self.profile_ids or self.env['aam.profile'].search(domain)
        if self.include_inactive:
            rules = rules.with_context(active_test=False)
            profiles = profiles.with_context(active_test=False)

        return {
            'format_version': 1,
            'module_version': self.env['ir.module.module'].sudo().search(
                [('name', '=', 'odooapp_access_management')], limit=1).installed_version or '',
            'odoo_series': '18.0',
            'exported_on': fields.Datetime.now().isoformat(),
            'source_database': self.env.cr.dbname,
            'profiles': [self._dump_profile(p) for p in profiles],
            'rules': [self._dump_rule(r) for r in rules],
        }

    def _dump_profile(self, profile):
        return {
            'name': profile.name,
            'active': profile.active,
            'sequence': profile.sequence,
            'description': profile.description or '',
            'date_start': profile.date_start and profile.date_start.isoformat() or None,
            'date_end': profile.date_end and profile.date_end.isoformat() or None,
            'users': [u.login for u in profile.user_ids],
            'groups': [x for x in (self._ref_out(g, 'xmlid') for g in profile.group_ids) if x],
            'companies': [c.name for c in profile.company_ids],
        }

    def _dump_rule(self, rule):
        refs = self._rule_refs()
        data = {
            name: rule[name]
            for name in self._scalars_of('aam.rule', set(refs) | {'profile_id'})
        }
        data['profile'] = rule.profile_id.name or None
        for fname, (comodel, kind) in refs.items():
            data[fname] = [
                x for x in (self._ref_out(rec, kind) for rec in rule[fname]) if x
            ]
        data['date_from'] = rule.date_from and rule.date_from.isoformat() or None
        data['date_to'] = rule.date_to and rule.date_to.isoformat() or None
        data['time_windows'] = [
            {'day_of_week': w.day_of_week, 'hour_from': w.hour_from,
             'hour_to': w.hour_to, 'tz': w.tz or None}
            for w in rule.time_window_ids
        ]
        for o2m, spec in LINE_SPECS.items():
            data[o2m] = [self._dump_line(line, spec) for line in rule[o2m]]
        return data

    def _dump_line(self, line, spec):
        refs = spec['refs']
        out = {name: line[name] for name in self._scalars_of(spec['comodel'], set(refs))}
        for fname, (comodel, kind) in refs.items():
            value = line[fname]
            if line._fields[fname].type == 'many2many':
                out[fname] = [x for x in (self._ref_out(r, kind) for r in value) if x]
            else:
                out[fname] = self._ref_out(value, kind)
        return out


class AamRulesImport(models.TransientModel):
    _name = 'aam.rules.import'
    _inherit = ['aam.rules.io.mixin']
    _description = 'Import Access Rules'

    data = fields.Binary('JSON File', required=True)
    filename = fields.Char()
    mode = fields.Selection(
        [('dry_run', 'Dry run - report only'), ('apply', 'Import')],
        default='dry_run', required=True,
        help="A dry run resolves every reference and reports what is missing, "
             "without writing anything.")
    on_conflict = fields.Selection(
        [('skip', 'Keep the existing rule'), ('replace', 'Replace it')],
        default='skip', required=True, string='If a rule already exists')

    state = fields.Selection(
        [('draft', 'Draft'), ('done', 'Done')], default='draft')
    report = fields.Html(readonly=True)
    problem_count = fields.Integer(readonly=True)
    imported_count = fields.Integer(readonly=True)

    def action_run(self):
        self.ensure_one()
        try:
            payload = json.loads(base64.b64decode(self.data).decode())
        except Exception as exc:
            raise UserError(_("That file is not valid JSON: %s", exc)) from exc

        if not isinstance(payload, dict) or 'rules' not in payload:
            raise UserError(_(
                "That does not look like an access-rules export - no 'rules' key found."))

        problems = []
        prepared = [self._prepare_rule(r, problems) for r in payload.get('rules', [])]
        profiles = [self._prepare_profile(p, problems) for p in payload.get('profiles', [])]

        imported = 0
        if self.mode == 'apply':
            imported = self._apply(profiles, prepared)

        self.write({
            'state': 'done',
            'problem_count': len(problems),
            'imported_count': imported,
            'report': self._render_report(payload, problems, prepared, imported),
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'aam.rules.import',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    # -- preparation -------------------------------------------------------

    def _prepare_profile(self, data, problems):
        label = _("profile '%s'", data.get('name', '?'))
        return {
            'name': data.get('name'),
            'active': data.get('active', True),
            'sequence': data.get('sequence', 10),
            'description': data.get('description') or False,
            'date_start': data.get('date_start') or False,
            'date_end': data.get('date_end') or False,
            'user_ids': [(6, 0, self._resolve_many(
                data.get('users'), 'res.users', 'login', problems, label))],
            'group_ids': [(6, 0, self._resolve_many(
                data.get('groups'), 'res.groups', 'xmlid', problems, label))],
            'company_ids': [(6, 0, self._resolve_many(
                data.get('companies'), 'res.company', 'name', problems, label))],
        }

    def _resolve_many(self, values, comodel, kind, problems, label):
        ids = []
        for value in values or []:
            resolved = self._ref_in(value, comodel, kind, problems, label)
            if resolved:
                ids.append(resolved)
        return ids

    def _prepare_rule(self, data, problems):
        label = _("rule '%s'", data.get('name', '?'))
        refs = self._rule_refs()
        values = {
            name: data[name]
            for name in self._scalars_of('aam.rule', set(refs) | {'profile_id'})
            if name in data
        }
        values['date_from'] = data.get('date_from') or False
        values['date_to'] = data.get('date_to') or False

        for fname, (comodel, kind) in refs.items():
            values[fname] = [(6, 0, self._resolve_many(
                data.get(fname), comodel, kind, problems, label))]

        values['time_window_ids'] = [
            (0, 0, {k: w.get(k) for k in ('day_of_week', 'hour_from', 'hour_to', 'tz')})
            for w in data.get('time_windows') or []
        ]

        for o2m, spec in LINE_SPECS.items():
            commands = []
            for raw in data.get(o2m) or []:
                line = self._prepare_line(raw, spec, problems, label)
                if line is not None:
                    commands.append((0, 0, line))
            values[o2m] = commands

        return {'profile': data.get('profile'), 'values': values,
                'name': data.get('name', '?')}

    def _prepare_line(self, raw, spec, problems, label):
        refs = spec['refs']
        line = {name: raw[name] for name in self._scalars_of(spec['comodel'], set(refs))
                if name in raw}
        Model = self.env[spec['comodel']]
        for fname, (comodel, kind) in refs.items():
            value = raw.get(fname)
            if Model._fields[fname].type == 'many2many':
                line[fname] = [(6, 0, self._resolve_many(
                    value, comodel, kind, problems, label))]
            else:
                resolved = self._ref_in(value, comodel, kind, problems, label)
                if not resolved and Model._fields[fname].required:
                    # The line cannot exist without it, so drop the line rather
                    # than write a broken one. It is already in the report.
                    return None
                line[fname] = resolved
        return line

    # -- applying ----------------------------------------------------------

    def _apply(self, profiles, prepared):
        Profile = self.env['aam.profile']
        Rule = self.env['aam.rule']

        by_name = {}
        for values in profiles:
            if not values.get('name'):
                continue
            existing = Profile.with_context(active_test=False).search(
                [('name', '=', values['name'])], limit=1)
            if existing:
                if self.on_conflict == 'replace':
                    existing.write(values)
                by_name[values['name']] = existing
            else:
                by_name[values['name']] = Profile.create(values)

        count = 0
        for item in prepared:
            values = dict(item['values'])
            profile_name = item['profile']
            if profile_name:
                profile = by_name.get(profile_name) or Profile.with_context(
                    active_test=False).search([('name', '=', profile_name)], limit=1)
                values['profile_id'] = profile.id if profile else False

            existing = Rule.with_context(active_test=False).search(
                [('name', '=', item['name'])], limit=1)
            if existing:
                if self.on_conflict == 'skip':
                    continue
                existing.unlink()
            Rule.create(values)
            count += 1
        return count

    # -- report ------------------------------------------------------------

    def _render_report(self, payload, problems, prepared, imported):
        rows = []
        for problem in problems:
            rows.append(
                '<tr><td><code>%s</code></td><td>%s</td><td>%s</td></tr>' % (
                    problem['reference'], problem['target_model'], problem['context']))

        head = _(
            "<p>File from <b>%(db)s</b>, exported %(when)s (Odoo %(series)s).<br/>"
            "%(rules)s rule(s) and %(profiles)s profile(s) in the file.</p>",
            db=payload.get('source_database', '?'),
            when=payload.get('exported_on', '?'),
            series=payload.get('odoo_series', '?'),
            rules=len(prepared), profiles=len(payload.get('profiles', [])))

        if self.mode == 'apply':
            head += _("<p><b>%s rule(s) imported.</b></p>", imported)
        else:
            head += _("<p><i>Dry run - nothing was written.</i></p>")

        if not rows:
            return head + _(
                "<div class='alert alert-success'>Every reference resolved. "
                "This file will import cleanly.</div>")

        return head + _(
            "<div class='alert alert-warning'><b>%(n)s reference(s) could not be "
            "resolved</b> and will be skipped. This usually means the target "
            "database is missing an app, or a field was renamed between versions."
            "</div><table class='table table-sm'><thead><tr><th>Reference</th>"
            "<th>Expected</th><th>Used by</th></tr></thead><tbody>%(rows)s"
            "</tbody></table>", n=len(problems), rows=''.join(rows))
