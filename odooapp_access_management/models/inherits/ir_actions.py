from odoo import api, models


class IrActionsActions(models.Model):
    _inherit = 'ir.actions.actions'

    @api.model
    def get_bindings(self, model_name):
        """Filter the Print and Action menus (features B8-B11, B16-B17, H7, H8).

        This is the single point the toolbar is built from - ``get_views``
        reads it for both the ``print`` and ``action`` keys - so filtering here
        covers every view type at once. The backing ``_get_bindings`` is cached
        on ``(model_name, lang)`` only, with group filtering deliberately left
        outside the cache, so it is safe to filter per user here.
        """
        bindings = super().get_bindings(model_name)
        if self.env.su:
            return bindings

        policy = self.env['aam.policy'].get_policy()
        g = policy['globals']
        entry = policy['models'].get(model_name, {})

        hide_reports = g.get('hide_print') or entry.get('hide_print')
        hide_actions = g.get('hide_action_button') or entry.get('hide_action_button')
        hidden_report_ids = policy['reports']
        hidden_action_ids = policy['actions']

        if not (hide_reports or hide_actions or hidden_report_ids or hidden_action_ids):
            return bindings

        result = dict(bindings)
        # `hide_action_button` takes the reports with it. Reports and actions
        # are two separate dropdowns inside `.o_cp_action_menus` - a `fa-print`
        # button and a `fa-cog` Actions menu - and that is true on both 18 and
        # 19: `web/static/src/search/action_menus/action_menus.xml` is identical
        # in the two trees. So clearing only `action` left the *Print* button on
        # screen for any model with a report, which is what "Hide Action (cog)
        # Menu" on `mrp.bom` actually was. (An earlier version of this comment
        # claimed v19 merges the two into one cog; it does not, and neither does
        # v18.) `hide_print` stays the narrower flag that removes only the
        # reports and leaves the rest of the menu alone.
        if hide_reports or hide_actions:
            result['report'] = []
        elif hidden_report_ids:
            result['report'] = [
                a for a in result.get('report', []) if a.get('id') not in hidden_report_ids]

        if hide_actions:
            result['action'] = []
        elif hidden_action_ids:
            result['action'] = [
                a for a in result.get('action', []) if a.get('id') not in hidden_action_ids]
        return result


class IrActionsActWindow(models.Model):
    _inherit = 'ir.actions.act_window'

    def _get_action_dict(self):
        """Strip hidden view types from an action (features B12, B13).

        The web client asks for an action, then loads the views it names. Doing
        this here means a hidden view type never gets requested in the first
        place, rather than being loaded and then blanked.
        """
        result = super()._get_action_dict()
        if self.env.su:
            return result

        self.ensure_one()
        policy = self.env['aam.policy'].get_policy()
        entry = policy['models'].get(result.get('res_model'))
        hidden = set(entry['hidden_view_modes']) if entry else set()
        hidden_ids = set(policy['views'])
        if not hidden and not hidden_ids:
            return result

        # A specific view was named rather than a whole type: unpin it so the
        # action falls back to the model's default view of that type, instead
        # of leaving the user with a screen that will not load.
        if hidden_ids and result.get('views'):
            result = dict(result)
            result['views'] = [
                (False, vtype) if vid in hidden_ids else (vid, vtype)
                for vid, vtype in result['views']
            ]
            if result.get('view_id') and result['view_id'][0] in hidden_ids:
                result['view_id'] = False

        modes = [m for m in (result.get('view_mode') or '').split(',') if m and m not in hidden]
        if not modes:
            # Never leave an action with no views at all - that renders as a
            # broken screen rather than a clear restriction.
            return result

        result = dict(result)
        result['view_mode'] = ','.join(modes)
        if result.get('views'):
            result['views'] = [v for v in result['views'] if v[1] in modes]
        return result
