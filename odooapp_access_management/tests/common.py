import os
import pathlib
import time
from unittest.mock import patch

from odoo.tests import TransactionCase

#: The file Chrome writes its remote-debugging port into.
_PORT_FILE = 'DevToolsActivePort'
_path_open = pathlib.Path.open


def _open_port_file_patiently(self, *args, **kwargs):
    """``Path.open``, retrying while Chrome still holds ``DevToolsActivePort``.

    Every other path is passed straight through.
    """
    if self.name != _PORT_FILE:
        return _path_open(self, *args, **kwargs)
    for _ in range(40):
        try:
            return _path_open(self, *args, **kwargs)
        except PermissionError:
            time.sleep(0.05)
    return _path_open(self, *args, **kwargs)


class ChromeSpawnTolerance:
    """Keep Windows from turning a Chrome start-up race into a skipped tour.

    Not a bug in this module, and nothing here touches what the tours assert.
    Chrome writes ``DevToolsActivePort`` into its profile and keeps it locked
    for a moment; Odoo's ``_spawn_chrome`` opens it as soon as it has content,
    and on Windows that open can hit the lock and raise ``PermissionError``.
    ``_chrome_start`` turns *any* ``OSError`` into
    ``SkipTest("<chrome.exe> not found")``, so the tour is skipped, the run still
    says "0 failed", and the Chrome process is left running.

    Measured on this machine with Chrome 154: 5 launches in 15 hit it, outside
    Odoo, with nothing else running - a race, not orphaned processes.

    The fix retries that one ``open``. It patches ``pathlib.Path.open`` rather
    than ``_spawn_chrome`` because every Odoo version reads the port file the
    same way while the rest of ``_spawn_chrome`` differs between them. Windows
    only, and only for the class that mixes it in.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if os.name == 'nt':
            patcher = patch.object(pathlib.Path, 'open', _open_port_file_patiently)
            patcher.start()
            cls.addClassCleanup(patcher.stop)


class AamCommon(TransactionCase):
    """Shared fixtures.

    Every enforcement test needs a user who is *not* an administrator:
    administrators are deliberately exempt from every rule (the safety rail), so
    asserting against one would pass for the wrong reason.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Rule = cls.env['aam.rule']
        cls.Profile = cls.env['aam.profile']
        cls.Policy = cls.env['aam.policy']

        cls.internal_group = cls.env.ref('base.group_user')
        # Partner manager, so the test users can genuinely create/write/delete
        # contacts. Without it the native ACL denies everything and our own
        # restrictions would never be what the assertions actually measure.
        cls.partner_manager = cls.env.ref('base.group_partner_manager')
        cls.crew = cls.env['res.groups'].create({'name': 'AAM Test Crew'})

        base_groups = [cls.internal_group.id, cls.partner_manager.id]
        # `email` is required, not cosmetic: Odoo 18's `message_post` calls
        # `_message_compute_author(..., raise_on_email=True)` and raises
        # "please configure the sender's email address" when the author partner
        # has none (mail/models/mail_thread.py:2247). Odoo 19 has no such
        # parameter and never raises, which is why the chatter tests passed
        # there with no email at all.
        cls.user = cls.env['res.users'].create({
            'name': 'Test Operator',
            'login': 'aam_test_operator',
            'email': 'aam_test_operator@example.com',
            'groups_id': [(6, 0, base_groups + [cls.crew.id])],
        })
        cls.other_user = cls.env['res.users'].create({
            'name': 'Test Bystander',
            'login': 'aam_test_bystander',
            'email': 'aam_test_bystander@example.com',
            'groups_id': [(6, 0, base_groups)],
        })

        cls.partner_model = cls.env['ir.model']._get('res.partner')
        cls.company_partner = cls.env['res.partner'].create({
            'name': 'AAM Alpha Ltd', 'is_company': True,
            'phone': '+91 98765 43210', 'email': 'alpha@example.com',
            'comment': 'confidential note',
        })
        cls.person_partner = cls.env['res.partner'].create({
            'name': 'AAM Bravo Person', 'is_company': False,
            'phone': '+91 12345 67890', 'email': 'bravo@example.com',
        })

        cls.env['ir.config_parameter'].sudo().set_param('aam.enabled', '1')
        cls.env['ir.config_parameter'].sudo().set_param('aam.allow_restrict_admin', '0')

    def field_id(self, model, field):
        return self.env['ir.model.fields']._get(model, field).id

    def model_id(self, model):
        return self.env['ir.model']._get(model).id

    def as_user(self, user=None):
        """An environment acting as the test user, with caches dropped.

        Rule writes already clear the policy cache, but tests mutate rules
        between assertions far faster than a real session would, so being
        explicit here keeps failures honest.
        """
        self.env.registry.clear_cache('groups')
        self.env.registry.clear_cache()
        return self.env(user=user or self.user)

    def policy_for(self, user=None):
        return self.Policy.with_user(user or self.user).get_policy()

    def mask_rule(self, model, field, mask_type='phone', keep=4, user=None, **extra):
        """One enforced rule masking ``model.field`` for ``user`` (default: the operator)."""
        line = {'model_id': self.model_id(model), 'field_id': self.field_id(model, field),
                'mask_type': mask_type, 'mask_keep': keep}
        line.update(extra)
        return self.Rule.create({
            'name': 'Mask %s.%s' % (model, field), 'target_type': 'user',
            'user_ids': [(6, 0, [(user or self.user).id])],
            'field_line_ids': [(0, 0, line)],
        })
