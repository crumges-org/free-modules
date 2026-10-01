from odoo import api, models, tools
from odoo.osv import expression
from odoo.tools import config

from ..aam_constants import SKIP_SOFT

#: How far up a parent chain hierarchy access walks.
#:
#: We expand the chain into nested ``any`` clauses rather than materialising the
#: matching ids, because ``_compute_domain`` is cached until a *rule* changes -
#: an id list baked in here would silently stop covering records created later.
#: Six levels covers any realistic org chart or category tree.
HIERARCHY_DEPTH = 6


class IrRule(models.Model):
    _inherit = 'ir.rule'

    @api.model
    def _compute_domain_keys(self):
        """Make the soft-restrict flag part of the cache key.

        ``_compute_domain`` is ormcached, so a context flag that changes its
        result *must* be declared here or reads would be served a domain
        computed under the opposite flag.
        """
        return super()._compute_domain_keys() + ['aam_skip_soft']

    def _compute_domain_context_values(self):
        """Also key the cached domain on the time-windowed rules active now.

        ``_compute_domain`` stays cached until a rule changes, and a time
        window opening or closing changes no rule - so without this a windowed
        record restriction kept whatever state it had when first cached.
        """
        yield from super()._compute_domain_context_values()
        yield self.env['aam.policy']._access_fingerprint()

    @api.model
    @tools.conditional(
        'xml' not in config['dev_mode'],
        tools.ormcache('self.env.uid', 'self.env.su', 'model_name', 'mode',
                       'tuple(self._compute_domain_context_values())'),
    )
    def _compute_domain(self, model_name, mode="read"):
        """AND our record-level restrictions onto Odoo's own (features D1-D6).

        Odoo 18 has no ``odoo.fields.Domain``; domains are plain nested lists
        combined through ``odoo.osv.expression``. ``super()`` returns ``[]`` when
        no native rule applies, and ``expression.normalize_domain([])`` is the
        AND-unit, which ``combine`` skips - so passing it straight through is
        safe. There is also no ``.optimize()`` on this version; the extra term
        that produced is a query-planner nicety, not a correctness requirement.
        """
        domain = super()._compute_domain(model_name, mode)

        extra = self._aam_domains(model_name, mode)
        if not extra:
            return domain
        return expression.AND([domain] + extra)

    @api.model
    def _aam_domains(self, model_name, mode):
        """Build this user's extra domains for one model and mode."""
        if self.env.su:
            return []
        policy = self.env['aam.policy'].get_policy()
        entry = policy['models'].get(model_name)
        if not entry:
            return []
        clauses = entry['domains'].get(mode)
        if not clauses:
            return []

        skip_soft = self.env.context.get('aam_skip_soft') is SKIP_SOFT
        model = self.env[model_name]
        out = []
        for clause in clauses:
            if clause['soft'] and skip_soft:
                # Soft restriction: filters lists, but leaves a record reachable
                # when something else legitimately points at it. See _check_access
                # on the base model, which sets the flag.
                continue
            built = self._build_clause(model, clause)
            if built is not None:
                out.append(built)
        return out

    @api.model
    def _build_clause(self, model, clause):
        """Turn one compiled clause into a domain, or None if inapplicable."""
        try:
            base = expression.normalize_domain(clause['domain'])
        except Exception:
            # A domain that no longer parses (a removed field, say) must not
            # take every user's access down with it.
            return None

        field_name = clause.get('field')
        if field_name and field_name in model._fields:
            # Restrict through a relational field rather than the model itself.
            return [(field_name, 'any', base)]

        hierarchy = clause.get('hierarchy')
        if hierarchy and hierarchy in model._fields:
            return self._expand_hierarchy(base, hierarchy)

        return base

    @api.model
    def _expand_hierarchy(self, base, field_name):
        """Match the record, or anything beneath a record that matches.

        Expressed as nested ``any`` clauses so it stays a pure domain and never
        goes stale - see HIERARCHY_DEPTH.
        """
        clauses = [base]
        current = base
        for _level in range(HIERARCHY_DEPTH - 1):
            current = [(field_name, 'any', current)]
            clauses.append(current)
        return expression.OR(clauses)
