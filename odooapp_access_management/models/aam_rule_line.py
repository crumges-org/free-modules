from odoo import api, fields, models


class AamRuleLineMixin(models.AbstractModel):
    """Shared plumbing for every restriction line.

    All lines hang off a rule, most are scoped to a model, and every one of them
    must drop the compiled-policy cache when it changes - forgetting that on a
    single line model is exactly the kind of bug that makes these modules feel
    flaky, so it lives here rather than being re-implemented six times.
    """

    _name = 'aam.rule.line.mixin'
    _description = 'Access Rule Line Mixin'

    rule_id = fields.Many2one(
        'aam.rule', required=True, ondelete='cascade', index=True)
    active = fields.Boolean(default=True)

    def _invalidate_policy(self):
        self.env.registry.clear_cache('groups')
        self.env.registry.clear_cache()

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._invalidate_policy()
        return lines

    def write(self, vals):
        res = super().write(vals)
        self._invalidate_policy()
        return res

    def unlink(self):
        res = super().unlink()
        self._invalidate_policy()
        return res


class AamRuleModelLineMixin(models.AbstractModel):
    """A restriction line scoped to one model.

    ``model_name`` is stored and indexed on purpose: the policy compiler groups
    every line by technical model name, and resolving that through ``model_id``
    on each read would turn one query into hundreds.
    """

    _name = 'aam.rule.model.line.mixin'
    _inherit = ['aam.rule.line.mixin']
    _description = 'Access Rule Model Line Mixin'

    model_id = fields.Many2one(
        'ir.model', 'Model', required=True, ondelete='cascade', index=True,
        domain=[('transient', '=', False)])
    model_name = fields.Char(
        related='model_id.model', store=True, index=True, string='Model Name')
