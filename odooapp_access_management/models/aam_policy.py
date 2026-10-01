"""Compiles every rule that applies to a user into one cached dict.

Why this exists
---------------
The obvious implementation of an access-management module is to search
``aam.rule`` inside each enforcement hook. That is also why these modules have a
reputation for making databases slow: ``fields_get``, ``get_view`` and
``ir.model.access.check`` run constantly, and a rule search inside each of them
multiplies across every request.

Instead we compile once per ``(uid, company, lang, debug)`` and cache the result
in the registry, so every hook downstream is a plain dict lookup. The cache is
dropped whenever any ``aam.*`` record changes.

Time-based rules would poison that cache, so compilation is split in two:

* the **static tier** - rules with no time window - is cached, and carries the
  next date boundary at which it stops being true;
* the **dynamic overlay** - rules with time windows - is recompiled per call
  from a cached, small list of rule ids.

The cached policy is **frozen** (frozensets and tuples). Enforcement hooks only
read it, and freezing means a hook that tries to mutate fails loudly here rather
than silently corrupting every other user's policy through the shared cache.

Merge semantics
---------------
**Deny wins.** Booleans OR together, hidden-id sets union, and domains AND
together. ``priority`` only breaks ties between restrictions of the same kind;
it can never turn a denial into a permission. This is deliberate: an
access-management module that lets one rule silently re-grant what another took
away is impossible to reason about, and none of the comparable modules document
what they do here at all.
"""

import hashlib
import json

from odoo import SUPERUSER_ID, api, fields, models, tools
from odoo.tools.safe_eval import safe_eval

from .aam_constants import (
    GLOBAL_FLAGS,
    PARAM_ALLOW_RESTRICT_ADMIN,
    PARAM_ENABLED,
    PROTECTED_UIDS,
    RAW_VALUES,
)

#: Set-valued keys, by the section that owns them. Used by the freeze/thaw and
#: JSON helpers so the three stay in step.
_SET_KEYS = {
    'root': ('menus', 'reports', 'actions', 'views'),
    'model': ('blocked', 'hidden_view_modes'),
    'search': ('filters', 'groupbys'),
}


def _empty_policy():
    """A policy that restricts nothing. Every section is always present."""
    return {
        'globals': {flag: False for flag in GLOBAL_FLAGS},
        'menus': set(),
        'models': {},
        'fields': {},
        'buttons': {},
        'search': {},
        'chatter': {},
        'reports': set(),
        'actions': set(),
        'views': set(),
    }


def _empty_model_entry():
    return {
        'blocked': set(),
        'hide_archive': False,
        'hide_duplicate': False,
        'hide_export': False,
        'hide_import': False,
        'hide_spreadsheet': False,
        'hide_print': False,
        'hide_action_button': False,
        'hide_edit_button': False,
        'hidden_view_modes': set(),
        'domains': {},
    }


def _empty_field_entry():
    return {
        'invisible': False,
        'readonly': False,
        'required': False,
        'no_open': False,
        'no_create': False,
        'no_quick_create': False,
        'no_create_edit': False,
        'no_export': False,
        'conditions': [],
        'domains': [],
        'mask': None,
        'enforced': False,
        # View types this field is hidden in from a scoped line. Arch-only:
        # never read by `_aam_field_is_hidden`, so the field still exists.
        'view_invisible': set(),
    }


def _empty_search_entry():
    return {
        'filters': set(),
        'groupbys': set(),
        'hide_all_filters': False,
        'hide_all_groupby': False,
        'hide_custom_filter': False,
        'hide_custom_groupby': False,
        'hide_delete_filter': False,
        'hide_favourite': False,
        'hide_search_panel': False,
    }


def _freeze(policy):
    """Make a compiled policy immutable before it enters the registry cache."""
    frozen = dict(policy)
    frozen['globals'] = dict(policy['globals'])
    for key in _SET_KEYS['root']:
        frozen[key] = frozenset(policy[key])

    frozen['models'] = {}
    for model, entry in policy['models'].items():
        new = dict(entry)
        for key in _SET_KEYS['model']:
            new[key] = frozenset(entry[key])
        new['domains'] = {mode: tuple(clauses) for mode, clauses in entry['domains'].items()}
        frozen['models'][model] = new

    frozen['fields'] = {
        model: {
            fname: {**fentry,
                    'conditions': tuple(fentry['conditions']),
                    'domains': tuple(fentry['domains']),
                    'view_invisible': frozenset(fentry['view_invisible'])}
            for fname, fentry in fields_.items()
        }
        for model, fields_ in policy['fields'].items()
    }
    frozen['buttons'] = {model: tuple(items) for model, items in policy['buttons'].items()}

    frozen['search'] = {}
    for model, entry in policy['search'].items():
        new = dict(entry)
        for key in _SET_KEYS['search']:
            new[key] = frozenset(entry[key])
        frozen['search'][model] = new

    frozen['chatter'] = {model: dict(entry) for model, entry in policy['chatter'].items()}
    return frozen


def _thaw(frozen):
    """Rebuild a mutable policy from a frozen one, for the dynamic overlay.

    Cheaper and far more predictable than ``copy.deepcopy`` on a structure that
    mixes frozensets, tuples and dicts.
    """
    policy = _empty_policy()
    policy['globals'] = dict(frozen['globals'])
    for key in _SET_KEYS['root']:
        policy[key] = set(frozen[key])

    for model, entry in frozen['models'].items():
        new = dict(entry)
        for key in _SET_KEYS['model']:
            new[key] = set(entry[key])
        new['domains'] = {mode: list(clauses) for mode, clauses in entry['domains'].items()}
        policy['models'][model] = new

    policy['fields'] = {
        model: {
            fname: {**fentry,
                    'conditions': list(fentry['conditions']),
                    'domains': list(fentry['domains']),
                    'view_invisible': set(fentry['view_invisible'])}
            for fname, fentry in fields_.items()
        }
        for model, fields_ in frozen['fields'].items()
    }
    policy['buttons'] = {model: list(items) for model, items in frozen['buttons'].items()}

    for model, entry in frozen['search'].items():
        new = dict(entry)
        for key in _SET_KEYS['search']:
            new[key] = set(entry[key])
        policy['search'][model] = new

    policy['chatter'] = {model: dict(entry) for model, entry in frozen['chatter'].items()}
    return policy


def _to_json(policy):
    """Deep-convert a policy to something ``json.dumps`` accepts.

    Sets become sorted lists so the blob is byte-stable between calls; an
    unstable blob would defeat HTTP caching and make the client re-render for
    no reason.
    """
    out = {
        'globals': dict(policy['globals']),
        'models': {},
        'fields': {},
        'buttons': {model: list(items) for model, items in policy['buttons'].items()},
        'search': {},
        'chatter': {model: dict(entry) for model, entry in policy['chatter'].items()},
    }
    for key in _SET_KEYS['root']:
        out[key] = sorted(policy[key])

    for model, entry in policy['models'].items():
        new = dict(entry)
        for key in _SET_KEYS['model']:
            new[key] = sorted(entry[key])
        new['domains'] = {mode: list(clauses) for mode, clauses in entry['domains'].items()}
        out['models'][model] = new

    out['fields'] = {
        model: {
            fname: {**fentry,
                    'conditions': list(fentry['conditions']),
                    'domains': list(fentry['domains']),
                    'view_invisible': sorted(fentry['view_invisible'])}
            for fname, fentry in fields_.items()
        }
        for model, fields_ in policy['fields'].items()
    }

    for model, entry in policy['search'].items():
        new = dict(entry)
        for key in _SET_KEYS['search']:
            new[key] = sorted(entry[key])
        out['search'][model] = new
    return out


class AamPolicy(models.AbstractModel):
    _name = 'aam.policy'
    _description = 'Compiled Access Policy'

    # ------------------------------------------------------------------
    # Entry points
    # ------------------------------------------------------------------

    @api.model
    @api.private
    def get_policy(self):
        """Effective policy for the current user. Read-only - do not mutate.

        The common path returns the frozen, cached object directly, so this is
        cheap enough to call from inside enforcement hooks.
        """
        static, active = self._policy_parts()
        return self._compose_policy(static, active)

    @api.model
    def _compose_policy(self, static, active):
        """``static`` with the active time-windowed rules folded in."""
        if not active:
            return static
        policy = _thaw(static)
        # Compiled raw, for the same reason as in `_static_policy`.
        self.with_context(aam_raw_values=RAW_VALUES)._merge_rules(policy, active)
        return _freeze(policy)

    @api.model
    @api.private
    def _access_fingerprint(self):
        """What, beyond the user, record and model access depend on right now.

        Added to the cache keys of ``ir.rule._compute_domain`` and
        ``ir.model.access._get_allowed_models``. Both are ormcached until a rule
        changes, so without this a time-windowed restriction stayed however it
        was when first cached: a window that opened later never applied, and one
        that closed kept applying.

        The static tier needs nothing here - its cache is cleared whenever a
        rule changes - so this is only the time-windowed rules active at this
        moment: empty for almost every user, and a short tuple of ids for the
        rest. Shares ``_policy_parts`` with ``get_policy`` so the two can never
        disagree about whether a user is restricted at all.
        """
        _static, active = self._policy_parts()
        return tuple(active.ids)

    @api.model
    def _policy_parts(self):
        """``(frozen static policy, active time-windowed rules)`` for this user."""
        if self.env.su:
            return _freeze(_empty_policy()), self.env['aam.rule'].sudo()
        return self._policy_parts_for_uid()

    @api.model
    def _policy_parts_for_uid(self):
        """The same for ``env.uid``, whether or not this env is ``sudo()``.

        ``get_policy`` stands down under ``sudo()``. A module that redacts
        values serialised under ``sudo()`` for the current user asks here:
        ``sudo()`` keeps the uid, so the answer is still about the right
        person. Resolved in place rather than through ``sudo(False)``: a sudo
        flow may run in a company the user does not belong to, where a non-sudo
        env raises on ``env.company``.
        """
        env = self.env
        no_rules = env['aam.rule'].sudo()
        if env.uid == SUPERUSER_ID or not env.uid:
            # The superuser, or no resolvable user (a degenerate environment, or
            # a request that has not authenticated yet). Restricting nothing is
            # the only safe answer: we have nobody to compile a policy for, and
            # guessing would either leak or lock out.
            return _freeze(_empty_policy()), no_rules

        # This runs for every field of every record a user reads, so after the
        # first call it has to be a single cache lookup. The kill switch and the
        # administrator rail are decided inside `_static_policy`, behind the
        # cache - reading them here made every list page ~4x slower for every
        # user, including those no rule applies to.
        debug = bool(env.context.get('aam_debug'))
        company_id = env.company.id
        lang = env.lang or 'en_US'
        static, valid_until, dynamic_ids = self._static_policy(
            env.uid, company_id, lang, debug)

        if valid_until and fields.Datetime.now() >= valid_until:
            # A date boundary passed since we cached. Drop and recompute rather
            # than serving a policy we already know is stale.
            env.registry.clear_cache()
            static, valid_until, dynamic_ids = self._static_policy(
                env.uid, company_id, lang, debug)

        if not dynamic_ids:
            return static, no_rules
        # Read raw for the same reason as in `_static_policy`.
        return static, self.with_context(aam_raw_values=RAW_VALUES)._active_dynamic_rules(dynamic_ids)

    @api.model
    @api.readonly
    def get_client_policy(self):
        """JSON-safe slice of the policy, for the web client at boot.

        ``version`` fingerprints the payload. The web client keeps view archs in
        a *persistent* IndexedDB cache that Odoo only invalidates when
        ``ir.ui.view`` or ``ir.filters`` is written, so assigning a profile -
        which writes neither - left the browser rendering the arch it had cached
        from before the restriction: fields this module had already stripped
        server-side were still on screen after a reload. The client compares
        this fingerprint with the one it last saw and drops the cache when it
        moves. Without it the server is right and the browser is stale, which is
        the worst possible split.
        """
        policy = _to_json(self.get_policy())
        blob = json.dumps(policy, sort_keys=True, default=str)
        policy['version'] = hashlib.sha256(blob.encode()).hexdigest()[:16]
        return policy

    @api.model
    def _is_protected(self, user):
        """True when this user must never be restricted (safety rail)."""
        if len(user) != 1:
            return True
        params = self.env['ir.config_parameter'].sudo()
        if params.get_param(PARAM_ALLOW_RESTRICT_ADMIN) in ('1', 'True', 'true'):
            return False
        return user.id in PROTECTED_UIDS or user._is_system()

    # ------------------------------------------------------------------
    # Static tier (cached)
    # ------------------------------------------------------------------

    @api.model
    @tools.ormcache('uid', 'company_id', 'lang', 'debug')
    def _static_policy(self, uid, company_id, lang, debug):
        """Compile all non-time-windowed rules for one user.

        Returns ``(frozen_policy, valid_until, dynamic_rule_ids)``.
        ``valid_until`` is the earliest moment at which this result stops being
        correct because a rule starts or stops applying; ``None`` means never.

        Also decides whether to restrict this user at all. The kill switch and
        the administrator rail belong behind this cache: each only changes
        through a write that clears the registry cache (``set_param``, a group
        change), so caching them is exact, and it keeps them off the per-field
        hot path in ``get_policy``.

        Everything read while compiling is internal, so it is read raw
        (``aam_raw_values``). Nothing in this module looks at that key. A module
        that redacts ``sudo()`` reads (Access Management Pro) honours it: the
        group lookup behind ``_is_system`` serialises ``ir.model.data`` under
        ``sudo()``, and redacting that read would ask for the policy being
        compiled. Set here, behind the cache, so the hot path never builds an
        env for it.
        """
        self = self.with_context(aam_raw_values=RAW_VALUES)
        user = self.env['res.users'].sudo().browse(uid)
        params = self.env['ir.config_parameter'].sudo()
        if params.get_param(PARAM_ENABLED, '1') not in ('1', 'True', 'true'):
            # Master kill switch: every rule inert without uninstalling.
            return _freeze(_empty_policy()), None, ()
        if self._is_protected(user):
            return _freeze(_empty_policy()), None, ()

        rules = self._rules_for_user(user, company_id)

        static = rules.filtered(lambda r: not r.time_window_ids)
        dynamic = rules - static

        policy = _empty_policy()
        self._merge_rules(policy, static)
        return _freeze(policy), self._next_boundary(rules), tuple(dynamic.ids)

    @api.model
    def _rules_for_user(self, user, company_id):
        """Every active, in-date rule that targets this user in this company."""
        now = fields.Datetime.now()
        rules = self.env['aam.rule'].sudo().search([
            ('active', '=', True),
            '|', ('date_from', '=', False), ('date_from', '<=', now),
            '|', ('date_to', '=', False), ('date_to', '>=', now),
        ])

        def keeps(rule):
            if rule.company_ids and company_id not in rule.company_ids.ids:
                return False
            profile = rule.profile_id
            if profile:
                if not profile.active:
                    return False
                if profile.date_start and profile.date_start > now:
                    return False
                if profile.date_end and profile.date_end < now:
                    return False
            return rule._applies_to_user(user)

        return rules.filtered(keeps)

    @api.model
    def _next_boundary(self, rules):
        """Earliest future ``date_from``/``date_to`` among these rules."""
        now = fields.Datetime.now()
        moments = [
            moment
            for rule in rules
            for moment in (rule.date_from, rule.date_to)
            if moment and moment > now
        ]
        return min(moments) if moments else None

    # ------------------------------------------------------------------
    # Dynamic overlay
    # ------------------------------------------------------------------

    @api.model
    def _active_dynamic_rules(self, rule_ids):
        """Of the time-windowed rules, those whose window contains right now."""
        import pytz
        moment = pytz.UTC.localize(fields.Datetime.now())
        rules = self.env['aam.rule'].sudo().browse(rule_ids).exists()
        return rules.filtered(
            lambda r: any(w._matches(moment) for w in r.time_window_ids))

    # ------------------------------------------------------------------
    # Compilation
    # ------------------------------------------------------------------

    @api.model
    def _merge_rules(self, policy, rules):
        """Fold every rule into ``policy`` in place. Deny always wins."""
        for rule in rules.sorted(lambda r: (-r.priority, r.sequence, r.id)):
            self._merge_globals(policy, rule)
            self._merge_menus(policy, rule)
            self._merge_models(policy, rule)
            self._merge_fields(policy, rule)
            self._merge_buttons(policy, rule)
            self._merge_search(policy, rule)
            self._merge_chatter(policy, rule)

    @api.model
    def _merge_globals(self, policy, rule):
        for flag in GLOBAL_FLAGS:
            if getattr(rule, flag, False):
                policy['globals'][flag] = True

    @api.model
    def _merge_menus(self, policy, rule):
        lines = rule.menu_line_ids.filtered('active')
        if lines:
            policy['menus'].update(lines._menu_ids_to_hide())

    @api.model
    def _merge_models(self, policy, rule):
        enforced = rule.enforcement == 'enforced'
        for line in rule.model_line_ids.filtered('active'):
            model = line.model_name
            if not model:
                continue
            entry = policy['models'].setdefault(model, _empty_model_entry())

            entry['blocked'].update(line._blocked_modes())
            for flag in ('hide_archive', 'hide_duplicate', 'hide_export', 'hide_import',
                         'hide_spreadsheet', 'hide_print', 'hide_action_button',
                         'hide_edit_button'):
                if getattr(line, flag):
                    entry[flag] = True

            if line.hide_view_ids:
                # View ids are globally unique, so one set at the top level is
                # enough - a per-model copy would just be state to keep in step.
                policy['views'].update(line.hide_view_ids.ids)
            if line.hide_view_modes:
                entry['hidden_view_modes'].update(
                    m.strip() for m in line.hide_view_modes.split(',') if m.strip())
            if line.hide_report_ids:
                policy['reports'].update(line.hide_report_ids.ids)
            if line.hide_action_ids:
                policy['actions'].update(line.hide_action_ids.ids)
            if line.hide_server_action_ids:
                policy['actions'].update(line.hide_server_action_ids.ids)

            domain_modes = line._domain_modes()
            if domain_modes:
                parsed = self._parse_domain(line.domain)
                if parsed is not None:
                    clause = {
                        'domain': parsed,
                        'soft': line.soft_restrict,
                        'field': line.related_field_id.name or None,
                        'hierarchy': line.hierarchy_field_id.name or None,
                        'enforced': enforced,
                        'rule_id': rule.id,
                    }
                    for mode in domain_modes:
                        entry['domains'].setdefault(mode, []).append(clause)

    @api.model
    def _parse_domain(self, raw):
        """Evaluate a stored domain string, tolerating a bad one.

        A malformed domain must not take the whole policy down - that would lock
        every user out over one typo - so we drop the offending clause and leave
        the rest of the rule standing. The constraint on ``aam.rule.model``
        catches these at save time; this is the backstop for domains that stop
        parsing later, say because a field was removed.
        """
        if not raw:
            return None
        try:
            parsed = safe_eval(raw, {'user': self.env.user, 'uid': self.env.uid})
        except Exception:
            return None
        return parsed if isinstance(parsed, (list, tuple)) else None

    @api.model
    def _merge_fields(self, policy, rule):
        enforced = rule.enforcement == 'enforced'
        for line in rule.field_line_ids.filtered('active'):
            model, fname = line.model_name, line.field_name
            if not model or not fname:
                continue
            entry = policy['fields'].setdefault(model, {}).setdefault(
                fname, _empty_field_entry())

            # A scoped line only hides, and only in the arch of that view type.
            # It must not set `invisible`: that flag means the field does not
            # exist for this user, and removes it from fields_get and read().
            if line.view_mode and line.view_mode != 'all':
                if line.invisible:
                    entry['view_invisible'].add(line.view_mode)
                continue

            for flag in ('invisible', 'readonly', 'required', 'no_open', 'no_create',
                         'no_quick_create', 'no_create_edit', 'no_export'):
                if getattr(line, flag):
                    entry[flag] = True

            if line.condition:
                entry['conditions'].append(line.condition)
            if line.field_domain:
                parsed = self._parse_domain(line.field_domain)
                if parsed is not None:
                    entry['domains'].append(parsed)

            if line.mask_type and line.mask_type != 'none' and entry['mask'] is None:
                # Rules arrive highest priority first, so the first mask wins -
                # which is what the `priority` field promises.
                entry['mask'] = {
                    'type': line.mask_type,
                    'char': line.mask_char or '*',
                    'keep': line.mask_keep or 0,
                    'pattern': line.mask_pattern or '',
                }
            if enforced:
                entry['enforced'] = True

    @api.model
    def _merge_buttons(self, policy, rule):
        for line in rule.button_line_ids.filtered('active'):
            model = line.model_name
            if not model:
                continue
            policy['buttons'].setdefault(model, []).append({
                'type': line.element_type,
                'name': line.element_name,
                'view_mode': line.view_mode,
                'condition': line.condition or None,
            })

    @api.model
    def _merge_search(self, policy, rule):
        for line in rule.search_line_ids.filtered('active'):
            model = line.model_name
            if not model:
                continue
            entry = policy['search'].setdefault(model, _empty_search_entry())
            entry['filters'].update(line._hidden_filter_names())
            entry['groupbys'].update(line._hidden_groupby_names())
            for flag in ('hide_all_filters', 'hide_all_groupby', 'hide_custom_filter',
                         'hide_custom_groupby', 'hide_delete_filter', 'hide_favourite',
                         'hide_search_panel'):
                if getattr(line, flag):
                    entry[flag] = True

    @api.model
    def _merge_chatter(self, policy, rule):
        for line in rule.chatter_line_ids.filtered('active'):
            model = line.model_name
            if not model:
                continue
            entry = policy['chatter'].setdefault(model, {})
            for flag in ('hide_chatter', 'hide_send_message', 'hide_log_note',
                         'hide_activity', 'hide_followers', 'hide_attachments'):
                if getattr(line, flag):
                    entry[flag] = True

    # ------------------------------------------------------------------
    # Pre-authentication lookups
    # ------------------------------------------------------------------
    # These run before there is a user to compile a policy for, so they query
    # the rules directly rather than going through the per-user cache.

    @api.model
    @tools.ormcache()
    def _login_disabled_user_ids(self):
        """Users whose login is blocked by an active rule (feature H3)."""
        return self._users_with_global_flag('disable_login')

    @api.model
    @tools.ormcache()
    def _rpc_blocked_user_ids(self):
        """Users barred from non-interactive authentication (feature H12)."""
        return self._users_with_global_flag('restrict_rpc')

    @api.model
    def _users_with_global_flag(self, flag):
        params = self.env['ir.config_parameter'].sudo()
        if params.get_param(PARAM_ENABLED, '1') not in ('1', 'True', 'true'):
            return frozenset()

        rules = self.env['aam.rule'].sudo().search([
            ('active', '=', True), (flag, '=', True),
        ])
        now = fields.Datetime.now()
        reached = set()
        for rule in rules:
            if rule.date_from and rule.date_from > now:
                continue
            if rule.date_to and rule.date_to < now:
                continue
            if rule.profile_id and not rule.profile_id.active:
                continue
            targeted = rule._targeted_user_ids()
            if targeted is None:
                # 'Everyone'. Blocking every login would brick the database, so
                # this is deliberately treated as reaching nobody here - the
                # constraint on aam.rule already refuses such a rule unless
                # administrator protection was turned off on purpose.
                continue
            reached.update(targeted)

        if not reached:
            return frozenset()

        # Never lock out a protected account through this path.
        users = self.env['res.users'].sudo().browse(sorted(reached)).exists()
        return frozenset(u.id for u in users if not self._is_protected(u))
