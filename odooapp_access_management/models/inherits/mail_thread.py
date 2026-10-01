from odoo import _, models
from odoo.exceptions import AccessError


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _aam_chatter_flags(self):
        """Chatter restrictions for this model, global ones folded in."""
        if self.env.su:
            return {}
        policy = self.env['aam.policy'].get_policy()
        entry = dict(policy['chatter'].get(self._name, {}))
        for flag, value in policy['globals'].items():
            if flag.startswith('hide_') and value and flag in (
                    'hide_chatter', 'hide_send_message', 'hide_log_note',
                    'hide_activity', 'hide_followers', 'hide_attachments'):
                entry[flag] = True
        return entry

    def message_post(self, **kwargs):
        """Enforce chatter restrictions server-side (features G1-G4).

        Hiding the composer in the browser is not enough - the endpoint stays
        callable. Which switch applies depends on the subtype: a log note and a
        broadcast message use the same method.
        """
        flags = self._aam_chatter_flags()
        if flags:
            subtype = kwargs.get('subtype_xmlid') or ''
            is_note = subtype == 'mail.mt_note' or (
                not subtype and not kwargs.get('subtype_id'))
            if flags.get('hide_chatter'):
                raise AccessError(_("You are not allowed to post on this document."))
            if is_note and flags.get('hide_log_note'):
                raise AccessError(_("You are not allowed to log notes on this document."))
            if not is_note and flags.get('hide_send_message'):
                raise AccessError(_("You are not allowed to send messages on this document."))
        return super().message_post(**kwargs)
