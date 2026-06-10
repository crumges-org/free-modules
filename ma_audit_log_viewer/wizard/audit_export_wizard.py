import base64
import io

from odoo import api, fields, models


class AuditExportWizard(models.TransientModel):
    _name = 'audit.export.wizard'
    _description = 'Audit Log Export'

    date_from = fields.Datetime(
        required=True,
        default=lambda s: fields.Datetime.now(),
        string='From',
    )
    date_to = fields.Datetime(
        required=True,
        default=lambda s: fields.Datetime.now(),
        string='To',
    )
    user_ids = fields.Many2many('res.users', string='Filter by User (optional)')
    model_name = fields.Char(string='Filter by Model (optional)',
                             help='e.g. res.partner — leave empty for all')
    export_format = fields.Selection(
        [('excel', 'Excel (.xlsx)'), ('pdf', 'PDF')],
        default='excel',
        required=True,
        string='Format',
    )

    def action_export(self):
        logs = self._get_logs()
        if self.export_format == 'excel':
            return self._export_excel(logs)
        return self._export_pdf(logs)

    def _get_logs(self):
        domain = [('date', '>=', self.date_from), ('date', '<=', self.date_to)]
        if self.user_ids:
            domain.append(('user_id', 'in', self.user_ids.ids))
        if self.model_name:
            domain.append(('model_name', '=', self.model_name.strip()))
        return self.env['audit.log.line'].search(
            domain, order='date desc', limit=10000
        )

    def _export_excel(self, logs):
        import xlsxwriter
        buf = io.BytesIO()
        wb = xlsxwriter.Workbook(buf, {'in_memory': True})
        ws = wb.add_worksheet('Audit Log')

        hdr_fmt = wb.add_format({
            'bold': True,
            'bg_color': '#1B2A4A',
            'font_color': '#FFFFFF',
            'border': 1,
        })
        headers = [
            'Date', 'Model', 'Record', 'Field',
            'Operation', 'Changed By', 'Old Value', 'New Value',
        ]
        col_widths = [20, 20, 25, 20, 12, 20, 30, 30]
        for col, (h, w) in enumerate(zip(headers, col_widths)):
            ws.write(0, col, h, hdr_fmt)
            ws.set_column(col, col, w)

        for row, log in enumerate(logs, start=1):
            ws.write(row, 0, str(log.date or ''))
            ws.write(row, 1, log.model_name or '')
            ws.write(row, 2, log.res_name or '')
            ws.write(row, 3, log.field_label or '')
            ws.write(row, 4, log.operation or '')
            ws.write(row, 5, log.user_id.name if log.user_id else '')
            ws.write(row, 6, log.old_value or '')
            ws.write(row, 7, log.new_value or '')

        wb.close()
        data = base64.b64encode(buf.getvalue())
        attachment = self.env['ir.attachment'].create({
            'name': 'audit_log.xlsx',
            'datas': data,
            'mimetype': (
                'application/vnd.openxmlformats-officedocument'
                '.spreadsheetml.sheet'
            ),
            'res_model': self._name,
            'res_id': self.id,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def _export_pdf(self, logs):
        return (
            self.env.ref('ma_audit_log_viewer.action_report_audit_log')
            .report_action(logs)
        )
