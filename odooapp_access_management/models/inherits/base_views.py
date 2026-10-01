"""Per-user view-arch injection.

Where this runs matters more than what it does. Odoo splits view loading in two
(v18 ``ir_ui_view.py:2760-2820``; v19 ~3164 - the arrangement is the same on
both)::

    result = dict(self._get_view_cache(view_id, view_type, **options))  # CACHED, user-agnostic
    node = self.env['ir.ui.view']._postprocess_access_rights(node)      # PER-USER, uncached

``_get_view_cache`` is keyed on ``(view_id, view_type, mobile, lang)`` and any
``*_view_ref`` context keys - **no user and no groups**. So any per-user edit
made inside that cache would be served to every other user sharing a language.

We therefore override ``get_view`` and work on the arch *after* ``super()``
returns, which is exactly the point where core does its own per-user pass. The
template cache stays intact, which is what keeps view loading fast.
"""

from lxml import etree

from odoo import api, models

#: View-arch attributes that hold a Python expression (v17+ replaced ``attrs``).
MODIFIERS = ('invisible', 'readonly', 'required', 'column_invisible')

#: Relational widget options we can switch off from the arch.
FIELD_OPTION_FLAGS = {
    'no_open': 'no_open',
    'no_create': 'no_create',
    'no_quick_create': 'no_quick_create',
    'no_create_edit': 'no_create_edit',
}


def _or_modifier(node, attr, expr):
    """OR ``expr`` into a modifier already on the node.

    Restrictions can only ever add reasons for something to be hidden or frozen,
    never remove one - so this is always an OR, never a replacement.
    """
    existing = node.get(attr)
    if expr in ('1', 'True'):
        node.set(attr, '1')
    elif not existing or existing in ('0', 'False'):
        node.set(attr, expr)
    elif existing in ('1', 'True'):
        return
    else:
        node.set(attr, '(%s) or (%s)' % (existing, expr))


def _merge_options(node, flags):
    """Merge boolean widget options into a field node's ``options`` attribute."""
    if not flags:
        return
    import json
    raw = node.get('options')
    try:
        options = json.loads(raw) if raw else {}
    except ValueError:
        # Some views still carry python-ish options; leave them alone rather
        # than corrupting the arch.
        return
    if not isinstance(options, dict):
        return
    options.update({flag: True for flag in flags})
    node.set('options', json.dumps(options))


def _merge_domain(node, extra):
    """AND an extra domain onto a relational field's ``domain`` attribute."""
    existing = (node.get('domain') or '').strip()
    extra_str = repr(list(extra))
    if not existing or existing in ('[]', '"[]"'):
        node.set('domain', extra_str)
    else:
        node.set('domain', '[%s] + %s' % ("'&'", '%s + %s' % (existing, extra_str)))


def _drop(node):
    """Remove a node, preserving surrounding text so the layout does not shift."""
    parent = node.getparent()
    if parent is None:
        return
    tail = node.tail
    previous = node.getprevious()
    parent.remove(node)
    if tail:
        if previous is not None:
            previous.tail = (previous.tail or '') + tail
        else:
            parent.text = (parent.text or '') + tail


class Base(models.AbstractModel):
    _inherit = 'base'

    # ------------------------------------------------------------------
    # Entry points
    # ------------------------------------------------------------------

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        result = super().get_view(view_id=view_id, view_type=view_type, **options)
        if self.env.su:
            return result

        policy = self.env['aam.policy'].get_policy()
        if not self._aam_touches(policy, view_type):
            return result

        try:
            root = etree.fromstring(result['arch'])
        except etree.XMLSyntaxError:
            return result

        self._aam_apply_actions(root, policy, view_type)
        self._aam_apply_fields(root, policy, view_type)
        self._aam_apply_buttons(root, policy, view_type)
        self._aam_apply_search(root, policy, view_type)
        self._aam_apply_chatter(root, policy)

        result = dict(result)
        result['arch'] = etree.tostring(root, encoding='unicode')
        return result

    @api.model
    def _aam_apply_actions(self, root, policy, view_type):
        """Switch off the inline edit affordance (feature B14).

        Distinct from blocking write: some workflows want records edited only
        through their buttons, not by clicking into the form. ``getActiveActions``
        on the client reads these attributes, and core writes the create/delete
        ones from ``has_access`` already - this is the one it has no notion of.
        """
        if policy['models'].get(self._name, {}).get('hide_edit_button'):
            root.set('edit', 'False')

    @api.model
    def _aam_touches(self, policy, view_type):
        """Cheap bail-out so unrestricted models pay almost nothing."""
        model = self._name
        if model in policy['fields'] or model in policy['buttons']:
            return True
        if policy['models'].get(model, {}).get('hide_edit_button'):
            return True
        if view_type == 'search' and (model in policy['search'] or self._aam_global_search(policy)):
            return True
        if view_type == 'form' and (model in policy['chatter']
                                    or policy['globals'].get('hide_chatter')):
            return True
        return False

    @api.model
    def _aam_global_search(self, policy):
        g = policy['globals']
        return any(g.get(flag) for flag in (
            'hide_filter', 'hide_group_by', 'hide_search_panel', 'hide_favourite'))

    # ------------------------------------------------------------------
    # Fields (features C1-C9, C12)
    # ------------------------------------------------------------------

    @api.model
    def _aam_apply_fields(self, root, policy, view_type):
        entries = policy['fields'].get(self._name)
        if not entries:
            return

        invisible_attr = 'column_invisible' if view_type == 'list' else 'invisible'

        for name, entry in entries.items():
            nodes = root.xpath("//field[@name='%s']" % name)
            if not nodes:
                continue

            # A condition turns a hard restriction into a conditional one.
            condition = ' or '.join('(%s)' % c for c in entry['conditions']) \
                if entry['conditions'] else None
            expr = condition or '1'
            # A scoped line hides in this view type only, arch-only, and always
            # unconditionally - a condition from another rule's unscoped line
            # on the same field must not make it conditional.
            scoped = view_type in entry['view_invisible']
            hidden = entry['invisible'] or scoped

            for node in nodes:
                # Skip fields nested in a sub-view of another model: their
                # restrictions belong to that model's own policy entry.
                if self._aam_in_subview(node, root):
                    continue

                if hidden:
                    if self._aam_field_is_absent(entry):
                        # `_has_field_access` already removed this field from
                        # `fields_get`, so leaving the node in the arch makes the
                        # client throw *"field is undefined"* and blanks the whole
                        # view. Dropping it is also the honest rendering: for this
                        # user the field does not exist.
                        _drop(node)
                        continue
                    _or_modifier(node, invisible_attr, '1' if scoped else expr)
                    if view_type == 'search':
                        _drop(node)
                        continue
                if entry['readonly']:
                    _or_modifier(node, 'readonly', expr)
                if entry.get('mask'):
                    self._aam_mask_node(node, name, entry, hidden)
                if entry['required'] and not hidden:
                    _or_modifier(node, 'required', expr)

                flags = [opt for flag, opt in FIELD_OPTION_FLAGS.items() if entry[flag]]
                _merge_options(node, flags)

                for extra in entry['domains']:
                    _merge_domain(node, extra)

    @api.model
    def _aam_field_is_absent(self, entry):
        """True when the policy removes this field from the user's world.

        Delegates rather than repeating the condition: `fields_get`, `read` and
        this arch pass all have to agree about what "hidden" means, so there is
        one definition of it, in `base_records.py`.
        """
        return self._aam_field_is_hidden(entry)

    @api.model
    def _aam_mask_node(self, node, name, entry, hidden):
        """Called for each arch node of a masked field. Does nothing here.

        For a module that changes how a masked field behaves in a view, not
        only what it shows.
        """

    @api.model
    def _aam_in_subview(self, node, root):
        """True when this field belongs to an embedded view of another model."""
        parent = node.getparent()
        while parent is not None and parent is not root:
            if parent.tag in ('list', 'form', 'kanban', 'tree') and parent is not root:
                # An embedded view is itself wrapped in a <field> of this model.
                grandparent = parent.getparent()
                if grandparent is not None and grandparent.tag == 'field':
                    return True
            parent = parent.getparent()
        return False

    # ------------------------------------------------------------------
    # Buttons, tabs, kanban links (features E1-E6)
    # ------------------------------------------------------------------

    @api.model
    def _aam_apply_buttons(self, root, policy, view_type):
        items = policy['buttons'].get(self._name)
        if not items:
            return

        for item in items:
            if item['view_mode'] not in ('all', view_type):
                continue
            for node in self._aam_find_elements(root, item):
                if item['condition']:
                    _or_modifier(node, 'invisible', item['condition'])
                else:
                    _drop(node)

    @api.model
    def _aam_find_elements(self, root, item):
        name = item['name']
        kind = item['type']
        if kind == 'button':
            return root.xpath("//button[@name='%s']" % name)
        if kind == 'tab':
            # Pages are addressed by name when they have one, else by label.
            found = root.xpath("//page[@name='%s']" % name)
            return found or root.xpath("//page[@string='%s']" % name)
        if kind == 'kanban_link':
            return root.xpath("//a[@type='%s']" % name)
        return []

    # ------------------------------------------------------------------
    # Search panel (features F1-F7)
    # ------------------------------------------------------------------

    @api.model
    def _aam_apply_search(self, root, policy, view_type):
        if view_type != 'search':
            return

        entry = policy['search'].get(self._name, {})
        g = policy['globals']

        hide_all_filters = entry.get('hide_all_filters') or g.get('hide_filter')
        hide_all_groupby = entry.get('hide_all_groupby') or g.get('hide_group_by')
        hide_panel = entry.get('hide_search_panel') or g.get('hide_search_panel')

        named_filters = set(entry.get('filters') or ())
        named_groupbys = set(entry.get('groupbys') or ())

        for node in root.xpath('//filter'):
            name = node.get('name') or ''
            is_groupby = 'group_by' in (node.get('context') or '')
            if is_groupby:
                if hide_all_groupby or name in named_groupbys:
                    _drop(node)
            elif hide_all_filters or name in named_filters:
                _drop(node)

        if hide_panel:
            for node in root.xpath('//searchpanel'):
                _drop(node)

    # ------------------------------------------------------------------
    # Chatter (features G1-G6)
    # ------------------------------------------------------------------

    @api.model
    def _aam_apply_chatter(self, root, policy):
        entry = policy['chatter'].get(self._name, {})
        if not (entry.get('hide_chatter') or policy['globals'].get('hide_chatter')):
            return
        # v19 renders the chatter from a <chatter/> tag rather than the old
        # oe_chatter div; drop both so the module also behaves on views that
        # were carried over from an older version.
        for node in root.xpath('//chatter'):
            _drop(node)
        for node in root.xpath("//div[contains(@class, 'oe_chatter')]"):
            _drop(node)
