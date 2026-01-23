# -*- coding: utf-8 -*-
from odoo import models, api


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    @api.model
    def get_zatca_dashboard_kpi(self):
        """
        Get company-wide ZATCA KPI statistics for the dashboard header.
        Returns counts for sent, pending, errors, and warnings.
        """
        company = self.env.company

        # Get all sale journals for current company
        sale_journals = self.search([
            ('type', '=', 'sale'),
            ('company_id', '=', company.id),
        ])

        if not sale_journals:
            return {
                'sent': 0,
                'pending': 0,
                'errors': 0,
                'warnings': 0,
            }

        # Get all posted invoices for these journals
        invoices = self.env['account.move'].search([
            ('journal_id', 'in', sale_journals.ids),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', '=', 'posted'),
        ])

        sent = 0
        pending = 0
        errors = 0
        warnings = 0

        for invoice in invoices:
            # Find ZATCA EDI document
            zatca_doc = invoice.edi_document_ids.filtered(
                lambda d: d.edi_format_id.code == 'sa_zatca'
            )

            if not zatca_doc:
                continue

            zatca_doc = zatca_doc[0]

            if zatca_doc.state == 'sent':
                if zatca_doc.blocking_level == 'warning':
                    warnings += 1
                else:
                    sent += 1
            elif zatca_doc.state == 'to_send':
                if zatca_doc.blocking_level == 'error':
                    errors += 1
                else:
                    pending += 1

        return {
            'sent': sent,
            'pending': pending,
            'errors': errors,
            'warnings': warnings,
        }

    @api.model
    def open_zatca_kpi_action(self, kpi_type):
        """
        Open a filtered list of invoices based on ZATCA KPI type clicked.
        """
        company = self.env.company

        # Base domain
        domain = [
            ('journal_id.type', '=', 'sale'),
            ('journal_id.company_id', '=', company.id),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', '=', 'posted'),
            ('edi_document_ids.edi_format_id.code', '=', 'sa_zatca'),
        ]

        # Add specific filters based on type
        if kpi_type == 'sent':
            domain.append(('edi_document_ids.state', '=', 'sent'))
            domain.append(('edi_document_ids.blocking_level', 'in', [False, 'info']))
            title = 'ZATCA Sent Invoices'
        elif kpi_type == 'pending':
            domain.append(('edi_document_ids.state', '=', 'to_send'))
            domain.append(('edi_document_ids.blocking_level', 'in', [False, 'info', 'warning']))
            title = 'ZATCA Pending Invoices'
        elif kpi_type == 'errors':
            domain.append(('edi_document_ids.state', '=', 'to_send'))
            domain.append(('edi_document_ids.blocking_level', '=', 'error'))
            title = 'ZATCA Error Invoices'
        elif kpi_type == 'warnings':
            domain.append(('edi_document_ids.state', '=', 'sent'))
            domain.append(('edi_document_ids.blocking_level', '=', 'warning'))
            title = 'ZATCA Warning Invoices'
        else:
            title = 'ZATCA Invoices'

        return {
            'name': title,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': domain,
            'target': 'current',
            'context': {
                'default_move_type': 'out_invoice',
                'create': False,
            },
        }
