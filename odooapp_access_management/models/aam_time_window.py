import pytz

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# Mirrors odoo.addons.base.models.res_partner: 'Etc/*' sorted last to avoid
# confusing users.
_TZS = [(tz, tz) for tz in sorted(pytz.all_timezones,
                                  key=lambda tz: tz if not tz.startswith('Etc/') else '_')]

DAYS = [
    ('0', 'Monday'),
    ('1', 'Tuesday'),
    ('2', 'Wednesday'),
    ('3', 'Thursday'),
    ('4', 'Friday'),
    ('5', 'Saturday'),
    ('6', 'Sunday'),
]


class AamTimeWindow(models.Model):
    """A weekday + hour range during which the owning rule is active.

    A rule with no windows is always active. A rule with windows is active
    only inside one of them, evaluated in the window's own timezone so that
    "no access outside office hours" means the office's hours, not UTC.
    """

    _name = 'aam.time.window'
    _description = 'Access Time Window'
    _order = 'day_of_week, hour_from'

    rule_id = fields.Many2one('aam.rule', required=True, ondelete='cascade', index=True)
    day_of_week = fields.Selection(DAYS, required=True, default='0')
    hour_from = fields.Float('From', required=True, default=9.0)
    hour_to = fields.Float('To', required=True, default=18.0)
    tz = fields.Selection(
        _TZS, 'Timezone',
        help="Timezone the hours are expressed in. Leave empty to use the user's own timezone.",
    )

    def _invalidate_policy(self):
        self.env.registry.clear_cache()

    @api.model_create_multi
    def create(self, vals_list):
        windows = super().create(vals_list)
        windows._invalidate_policy()
        return windows

    def write(self, vals):
        res = super().write(vals)
        self._invalidate_policy()
        return res

    def unlink(self):
        res = super().unlink()
        self._invalidate_policy()
        return res

    @api.constrains('hour_from', 'hour_to')
    def _check_hours(self):
        for window in self:
            if not 0.0 <= window.hour_from < 24.0 or not 0.0 < window.hour_to <= 24.0:
                raise ValidationError(_("Hours must fall between 00:00 and 24:00."))
            if window.hour_from >= window.hour_to:
                raise ValidationError(
                    _("The 'From' hour must come before the 'To' hour (got %(f)s to %(t)s).",
                      f=window.hour_from, t=window.hour_to)
                )

    def _matches(self, moment):
        """Return True if ``moment`` (an aware datetime) falls inside this window."""
        self.ensure_one()
        tz_name = self.tz or self.env.user.tz or 'UTC'
        local = moment.astimezone(pytz.timezone(tz_name))
        if str(local.weekday()) != self.day_of_week:
            return False
        hour = local.hour + local.minute / 60.0
        return self.hour_from <= hour < self.hour_to
