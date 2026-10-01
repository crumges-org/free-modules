from odoo import fields, models


class AamRuleChatter(models.Model):
    """Per-model chatter restrictions (features G1-G6).

    Six independent switches rather than one, because the common request is
    "they may read the history but not post" - a single on/off cannot express
    that.
    """

    _name = 'aam.rule.chatter'
    _inherit = ['aam.rule.model.line.mixin']
    _description = 'Chatter Restriction'

    hide_chatter = fields.Boolean('Hide Whole Chatter')
    hide_send_message = fields.Boolean('Hide Send Message')
    hide_log_note = fields.Boolean('Hide Log Note')
    hide_activity = fields.Boolean('Hide Activities')
    hide_followers = fields.Boolean('Hide Followers')
    hide_attachments = fields.Boolean('Hide Attachments')

    _sql_constraints = [
        ('chatter_uniq',
         'UNIQUE (rule_id, model_id)',
         'This model already has a chatter restriction in this rule.'),
    ]
