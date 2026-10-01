"""Record-level enforcement: field visibility, masking, and access checks.

This is the layer that makes the module's restrictions *real*. Competing
modules apply field rules at ``fields_get`` and view-arch level only, so a user
who calls ``read`` over XML-RPC gets everything back. Values are redacted in
``_read_format``, the serialiser under ``read``, ``search_read`` (which in
Odoo 19 never calls ``read``), ``web_read``, ``web_save`` and onchange - so
overriding it once covers the browser and the API alike.
"""

from odoo import _, api, models
from odoo.exceptions import AccessError
from odoo.tools import OrderedSet

from ..aam_constants import SKIP_SOFT
from ..aam_masking import apply_mask


class Base(models.AbstractModel):
    _inherit = 'base'

    # ------------------------------------------------------------------
    # Field metadata
    # ------------------------------------------------------------------

    def _has_field_access(self, field, operation):
        """Freeze fields per the policy (feature C2), and block writes to hidden ones.

        **This method is ours on Odoo 18.** Core introduces it in 19
        (``odoo/orm/models.py:3369``) and calls it from three places; v18 has no
        such hook, so we define it here - keeping the name so the enforcement
        logic reads identically on both branches - and wire it into v18's three
        equivalents by hand: :meth:`check_field_access_rights` (the write path),
        :meth:`create` (v18 performs *no* field check on create at all) and
        :meth:`fields_get` (v18 does not downgrade ``readonly`` from write
        access). Miss any one of the three and field freezing silently stops
        being enforced while still looking enforced.

        Read access is deliberately *not* denied here, even for a field the
        policy hides outright. ``Field.__get__`` consults this on every single
        attribute access, including the ones core computes make internally:
        denying ``read`` made ``account``'s ``_compute_tax_string`` raise
        ``AccessError`` the moment it touched ``list_price``, and that took the
        whole product form down for the user - a hidden price field turned into
        an unopenable record. Odoo's own ``groups=`` fields have the same
        behaviour, but core only ever applies them to fields whose dependants
        it has already made ``sudo``; a rule engine cannot make that promise
        about a field an administrator picks at runtime.

        Hiding therefore happens where it can be done without breaking the ORM:
        :meth:`fields_get` drops the field from the metadata every client and
        the exporter read, :meth:`_read_format` drops it from the values, and
        ``get_view`` drops the node from the arch. See
        :meth:`_aam_field_is_hidden`.
        """
        if self.env.su:
            return True
        # Odoo 18 has no core `_has_field_access`; the per-field primitive is
        # `Field.is_accessible(env)`, which answers the `groups=` question that
        # v19's super() answered. It takes no operation - it is a visibility
        # check - so it is consulted for both and never used to deny read here.
        if not field.is_accessible(self.env):
            return False

        entry = self._aam_field_entry(field.name)
        if not entry:
            return True
        if operation == 'write' and (entry['readonly'] or self._aam_field_is_hidden(entry)):
            return False
        return True

    @api.model
    def _aam_field_is_hidden(self, entry):
        """True when the policy removes this field from the user's world.

        Unconditionally invisible and enforced. Conditional restrictions stay in
        the arch, because whether they apply depends on the record.

        The single definition of "hidden", shared by ``fields_get``, ``read``
        and the arch injection in ``base_views.py`` - they have to agree, or a
        field vanishes from one and survives in another.
        """
        return bool(entry['invisible'] and entry['enforced'] and not entry['conditions'])

    @api.model
    def _aam_hidden_fields(self):
        """Names of the fields this user may not see on this model."""
        policy = self.env['aam.policy'].get_policy()
        return {
            name
            for name, entry in policy['fields'].get(self._name, {}).items()
            if self._aam_field_is_hidden(entry)
        }

    @api.model
    def _aam_frozen_fields(self):
        """Names of the fields this user may not write on this model.

        The same test :meth:`_has_field_access` applies for ``write``, hoisted
        so the two v18 entry points can ask it once per call instead of once per
        field.
        """
        policy = self.env['aam.policy'].get_policy()
        return {
            name
            for name, entry in policy['fields'].get(self._name, {}).items()
            if entry['readonly'] or self._aam_field_is_hidden(entry)
        }

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        """Drop hidden fields, and mark frozen ones readonly (features C1, C2).

        Every client, the exporter and RPC introspection read the model through
        here, so this is what makes a hidden field genuinely absent rather than
        merely unpainted.

        The ``readonly`` half is v18-only work. v19 derives it inside core
        ``fields_get`` from ``_has_field_access(field, 'write')``
        (``odoo/orm/models.py:3363``); v18's ``fields_get``
        (``models.py:3744``) has no such step, so without this a frozen field
        arrives at the client fully editable and feature C2 is UI-only.
        ``Field.get_description`` builds a fresh dict per call
        (``fields.py:862``), so mutating the result is safe.
        """
        result = super().fields_get(allfields=allfields, attributes=attributes)
        if self.env.su:
            return result
        entries = self.env['aam.policy'].get_policy()['fields'].get(self._name)
        if not entries:
            return result
        for name, entry in entries.items():
            if self._aam_field_is_hidden(entry):
                result.pop(name, None)
            elif entry['readonly'] and name in result and 'readonly' in result[name]:
                # `attributes=('type',)` yields a dict without the key at all.
                result[name]['readonly'] = True
        return result

    @api.model
    def check_field_access_rights(self, operation, field_names):
        """Odoo 18's field-access hook - deny the writes the policy freezes.

        v18 checks field access per *list* and **raises** when the caller named
        the fields (``models.py:3777``). ``write()`` is the one core caller that
        passes ``operation='write'`` with the user's own keys
        (``models.py:4724``); ``_update_field_translations`` (``:3898``) is the
        other. On v19 all of this is core's job, via ``_check_field_access``.

        Read short-circuits *before* the policy is looked up on purpose:
        ``_field_to_sql`` (``models.py:2985``) calls this once per field per
        query, so it is the hottest path in the ORM.
        """
        result = super().check_field_access_rights(operation, field_names)
        if self.env.su:
            return result

        if operation in ('write', 'create'):
            if not field_names:
                return result
            frozen = self._aam_frozen_fields()
            invalid = [name for name in field_names if name in frozen]
            if invalid:
                self._aam_log_denial(operation)
                raise AccessError(_(
                    "You are not allowed to change the field(s) \"%(fields)s\" on "
                    "%(document)s. Please contact your system administrator.",
                    fields=', '.join(sorted(invalid)),
                    document=self.env['ir.model']._get(self._name).name or self._name,
                ))
            return result

        # Read, with no explicit field list: drop the hidden ones from the
        # "everything readable" answer. On v19 `read(fields=None)` builds its
        # list from `fields_get` and is covered already; on v18 it builds it
        # from here (`models.py:3856`), which knows nothing about the policy -
        # so without this the hidden columns are fetched from the database and
        # only then stripped by our `read()`. Core filters this same branch in
        # `account_move.py:3219` and `hr_employee.py:197`.
        if not field_names:
            hidden = self._aam_hidden_fields()
            if hidden:
                return [name for name in result if name not in hidden]
        return result

    @api.model_create_multi
    def create(self, vals_list):
        """Close v18's create-time field hole.

        v18's ``create`` goes straight from ``check_access('create')`` to
        ``_prepare_create_values`` (``models.py:4985``) with **no field-level
        check at all**, so without this a user could set a frozen or hidden
        field on a new record even though ``write`` refuses it. v19 closes the
        same hole inline (``orm/models.py:4642-4655``), including the
        ``default_*`` context keys - the other way a value reaches ``create`` -
        so those are covered here too.
        """
        if not self.env.su:
            names = OrderedSet(name for vals in vals_list for name in vals)
            names.update(
                field_name
                for context_key in self.env.context
                if context_key.startswith('default_')
                and (field_name := context_key[8:])
                and field_name in self._fields
            )
            if names:
                self.check_field_access_rights('write', list(names))
        return super().create(vals_list)

    @api.model
    def _aam_field_entry(self, field_name):
        """Compiled restriction for one field of this model, or None."""
        policy = self.env['aam.policy'].get_policy()
        return policy['fields'].get(self._name, {}).get(field_name)

    @api.model
    def _aam_masked_fields(self):
        """``{field_name: mask_spec}`` for this model and user."""
        policy = self._aam_output_policy()
        return self._aam_value_masks(policy['fields'].get(self._name, {}))

    # ------------------------------------------------------------------
    # Value masking
    # ------------------------------------------------------------------

    @api.model
    def _aam_serialising(self):
        """True when values serialised in this env are redacted.

        Outside ``sudo()`` only: internal ``sudo()`` code reads values to send
        or store them and must see them whole. Outside ``sudo()`` the caller
        controls the context (``call_kw`` applies it), so no context key is
        read here.
        """
        return not self.env.su

    @api.model
    def _aam_output_policy(self):
        """The policy values are redacted with."""
        return self.env['aam.policy'].get_policy()

    @api.model
    def _aam_value_masks(self, entries):
        """``{key: mask_spec}`` to apply to this model's serialised values.

        ``entries`` is this model's slice of ``policy['fields']``.
        """
        return {name: entry['mask'] for name, entry in entries.items() if entry.get('mask')}

    def _aam_mask_value(self, name, value, spec):
        """One value of ``name``, redacted."""
        return apply_mask(value, spec)

    def _read_format(self, fnames, load='_classic_read'):
        """Strip hidden values and redact masked ones (features C1, C14).

        Every serialiser ends here: ``read``, ``search_read`` (which in Odoo 19
        never calls ``read``), ``web_read``, ``web_save`` and onchange. It has
        to be done on the way out because the ORM is still allowed to read the
        value internally - see :meth:`_has_field_access`.

        Attribute access (``record.phone``) never comes through here, so
        business code keeps working with real values.
        """
        values_list = super()._read_format(fnames, load=load)
        if not values_list or not self._aam_serialising():
            return values_list
        entries = self._aam_output_policy()['fields'].get(self._name)
        if not entries:
            return values_list

        first = values_list[0]
        # Nothing is stripped under sudo(): an internal caller indexes the keys
        # it asked for. Only reached there when a module redacts sudo() reads.
        hidden = [] if self.env.su else [
            name for name, entry in entries.items()
            if name in first and self._aam_field_is_hidden(entry)]
        masks = [
            (name, spec) for name, spec in self._aam_value_masks(entries).items()
            if name in first and name not in hidden]
        if not hidden and not masks:
            return values_list

        for values in values_list:
            for name in hidden:
                values.pop(name, None)
            for name, spec in masks:
                values[name] = self._aam_mask_value(name, values[name], spec)
        return values_list

    def web_read(self, specification):
        """Never let a hidden field into the specification.

        ``read`` strips the values, but ``web_read`` then walks the
        specification and indexes the result for every relational entry - a
        stripped key would surface as a ``KeyError`` and a 500 rather than a
        clean omission. Dropping it here means an RPC caller that asks for a
        hidden field simply does not get it back.
        """
        if not self.env.su:
            hidden = self._aam_hidden_fields()
            if hidden:
                specification = {
                    name: spec for name, spec in specification.items()
                    if name not in hidden
                } or {'id': {}}
        return super().web_read(specification)

    # ------------------------------------------------------------------
    # Access checks
    # ------------------------------------------------------------------

    def _check_access(self, operation):
        """Apply soft-restricted domains only when browsing this model directly.

        A soft restriction should filter lists without breaking a record that
        something else legitimately points at - restricting Contacts must not
        blank out the customer on every order. ``_check_access`` is the
        direct-access path, so we ask ``ir.rule`` to skip soft clauses here;
        ``_search`` keeps them. The flag is declared in ``_compute_domain_keys``
        so it participates in the rule cache key. Its value is a server-side
        sentinel, not ``True``: the caller controls the context (``call_kw``),
        and a client sending ``aam_skip_soft`` must not lift soft restrictions
        off its searches.
        """
        if self.env.su:
            return super()._check_access(operation)

        result = super(Base, self.with_context(aam_skip_soft=SKIP_SOFT))._check_access(operation)
        if result is not None:
            self._aam_log_denial(operation)
        return result

    def _aam_log_denial(self, operation):
        self.env['aam.audit.log']._log(
            'denial',
            model_name=self._name,
            res_id=self.ids[0] if self.ids else 0,
            operation=operation,
        )

    # ------------------------------------------------------------------
    # Write guard for read-only users
    # ------------------------------------------------------------------

    def _aam_check_readonly_user(self):
        """Block writes for a read-only user (feature H1).

        ``_get_allowed_models`` already returns an empty set for these users, so
        this is belt-and-braces for paths that bypass ``ir.model.access`` - but
        an access module is exactly where belt-and-braces is warranted.
        """
        if self.env.su:
            return
        if self.env['aam.policy'].get_policy()['globals'].get('readonly_user'):
            raise AccessError(_(
                "Your account is read-only. Contact your administrator if you need "
                "to make changes."))
