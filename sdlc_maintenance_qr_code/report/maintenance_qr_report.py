import math

from odoo import api, models


class ReportMaintenanceEquipmentQr(models.AbstractModel):
    _name = "report.sdlc_maintenance_qr_code.report_maintenance_equipment_qr"
    _description = "Maintenance Equipment QR Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env["maintenance.qr.print.wizard"].browse(docids)
        wizard.ensure_one()

        equipments = wizard.equipment_ids
        columns = wizard.columns
        rows = wizard.rows
        copies = wizard.copies or 1
        header_color = wizard.header_color or "#6b4096"

        # Build the list of equipment entries (with copies)
        items = []
        for eq in equipments:
            for _i in range(copies):
                items.append(eq)

        # Calculate QR pixel size based on layout
        per_page = columns * rows
        total_pages = math.ceil(len(items) / per_page) if per_page else 1

        # QR size varies by layout
        if columns == 1 and rows == 1:
            qr_px = 320
        elif columns <= 2:
            qr_px = 280
        else:
            qr_px = 260

        # Build pages
        pages = []
        for page_idx in range(total_pages):
            start = page_idx * per_page
            page_items = items[start : start + per_page]
            page_rows = []
            for row_idx in range(rows):
                row_start = row_idx * columns
                row_items = page_items[row_start : row_start + columns]
                if row_items:
                    page_rows.append(row_items)
            if page_rows:
                pages.append(page_rows)

        company = self.env.company

        return {
            "doc_ids": docids,
            "doc_model": "maintenance.qr.print.wizard",
            "docs": wizard,
            "pages": pages,
            "columns": columns,
            "rows": rows,
            "qr_px": qr_px,
            "header_color": header_color,
            "company": company,
        }
