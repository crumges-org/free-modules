"""Data behind the Dashboard, Access Map and heatmap.

All of it is computed here rather than in the browser: the client would
otherwise need read access to ``ir.model.access``, ``res.groups`` and every
rule, which is precisely the data an access-management module should not hand
out casually. The OWL components receive numbers, not records.

Every entry point is ``@api.readonly`` so it can be served from a read replica,
and gated on the module's own groups.
"""

from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import AccessError
from .aam_group_compat import group_area, group_members, group_with_implied


#: Restriction families, in the order the heatmap shows them.
HEATMAP_COLUMNS = [
    ('read', 'Read'),
    ('write', 'Write'),
    ('create', 'Create'),
    ('unlink', 'Delete'),
    ('readonly', 'Read-only'),
    ('field_hide', 'Field Hide'),
    ('field_mask', 'Masked'),
    ('view_hide', 'View Hide'),
    ('duplicate', 'Duplicate'),
    ('archive', 'Archive'),
    ('import', 'Import'),
    ('export', 'Export'),
    ('print', 'Print'),
    ('button', 'Buttons'),
    ('search', 'Search'),
    ('chatter', 'Chatter'),
    ('domain', 'Records'),
]


class AamDashboard(models.AbstractModel):
    _name = 'aam.dashboard'
    _description = 'Access Management Dashboard Data'

    @api.model
    def _check_reader(self):
        if not self.env.user.has_group('odooapp_access_management.group_aam_user'):
            raise AccessError(_("You are not allowed to view access-management reporting."))

    # ------------------------------------------------------------------
    # Dashboard (features K1-K7)
    # ------------------------------------------------------------------

    @api.model
    @api.readonly
    def get_dashboard_data(self):
        self._check_reader()
        Rule = self.env['aam.rule'].sudo().with_context(active_test=False)
        rules = Rule.search([])
        now = fields.Datetime.now()
        soon = fields.Datetime.add(now, days=7)

        active = rules.filtered(lambda r: r.state == 'active')
        expired = rules.filtered(lambda r: r.state == 'expired')
        expiring = active.filtered(lambda r: r.date_to and now <= r.date_to <= soon)

        return {
            'tiles': self._tiles(rules, active, expired, expiring),
            'by_target': self._by_target(active),
            'by_family': self._by_family(active),
            'created_trend': self._created_trend(),
            'restricted_models': self._restricted_models(active),
            'insights': self._insights(rules, active),
            'recent_activity': self._recent_activity(),
            'top_users': self._top_users(active),
            'company': self.env.company.display_name,
            'updated': fields.Datetime.to_string(now),
        }

    def _tiles(self, rules, active, expired, expiring):
        total = len(rules) or 1
        def pct(n):
            return round(100.0 * n / total)
        return [
            {'key': 'total', 'label': _("Total Rules"), 'value': len(rules), 'pct': None},
            {'key': 'active', 'label': _("Active"), 'value': len(active),
             'pct': pct(len(active))},
            {'key': 'inactive', 'label': _("Inactive"), 'value': len(rules - active - expired),
             'pct': pct(len(rules - active - expired))},
            {'key': 'expiring', 'label': _("Expiring in 7 days"), 'value': len(expiring),
             'pct': pct(len(expiring))},
            {'key': 'expired', 'label': _("Expired"), 'value': len(expired),
             'pct': pct(len(expired))},
            {'key': 'user_rules', 'label': _("User Rules"),
             'value': len(active.filtered(lambda r: r.target_type == 'user')), 'pct': None},
            {'key': 'group_rules', 'label': _("Group Rules"),
             'value': len(active.filtered(lambda r: r.target_type == 'group')), 'pct': None},
            {'key': 'group_profile', 'label': _("Profile Rules"),
             'value': len(active.filtered(lambda r: r.target_type == 'profile')), 'pct': None},
            {'key': 'time_based', 'label': _("Time-Based"),
             'value': len(active.filtered(lambda r: r.time_window_ids)), 'pct': None},
            {'key': 'login_disabled', 'label': _("Login Disabled"),
             'value': len(active.filtered('disable_login')), 'pct': None},
        ]

    def _by_target(self, active):
        labels = dict(active._fields['target_type'].selection)
        counts = defaultdict(int)
        for rule in active:
            counts[rule.target_type] += 1
        return [{'label': labels.get(k, k), 'value': v} for k, v in sorted(counts.items())]

    def _by_family(self, active):
        families = [
            (_("Menus"), 'menu_line_ids'),
            (_("Models"), 'model_line_ids'),
            (_("Fields"), 'field_line_ids'),
            (_("Buttons"), 'button_line_ids'),
            (_("Search"), 'search_line_ids'),
            (_("Chatter"), 'chatter_line_ids'),
        ]
        return [
            {'label': label, 'value': sum(len(rule[fname]) for rule in active)}
            for label, fname in families
        ]

    def _created_trend(self):
        """Rules created per month over the last six months."""
        start = fields.Datetime.subtract(
            fields.Datetime.now().replace(day=1, hour=0, minute=0, second=0), days=155)
        groups = self.env['aam.rule'].sudo().with_context(active_test=False)._read_group(
            [('create_date', '>=', start)],
            groupby=['create_date:month'],
            aggregates=['__count'],
        )
        return [
            {'label': fields.Date.to_string(month)[:7], 'value': count}
            for month, count in groups
        ]

    def _restricted_models(self, active):
        """Rule-line count per model, most restricted first."""
        counts = defaultdict(int)
        for rule in active:
            for fname in ('model_line_ids', 'field_line_ids', 'button_line_ids',
                          'search_line_ids', 'chatter_line_ids'):
                for line in rule[fname]:
                    if line.model_name:
                        counts[line.model_name] += 1
        ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        return [{'model': m, 'value': v} for m, v in ordered]

    def _insights(self, rules, active):
        Policy = self.env['aam.policy']
        params = self.env['ir.config_parameter'].sudo()
        admin_protected = params.get_param('aam.allow_restrict_admin') not in (
            '1', 'True', 'true')
        enabled = params.get_param('aam.enabled', '1') in ('1', 'True', 'true')

        models_covered = {
            line.model_name
            for rule in active
            for fname in ('model_line_ids', 'field_line_ids', 'button_line_ids',
                          'search_line_ids', 'chatter_line_ids')
            for line in rule[fname]
            if line.model_name
        }
        users_affected = set()
        for rule in active:
            targeted = rule._targeted_user_ids()
            if targeted is None:
                users_affected.add('*')
            else:
                users_affected |= targeted

        companies = self.env['res.company'].sudo().search_count([])
        covered_companies = {c.id for rule in active for c in rule.company_ids} or None

        score, notes = self._config_score(rules, active, admin_protected, enabled)
        return {
            'score': score,
            'notes': notes,
            'enabled': enabled,
            'admin_protected': admin_protected,
            'models_covered': len(models_covered),
            'users_affected': '*' if '*' in users_affected else len(users_affected),
            'companies_total': companies,
            'companies_covered': companies if covered_companies is None
                                 else len(covered_companies),
            'ui_only_rules': len(active.filtered(lambda r: r.enforcement == 'ui_only')),
        }

    def _config_score(self, rules, active, admin_protected, enabled):
        """A blunt health score, with the reasons spelled out.

        A number on its own is not actionable, so every deduction comes with the
        note that explains it.
        """
        score = 100
        notes = []
        if not enabled:
            score -= 50
            notes.append({'level': 'danger', 'text': _(
                "Access Management is switched off - no rule is doing anything.")})
        if not admin_protected:
            score -= 20
            notes.append({'level': 'warning', 'text': _(
                "Administrator protection is off. A bad rule could lock you out.")})
        ui_only = active.filtered(lambda r: r.enforcement == 'ui_only')
        if ui_only:
            score -= min(15, 3 * len(ui_only))
            notes.append({'level': 'warning', 'text': _(
                "%s rule(s) only hide things in the UI and can be bypassed over the API.",
                len(ui_only))})
        stale = rules.filtered(lambda r: r.state == 'expired')
        if stale:
            score -= min(10, 2 * len(stale))
            notes.append({'level': 'info', 'text': _(
                "%s expired rule(s) are still lying around. Clean them up.", len(stale))})
        if not active:
            notes.append({'level': 'info', 'text': _(
                "No active rules yet. Load a preset to get started.")})
        if not notes:
            notes.append({'level': 'success', 'text': _("No configuration problems found.")})
        return max(score, 0), notes

    def _recent_activity(self, limit=8):
        logs = self.env['aam.audit.log'].sudo().search([], limit=limit)
        return [{
            'id': log.id,
            # Both spellings on purpose: `event` is the translated label the
            # dashboard prints, `event_type` the raw selection key the client
            # maps to an icon. Keying the icon off the label would silently
            # fall back to the default in every language but English.
            'event_type': log.event_type,
            'event': dict(log._fields['event_type'].selection).get(log.event_type),
            'user': log.user_id.display_name,
            'model': log.model_name or '',
            'when': fields.Datetime.to_string(log.create_date),
        } for log in logs]

    def _top_users(self, active, limit=8):
        counts = defaultdict(int)
        for rule in active:
            targeted = rule._targeted_user_ids()
            if targeted is None:
                continue
            for uid in targeted:
                counts[uid] += 1
        top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
        users = self.env['res.users'].sudo().browse([uid for uid, _c in top])
        by_id = {u.id: u.display_name for u in users}
        return [{'id': uid, 'name': by_id.get(uid, str(uid)), 'value': count}
                for uid, count in top if uid in by_id]

    # ------------------------------------------------------------------
    # Heatmap (feature K3)
    # ------------------------------------------------------------------

    @api.model
    @api.readonly
    def get_heatmap_data(self):
        self._check_reader()
        active = self.env['aam.rule'].sudo().search([])
        grid = defaultdict(lambda: defaultdict(int))

        for rule in active:
            for line in rule.model_line_ids:
                model = line.model_name
                if not model:
                    continue
                for mode in line._blocked_modes():
                    grid[model][mode] += 1
                if line.readonly_model:
                    grid[model]['readonly'] += 1
                for flag, column in (('hide_duplicate', 'duplicate'),
                                     ('hide_archive', 'archive'),
                                     ('hide_import', 'import'),
                                     ('hide_export', 'export'),
                                     ('hide_print', 'print')):
                    if getattr(line, flag):
                        grid[model][column] += 1
                if line.hide_view_ids or line.hide_view_modes:
                    grid[model]['view_hide'] += 1
                if line._domain_modes():
                    grid[model]['domain'] += 1
            for line in rule.field_line_ids:
                if not line.model_name:
                    continue
                if line.invisible:
                    grid[line.model_name]['field_hide'] += 1
                if line.mask_type and line.mask_type != 'none':
                    grid[line.model_name]['field_mask'] += 1
            for fname, column in (('button_line_ids', 'button'),
                                  ('search_line_ids', 'search'),
                                  ('chatter_line_ids', 'chatter')):
                for line in rule[fname]:
                    if line.model_name:
                        grid[line.model_name][column] += 1

        rows = []
        for model, columns in grid.items():
            total = sum(columns.values())
            rows.append({
                'model': model,
                'total': total,
                'cells': {key: columns.get(key, 0) for key, _label in HEATMAP_COLUMNS},
            })
        rows.sort(key=lambda r: (-r['total'], r['model']))
        return {
            'columns': [{'key': k, 'label': label} for k, label in HEATMAP_COLUMNS],
            'rows': rows,
        }

    # ------------------------------------------------------------------
    # Access Map (features K8-K13)
    # ------------------------------------------------------------------

    @api.model
    @api.readonly
    def get_access_map_groups(self):
        """Groups with their privilege area and member count."""
        self._check_reader()
        groups = self.env['res.groups'].sudo().search([])
        xmlids = groups.get_external_id()
        return [{
            'id': group.id,
            'name': group.name,
            'area': group_area(group).name or _("Uncategorised"),
            'xmlid': xmlids.get(group.id, ''),
            'members': len(group_members(group)),
            'implied': group.implied_ids.mapped('name'),
        } for group in groups]

    @api.model
    @api.readonly
    def get_access_map_detail(self, group_id, scope='relevant'):
        """Users and the model/CRUD matrix for one group.

        ``scope='relevant'`` shows only models this group has an explicit ACL
        row for - which is what an auditor means by "what can this role do".
        ``scope='all'`` adds models reachable through implied groups.
        """
        self._check_reader()
        group = self.env['res.groups'].sudo().browse(group_id).exists()
        if not group:
            return {}

        groups = group if scope == 'relevant' else group_with_implied(group)
        accesses = self.env['ir.model.access'].sudo().search(
            [('group_id', 'in', groups.ids)])

        by_model = {}
        for access in accesses:
            model = access.model_id.model
            entry = by_model.setdefault(model, {
                'model': model,
                'name': access.model_id.name,
                'create': False, 'read': False, 'write': False, 'unlink': False,
            })
            for perm, key in (('perm_create', 'create'), ('perm_read', 'read'),
                              ('perm_write', 'write'), ('perm_unlink', 'unlink')):
                entry[key] = entry[key] or bool(access[perm])

        rows = []
        for entry in by_model.values():
            granted = sum(1 for k in ('create', 'read', 'write', 'unlink') if entry[k])
            entry['status'] = ('full' if granted == 4
                               else 'readonly' if entry['read'] and granted == 1
                               else 'partial' if granted else 'none')
            rows.append(entry)
        rows.sort(key=lambda r: r['name'] or r['model'])

        return {
            'group': {'id': group.id, 'name': group.name,
                      'area': group_area(group).name or _("Uncategorised")},
            'users': [{'id': u.id, 'name': u.name, 'login': u.login}
                      for u in group_members(group)[:200]],
            'user_count': len(group_members(group)),
            'models': rows,
            'cannot': self._group_cannot(rows),
        }

    def _group_cannot(self, rows):
        """Derived from live rights, never hand-written.

        A "what this role cannot do" panel that someone typed by hand goes stale
        the first time an ACL changes, and a stale security summary is worse
        than none.
        """
        out = []
        no_delete = [r['model'] for r in rows if r['read'] and not r['unlink']]
        no_write = [r['model'] for r in rows if r['read'] and not r['write']]
        no_create = [r['model'] for r in rows if r['read'] and not r['create']]
        if no_delete:
            out.append({'text': _("Cannot delete"), 'models': sorted(no_delete)[:12],
                        'count': len(no_delete)})
        if no_write:
            out.append({'text': _("Cannot edit"), 'models': sorted(no_write)[:12],
                        'count': len(no_write)})
        if no_create:
            out.append({'text': _("Cannot create"), 'models': sorted(no_create)[:12],
                        'count': len(no_create)})
        return out
