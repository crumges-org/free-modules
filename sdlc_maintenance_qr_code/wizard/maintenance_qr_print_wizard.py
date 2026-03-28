from odoo import api, fields, models, _


class MaintenanceQrPrintWizard(models.TransientModel):
    _name = "maintenance.qr.print.wizard"
    _description = "Maintenance QR Print Wizard"

    equipment_ids = fields.Many2many(
        "maintenance.equipment",
        string="Equipment",
    )
    copies = fields.Integer(
        string="Copies",
        default=1,
    )
    size = fields.Selection(
        [
            ("dymo", "Dymo (1x1)"),
            ("2x7xprice", "2 x 7"),
            ("4x7xprice", "4 x 7"),
            ("custom", "Custom"),
        ],
        string="Label Layout",
        default="2x7xprice",
        required=True,
    )
    custom_columns = fields.Integer(
        string="Columns",
        default=2,
    )
    custom_rows = fields.Integer(
        string="Rows",
        default=7,
    )
    header_color = fields.Char(
        string="Header Color",
        default="#6b4096",
    )
    rows = fields.Integer(
        string="Rows (Computed)",
        compute="_compute_grid",
    )
    columns = fields.Integer(
        string="Columns (Computed)",
        compute="_compute_grid",
    )

    @api.depends("size", "custom_columns", "custom_rows")
    def _compute_grid(self):
        layout_map = {
            "dymo": (1, 1),
            "2x7xprice": (2, 7),
            "4x7xprice": (4, 7),
        }
        for rec in self:
            if rec.size == "custom":
                rec.columns = rec.custom_columns or 2
                rec.rows = rec.custom_rows or 7
            else:
                cols, rows = layout_map.get(rec.size, (2, 7))
                rec.columns = cols
                rec.rows = rows

    def action_print(self):
        self.ensure_one()
        return self.env.ref(
            "sdlc_maintenance_qr_code.action_report_maintenance_equipment_qr"
        ).report_action(self)
