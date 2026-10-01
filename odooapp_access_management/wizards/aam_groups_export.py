"""Export the full group/model permission matrix to Excel (feature J5).

Auditors ask for this constantly and there is no way to get it out of Odoo
without a script. One sheet lists the groups and who is in them; the other is
the model matrix - one row per group and model, with the four CRUD columns.
"""

import base64
import io

from odoo import _, fields, models
from odoo.exceptions import UserError
from ..models.aam_group_compat import group_area, group_members


try:
    import xlsxwriter
except ImportError:  # pragma: no cover - xlsxwriter ships with Odoo
    xlsxwriter = None


class AamGroupsExport(models.TransientModel):
    _name = 'aam.groups.export'
    _description = 'Export Security Groups'

    include_users = fields.Boolean('Include Member Lists', default=True)
    include_implied = fields.Boolean(
        'Count Implied Members', default=True, readonly=True,
        help="Has no effect on Odoo 18. Membership is stored already-expanded, so implied members are always counted.")
    only_restricted = fields.Boolean(
        'Only Groups With Access Rules',
        help="Limit to groups targeted by an access rule or profile.")

    data = fields.Binary('File', readonly=True, attachment=False)
    filename = fields.Char(readonly=True)

    def action_export(self):
        self.ensure_one()
        if xlsxwriter is None:
            raise UserError(_(
                "The xlsxwriter library is not available, so Excel export is "
                "disabled on this server."))

        groups = self._groups()
        stream = io.BytesIO()
        book = xlsxwriter.Workbook(stream, {'in_memory': True})
        styles = self._styles(book)
        self._sheet_groups(book, styles, groups)
        self._sheet_matrix(book, styles, groups)
        book.close()

        self.write({
            'data': base64.b64encode(stream.getvalue()),
            'filename': 'security_groups_%s.xlsx' % fields.Date.today().isoformat(),
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'aam.groups.export',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _groups(self):
        Group = self.env['res.groups'].sudo()
        if not self.only_restricted:
            return Group.search([])
        rules = self.env['aam.rule'].sudo().search([])
        profiles = self.env['aam.profile'].sudo().search([])
        ids = set(rules.group_ids.ids) | set(profiles.group_ids.ids)
        return Group.browse(sorted(ids))

    def _styles(self, book):
        return {
            'header': book.add_format({
                'bold': True, 'bg_color': '#2F285E', 'font_color': 'white',
                'border': 1, 'align': 'left', 'valign': 'vcenter'}),
            'cell': book.add_format({'border': 1, 'valign': 'top', 'text_wrap': True}),
            'yes': book.add_format({
                'border': 1, 'align': 'center', 'bg_color': '#D6F5EC'}),
            'no': book.add_format({
                'border': 1, 'align': 'center', 'bg_color': '#FBE3E3',
                'font_color': '#999999'}),
        }

    def _sheet_groups(self, book, styles, groups):
        sheet = book.add_worksheet('Groups')
        headers = ['Privilege', 'Group', 'External ID', 'Members', 'Implied Groups']
        if self.include_users:
            headers.append('Member Logins')
        for col, title in enumerate(headers):
            sheet.write(0, col, title, styles['header'])
        sheet.set_column(0, 1, 28)
        sheet.set_column(2, 2, 42)
        sheet.set_column(3, 4, 18)
        if self.include_users:
            sheet.set_column(5, 5, 60)
        sheet.freeze_panes(1, 0)

        xmlids = groups.get_external_id()
        for row, group in enumerate(groups, start=1):
            # `include_implied` is inert on Odoo 18: membership is stored
            # already-expanded, so direct and implied members are the same rows.
            # See models/aam_group_compat.py.
            members = group_members(group)
            values = [
                group_area(group).name or '',
                group.name or '',
                xmlids.get(group.id, ''),
                len(members),
                ', '.join(group.implied_ids.mapped('name')),
            ]
            if self.include_users:
                values.append(', '.join(sorted(members.mapped('login'))))
            for col, value in enumerate(values):
                sheet.write(row, col, value, styles['cell'])

    def _sheet_matrix(self, book, styles, groups):
        sheet = book.add_worksheet('Model Access')
        for col, title in enumerate(
                ['Group', 'Model', 'Technical Name', 'Create', 'Read', 'Write', 'Delete']):
            sheet.write(0, col, title, styles['header'])
        sheet.set_column(0, 1, 30)
        sheet.set_column(2, 2, 30)
        sheet.set_column(3, 6, 9)
        sheet.freeze_panes(1, 0)

        Access = self.env['ir.model.access'].sudo()
        row = 1
        for group in groups:
            for access in Access.search([('group_id', '=', group.id)], order='name'):
                model = access.model_id
                sheet.write(row, 0, group.name or '', styles['cell'])
                sheet.write(row, 1, model.name or '', styles['cell'])
                sheet.write(row, 2, model.model or '', styles['cell'])
                for col, perm in enumerate(
                        ('perm_create', 'perm_read', 'perm_write', 'perm_unlink'), start=3):
                    granted = access[perm]
                    sheet.write(row, col, 'Yes' if granted else 'No',
                                styles['yes'] if granted else styles['no'])
                row += 1
        if row == 1:
            sheet.write(1, 0, 'No model access rows for the selected groups.',
                        styles['cell'])
