from odoo import api, models, tools


class IrModelAccess(models.Model):
    _inherit = 'ir.model.access'

    @api.model
    @tools.ormcache('self.env.uid', 'mode', "self.env['aam.policy']._access_fingerprint()")
    def _get_allowed_models(self, mode='read'):
        """Remove models this user's policy blocks (features B1, B2, H1).

        ``ir.model.access.check`` is a thin wrapper over this, so subtracting
        here covers every CRUD path in the ORM at once - including XML-RPC.

        Re-decorating is safe: ``ormcache`` builds its key from
        ``(self._name, method, *args)`` where ``method`` is the function object,
        so this override gets its own cache slot rather than colliding with the
        base implementation's.

        The key includes the time-windowed rules active right now: a window
        opening or closing changes no rule, so nothing else would clear this.
        """
        allowed = super()._get_allowed_models(mode)
        policy = self.env['aam.policy'].get_policy()

        if policy['globals'].get('readonly_user') and mode in ('create', 'write', 'unlink'):
            return frozenset()

        blocked = {
            model for model, entry in policy['models'].items()
            if mode in entry['blocked']
        }
        if not blocked:
            return allowed
        return frozenset(allowed) - blocked
