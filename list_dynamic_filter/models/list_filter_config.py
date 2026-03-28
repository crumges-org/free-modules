from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ListFilterConfig(models.Model):
    _name = "list.filter.config"
    _description = "List View Filter Configuration"

    name = fields.Char(string="Name", required=True)
    model_id = fields.Many2one(
        "ir.model", string="Model", required=True, ondelete="cascade"
    )
    model_name = fields.Char(related="model_id.model", string="Model Name", store=True)
    active = fields.Boolean(default=True)
    filter_field_ids = fields.One2many(
        "list.filter.config.field", "config_id", string="Filter Fields"
    )

    _sql_constraints = [
        (
            "unique_model",
            "unique(model_id)",
            "A filter configuration already exists for this model!",
        )
    ]

    @api.model
    def action_get_model_name_from_list_view_id(self, view_id):
        view = self.env["ir.ui.view"].sudo().browse(view_id).exists()
        if not view or not view.model:
            return False
        return view.model


class ListFilterConfigField(models.Model):
    _name = "list.filter.config.field"
    _description = "List View Filter Field Configuration"
    _order = "sequence, id"

    name = fields.Char(string="Label", required=True, translate=True)
    sequence = fields.Integer(string="Sequence", default=10)
    config_id = fields.Many2one(
        "list.filter.config",
        string="Filter Config",
        required=True,
        ondelete="cascade",
    )
    field_id = fields.Many2one(
        "ir.model.fields",
        string="Field",
        required=True,
        ondelete="cascade",
        domain="[('model_id', '=', model_id), ('ttype', 'in', ['many2one', 'many2many'])]",  # noqa
    )
    model_id = fields.Many2one(related="config_id.model_id", store=True)
    field_name = fields.Char(related="field_id.name", string="Field Name", store=True)
    field_type = fields.Selection(
        related="field_id.ttype", string="Field Type", store=True
    )
    comodel_name = fields.Char(
        string="Related Model", compute="_compute_comodel_name", store=True
    )

    @api.depends("field_id")
    def _compute_comodel_name(self):
        for record in self:
            record.comodel_name = (
                record.field_id.relation if record.field_id.relation else False
            )

    @api.constrains("field_id")
    def _check_unique_field_id(self):
        for record in self:
            config = record.config_id
            field_count = {}
            for field in config.filter_field_ids:
                if field.field_id.id in field_count:
                    field_count[field.field_id.id] += 1
                else:
                    field_count[field.field_id.id] = 1
            duplicated_fields = [
                self.env["ir.model.fields"].browse(field_id).display_name
                for field_id, count in field_count.items()
                if count > 1
            ]
            if duplicated_fields:
                raise ValidationError(
                    _("The following fields are duplicated in the filter fields: %s")
                    % ", ".join(duplicated_fields)
                )
