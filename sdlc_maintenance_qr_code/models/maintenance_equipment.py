import html
import logging
from urllib.parse import quote_plus

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MaintenanceEquipment(models.Model):
    _inherit = "maintenance.equipment"

    x_equipment_code = fields.Char(
        string="Equipment Code",
        copy=False,
        index=True,
        tracking=True,
    )
    x_qr_payload = fields.Char(
        string="QR Payload",
        compute="_compute_qr_fields",
    )
    x_qr_url = fields.Char(
        string="QR URL",
        compute="_compute_qr_fields",
    )
    x_qr_image_html = fields.Html(
        string="QR Code",
        compute="_compute_qr_fields",
        sanitize=False,
    )
    x_qr_name_display = fields.Char(
        string="Display Name",
        compute="_compute_qr_name_display",
    )
    x_qr_name_entities = fields.Char(
        string="Name (HTML Entities)",
        compute="_compute_qr_name_display",
    )

    _sql_constraints = [
        (
            "unique_equipment_code",
            "unique(x_equipment_code)",
            "Equipment code must be unique!",
        ),
    ]

    @api.depends("x_equipment_code", "company_id")
    def _compute_qr_fields(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "")
        for rec in self:
            if rec.x_equipment_code and rec.id:
                payload = (
                    f"{base_url}/web#id={rec.id}"
                    f"&model=maintenance.equipment&view_type=form"
                )
                rec.x_qr_payload = payload
                encoded = quote_plus(payload)
                rec.x_qr_url = (
                    f"/report/barcode/?barcode_type=QR"
                    f"&value={encoded}&width=220&height=220"
                )
                rec.x_qr_image_html = (
                    f'<img src="{rec.x_qr_url}" '
                    f'alt="QR Code" style="max-width:220px;"/>'
                )
            else:
                rec.x_qr_payload = False
                rec.x_qr_url = False
                rec.x_qr_image_html = False

    @api.depends("name")
    def _compute_qr_name_display(self):
        for rec in self:
            name = rec.name or ""
            rec.x_qr_name_display = self._repair_mojibake(name)
            rec.x_qr_name_entities = self._qr_display_html_entities(name)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._assign_equipment_code_if_needed()
        return records

    def _assign_equipment_code_if_needed(self):
        for rec in self:
            if not rec.x_equipment_code:
                code = self.env["ir.sequence"].next_by_code(
                    "maintenance.equipment.code"
                )
                if code:
                    rec.x_equipment_code = code

    def action_generate_equipment_code(self):
        self.ensure_one()
        if not self.env.user.has_group("maintenance.group_equipment_manager"):
            raise UserError(
                _("Only Equipment Managers can generate equipment codes.")
            )
        if self.x_equipment_code:
            raise UserError(
                _("This equipment already has a code: %s", self.x_equipment_code)
            )
        self._assign_equipment_code_if_needed()

    def action_open_qr_print_wizard(self):
        return {
            "name": _("Print Equipment QR Labels"),
            "type": "ir.actions.act_window",
            "res_model": "maintenance.qr.print.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_equipment_ids": self.ids,
            },
        }

    @staticmethod
    def _repair_mojibake(text):
        """Attempt to repair UTF-8 text that was decoded as latin-1/cp1252."""
        if not text:
            return text
        try:
            repaired = text.encode("cp1252").decode("utf-8")
            return repaired
        except (UnicodeDecodeError, UnicodeEncodeError):
            pass
        try:
            repaired = text.encode("latin-1").decode("utf-8")
            return repaired
        except (UnicodeDecodeError, UnicodeEncodeError):
            pass
        return text

    @staticmethod
    def _qr_display_html_entities(text):
        """Convert text to HTML entities for safe PDF rendering."""
        if not text:
            return text
        return html.escape(text)

    def _qr_display_code(self):
        self.ensure_one()
        return self.x_equipment_code or ""
