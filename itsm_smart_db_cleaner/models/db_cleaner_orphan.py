# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2026 IT-Solutions.mg. All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class DbCleanerOrphan(models.Model):
    _name = "db.cleaner.orphan"
    _description = "Orphan Filestore Entry"
    _order = "size_bytes desc"

    scan_id = fields.Many2one(
        "db.cleaner.scan",
        string="Scan",
        required=True,
        ondelete="cascade",
        index=True,
    )
    attachment_id = fields.Many2one(
        "ir.attachment",
        string="Attachment",
        ondelete="set null",
    )
    name = fields.Char(string="Name")
    res_model = fields.Char(string="Linked Model")
    res_id = fields.Integer(string="Linked Record ID")
    reason = fields.Selection(
        [
            ("missing_record", "Linked record missing"),
            ("no_model", "No linked model"),
            ("file_missing", "File missing on disk"),
        ],
        string="Reason",
    )
    size_bytes = fields.Float(string="Size (MB)")
    create_date_attachment = fields.Datetime(string="Created on")

    # -------------------------------------------------------------------------
    # Scan
    # -------------------------------------------------------------------------

    @api.model
    def _scan(self, scan, limit=2000):
        """Detect attachments whose linked record no longer exists."""
        Attachment = self.env["ir.attachment"].sudo()
        # Heuristic 1: orphan attachments with a model + id but no record.
        domain = [("res_model", "!=", False), ("res_id", "!=", 0)]
        attachments = Attachment.search(domain, limit=limit, order="id desc")

        models_map = {}
        for att in attachments:
            models_map.setdefault(att.res_model, set()).add(att.res_id)

        existing = {}
        for model_name, ids in models_map.items():
            if model_name not in self.env:
                # Model removed (uninstalled module): everything is orphan.
                existing[model_name] = set()
                continue
            try:
                found = self.env[model_name].sudo().browse(list(ids)).exists()
                existing[model_name] = set(found.ids)
            except Exception:
                _logger.exception(
                    "Could not check existence on %s", model_name,
                )
                existing[model_name] = set(ids)

        records = []
        total_size = 0.0
        for att in attachments:
            if att.res_id not in existing.get(att.res_model, set()):
                size_mb = round((att.file_size or 0) / 1024.0 / 1024.0, 4)
                total_size += size_mb
                records.append({
                    "scan_id": scan.id,
                    "attachment_id": att.id,
                    "name": att.name,
                    "res_model": att.res_model,
                    "res_id": att.res_id,
                    "reason": "missing_record",
                    "size_bytes": size_mb,
                    "create_date_attachment": att.create_date,
                })

        if records:
            self.create(records)

        scan.write({"orphan_size_mb": round(total_size, 2)})

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def action_open_attachment(self):
        self.ensure_one()
        if not self.attachment_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": "ir.attachment",
            "res_id": self.attachment_id.id,
            "view_mode": "form",
            "target": "current",
        }
