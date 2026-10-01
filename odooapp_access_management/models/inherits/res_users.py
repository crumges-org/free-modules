from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessDenied, UserError
from odoo.osv import expression


class ResUsers(models.Model):
    _inherit = 'res.users'

    # -- Password expiry (feature J1) --------------------------------------
    aam_password_write_date = fields.Datetime(
        'Password Last Changed', readonly=True, copy=False,
        groups='base.group_system')
    aam_password_expiry_date = fields.Datetime(
        'Password Expires', compute='_compute_password_expiry',
        groups='base.group_system')
    aam_password_expired = fields.Boolean(
        'Password Expired', compute='_compute_password_expiry',
        groups='base.group_system')

    # Deliberately no _get_session_token_fields override: see
    # action_aam_force_logout and test_j3_the_module_adds_nothing_to_the_session_token.

    # ------------------------------------------------------------------
    # Login control
    # ------------------------------------------------------------------

    @api.model
    def _get_login_domain(self, login):
        """Refuse to find a user whose login is disabled (feature H3).

        The cleanest of the three possible hooks: ``_login`` searches with this
        domain and raises ``AccessDenied`` on an empty result, so a blocked
        account is indistinguishable from a wrong password - which is also the
        right thing to leak to whoever is trying.
        """
        domain = super()._get_login_domain(login)
        blocked = self.env['aam.policy'].sudo()._login_disabled_user_ids()
        if blocked:
            # Odoo 18 has no `odoo.fields.Domain`; `_get_login_domain` returns a
            # plain list here and `expression.AND` is what combines them.
            domain = expression.AND([domain, [('id', 'not in', list(blocked))]])
        return domain

    def _check_credentials(self, credential, env):
        """Block non-interactive authentication for restricted users (H12).

        ``env['interactive']`` is False for XML-RPC and API-key auth, which is
        exactly the distinction needed. This is a blunt instrument and rarely
        necessary - enforced rules already apply over RPC because they live in
        the ORM, not the UI.
        """
        auth_info = super()._check_credentials(credential, env)
        if env.get('interactive'):
            return auth_info

        uid = auth_info.get('uid') if isinstance(auth_info, dict) else None
        if uid and uid in self.env['aam.policy'].sudo()._rpc_blocked_user_ids():
            self.env['aam.audit.log']._log(
                'login_blocked', user_id=uid, detail='XML-RPC / script access blocked')
            raise AccessDenied(_("External API access is disabled for this account."))
        return auth_info

    @api.model
    def _update_last_login(self):
        """Record successful sign-ins (feature J4).

        ``_login`` calls this only after credentials check out, and unlike
        ``_login`` itself it runs with a normal environment - so there is no
        need to build a cursor by hand just to write one audit row.
        """
        res = super()._update_last_login()
        self.env['aam.audit.log']._log('login', user_id=self.env.uid)
        return res

    # ------------------------------------------------------------------
    # Password expiry (feature J1)
    # ------------------------------------------------------------------

    @api.depends('aam_password_write_date')
    def _compute_password_expiry(self):
        days = self._aam_expiry_days()
        now = fields.Datetime.now()
        for user in self:
            if not days or not user.aam_password_write_date:
                user.aam_password_expiry_date = False
                user.aam_password_expired = False
                continue
            expiry = user.aam_password_write_date + timedelta(days=days)
            user.aam_password_expiry_date = expiry
            user.aam_password_expired = expiry < now

    @api.model
    def _aam_expiry_days(self):
        raw = self.env['ir.config_parameter'].sudo().get_param('aam.password_expiry_days', 0)
        try:
            return int(raw or 0)
        except (TypeError, ValueError):
            return 0

    def _set_password(self):
        super()._set_password()
        # sudo: the field is group-restricted, and a user changing their own
        # password is exactly who needs the stamp updated.
        self.sudo().with_context(aam_skip_epoch=True).write({
            'aam_password_write_date': fields.Datetime.now()})

    @api.model
    def _cron_password_expiry_reminder(self):
        """Warn at 7 days and again at 1 day before expiry (feature J1)."""
        days = self._aam_expiry_days()
        if not days:
            return 0
        template = self.env.ref(
            'odooapp_access_management.mail_template_password_expiry',
            raise_if_not_found=False)
        if not template:
            return 0

        now = fields.Datetime.now()
        sent = 0
        for warn_at in (7, 1):
            target = now + timedelta(days=warn_at)
            window_start = target - timedelta(hours=12)
            window_end = target + timedelta(hours=12)
            users = self.sudo().search([
                ('active', '=', True),
                ('share', '=', False),
                ('aam_password_write_date', '!=', False),
                ('aam_password_write_date', '>=', window_start - timedelta(days=days)),
                ('aam_password_write_date', '<', window_end - timedelta(days=days)),
            ])
            for user in users:
                if not user.email:
                    continue
                template.with_context(aam_days_left=warn_at).send_mail(
                    user.id, force_send=False)
                sent += 1
        return sent

    # ------------------------------------------------------------------
    # Force logout (feature J3)
    # ------------------------------------------------------------------

    def action_aam_force_logout(self):
        """Sign this user out of every session they currently hold.

        This used to bump a counter that was part of the session token. Any
        field added to the token signs *every* user out when the module is
        installed, and it broke odoo.sh's Connect button, which builds its
        session outside the normal login. Odoo 19 already deletes a user's
        sessions through ``res.device``, with no change to the token.
        """
        self._aam_check_manager()
        for user in self:
            if user._is_system() and user != self.env.user:
                raise UserError(_(
                    "%s is an administrator. Sign them out from their own session "
                    "rather than forcing it here.", user.name))
            # Odoo's own device revocation: deletes the sessions from the store
            # and marks the devices revoked. Never the caller's own session.
            devices = self.env['res.device'].sudo().search([('user_id', '=', user.id)])
            devices.filtered(lambda d: not d.is_current)._revoke()
            self.env['aam.audit.log']._log(
                'logout', user_id=user.id, detail=_("Forced by %s", self.env.user.name))
        return True

    def _aam_check_manager(self):
        if not self.env.user.has_group('odooapp_access_management.group_aam_manager'):
            raise UserError(_("Only an Access Management administrator can do that."))

    # ------------------------------------------------------------------
    # Impersonation (feature J2)
    # ------------------------------------------------------------------

    def action_aam_impersonate(self):
        """Open a session as this user.

        Deliberately narrow: an Access Management administrator only, never
        another administrator as the target, and always audited. Impersonation
        is the single most abusable feature in this category - the audit row is
        written *before* the switch, so it survives even if the session is then
        used to try to cover the tracks.

        Prefer 'Simulate As' where you only need to see what someone sees; it
        renders under their policy without borrowing their identity.
        """
        self.ensure_one()
        self._aam_check_manager()
        if not self.env.user.has_group('base.group_system'):
            raise UserError(_("Only a Settings administrator can sign in as another user."))
        if self._is_system():
            raise UserError(_(
                "%s is an administrator. Signing in as another administrator is not "
                "allowed - it would defeat the audit trail.", self.name))
        if not self.active or self.share:
            raise UserError(_("You can only sign in as an active internal user."))

        self.env['aam.audit.log']._log(
            'impersonate', user_id=self.env.uid,
            detail=_("%(who)s signed in as %(target)s",
                     who=self.env.user.name, target=self.name))
        return {
            'type': 'ir.actions.act_url',
            'url': '/aam/impersonate/%s' % self.id,
            'target': 'self',
        }
