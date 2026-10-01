# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from datetime import datetime, date
from calendar import monthrange
import io


class PortalCustomerStatement(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'customer_statement_count' in counters:
            partner = request.env.user.partner_id.commercial_partner_id
            statement_count = request.env['account.move.line'].sudo().search_count([
                ('partner_id', 'child_of', [partner.id]),
                ('account_id.account_type', 'in', ('asset_receivable', 'liability_payable')),
                ('parent_state', '=', 'posted')
            ])
            values['customer_statement_count'] = statement_count
        return values

    @http.route(['/my/customer_statement'], type='http', auth="user", website=True)
    def portal_customer_statement(self, filter_type=None, year=None, month=None, quarter=None,
                                  date_from=None, date_to=None, **kw):
        """Portal Customer Statement - mirrors Partner Ledger report from backend"""
        
        # Parse filter parameters - default to 'year' filter with current year
        filter_type = filter_type or 'year'
        year = int(year) if year and year.isdigit() else date.today().year
        month = int(month) if month and month.isdigit() else None
        quarter = int(quarter) if quarter and quarter.isdigit() else None

        # Compute date range based on filter
        date_from, date_to = self._compute_date_range(
            filter_type, year, month, quarter, date_from, date_to
        )

        user = request.env.user
        partner = user.partner_id.commercial_partner_id
        company = request.env.company
        company_currency = company.currency_id

        # Get all partner IDs (including children)
        partner_ids = request.env['res.partner'].sudo().search([
            '|', ('id', '=', partner.id), ('parent_id', '=', partner.id)
        ]).ids

        # Build the query similar to Partner Ledger report
        # Columns: Journal, Account, Invoice Date, Due Date, Matching, Debit, Credit, Amount Currency, Balance
        query = """
            SELECT
                aml.id,
                aml.date,
                aj.code AS journal_code,
                aml.account_id,
                COALESCE(aml.invoice_date, aml.date) AS invoice_date,
                COALESCE(aml.date_maturity, aml.date) AS due_date,
                aml.matching_number,
                aml.debit,
                aml.credit,
                aml.amount_currency,
                aml.currency_id,
                rc.symbol AS currency_symbol,
                rc.position AS currency_position,
                am.name AS move_name,
                aml.name AS line_name,
                aml.ref AS line_ref
            FROM account_move_line aml
            JOIN account_move am ON am.id = aml.move_id
            JOIN account_account aa ON aa.id = aml.account_id
            LEFT JOIN account_journal aj ON aj.id = aml.journal_id
            LEFT JOIN res_currency rc ON rc.id = aml.currency_id
            WHERE aml.partner_id IN %s
              AND aa.account_type IN ('asset_receivable', 'liability_payable')
              AND am.state = 'posted'
            ORDER BY aml.date ASC, aml.id ASC
        """
        request.env.cr.execute(query, (tuple(partner_ids),))
        all_rows = request.env.cr.fetchall()
        
        # Get account codes using ORM (code_store is company-dependent in Odoo 18)
        account_ids = list(set(row[3] for row in all_rows if row[3]))
        accounts = request.env['account.account'].sudo().browse(account_ids)
        account_code_map = {acc.id: acc.code for acc in accounts}

        # Process all lines and compute running balance
        full_lines = []
        running_balance = 0.0

        today = date.today()
        for row in all_rows:
            (_id, dt, journal_code, account_id, invoice_date, due_date, matching_number,
             debit, credit, amount_currency, currency_id, currency_symbol, currency_position,
             move_name, line_name, line_ref) = row

            balance_change = float(debit or 0) - float(credit or 0)
            running_balance += balance_change

            # Format the reference/name similar to backend
            name = self._format_aml_name(line_name, line_ref, move_name)

            # Format dates for display (QWeb doesn't have hasattr)
            invoice_date_display = invoice_date.strftime('%d/%m/%Y') if invoice_date else ''
            due_date_display = due_date.strftime('%d/%m/%Y') if due_date else ''
            is_overdue = bool(due_date and due_date < today)
            
            # Get account code from map
            account_code = account_code_map.get(account_id, '')

            full_lines.append({
                'id': _id,
                'date': dt,
                'journal_code': journal_code or '',
                'account_code': account_code,
                'invoice_date': invoice_date_display,
                'due_date': due_date_display,
                'is_overdue': is_overdue,
                'matching_number': matching_number or '',
                'debit': float(debit or 0),
                'credit': float(credit or 0),
                'amount_currency': float(amount_currency or 0),
                'currency_id': currency_id,
                'currency_symbol': currency_symbol,
                'currency_position': currency_position,
                'balance': running_balance,
                'name': name,
                'move_name': move_name,
            })

        # Filter by date range
        def in_range(line):
            line_date = line['date']
            if date_from and line_date < date_from:
                return False
            if date_to and line_date > date_to:
                return False
            return True

        # Build statement lines with initial balance
        statement_lines = []
        initial_balance = 0.0
        initial_debit = 0.0
        initial_credit = 0.0
        total_debit = 0.0
        total_credit = 0.0

        if date_from:
            # Calculate initial balance from lines before the date range
            # Sum up all debits and credits separately (like backend Partner Ledger)
            prev_lines = [l for l in full_lines if l['date'] < date_from]
            for pl in prev_lines:
                initial_debit += pl['debit']
                initial_credit += pl['credit']
            initial_balance = initial_debit - initial_credit

            statement_lines.append({
                'is_initial_balance': True,
                'name': _('Initial Balance'),
                'journal_code': '',
                'account_code': '',
                'invoice_date': '',
                'due_date': '',
                'matching_number': '',
                'debit': initial_debit,
                'credit': initial_credit,
                'amount_currency': 0.0,
                'currency_symbol': None,
                'balance': initial_balance,
            })

        # Add lines within the date range
        current_balance = initial_balance
        for line in full_lines:
            if in_range(line):
                current_balance += line['debit'] - line['credit']
                line['balance'] = current_balance
                statement_lines.append(line)
                total_debit += line['debit']
                total_credit += line['credit']

        # Calculate totals
        total_balance = current_balance

        # Get available years for filter dropdown
        years = sorted({l['date'].year for l in full_lines if l['date']}, reverse=True)
        if not years:
            years = [date.today().year]

        # Month names for display
        month_names = {
            1: _('January'), 2: _('February'), 3: _('March'), 4: _('April'),
            5: _('May'), 6: _('June'), 7: _('July'), 8: _('August'),
            9: _('September'), 10: _('October'), 11: _('November'), 12: _('December')
        }

        # Quarter names for display
        quarter_names = {
            1: _('Q1 (Jan - Mar)'),
            2: _('Q2 (Apr - Jun)'),
            3: _('Q3 (Jul - Sep)'),
            4: _('Q4 (Oct - Dec)')
        }

        # Get current filter display text
        filter_display = self._get_filter_display_text(filter_type, year, month, quarter, date_from, date_to, month_names)

        return request.render('nexa_portal_customer_statement.customer_statement_page', {
            'statement_lines': statement_lines,
            'partner': partner,
            'total_debit': total_debit,
            'total_credit': total_credit,
            'total_balance': total_balance,
            'currency': company_currency,
            'date_from': date_from,
            'date_to': date_to,
            'page_name': 'customer_statement',
            'filter_type': filter_type or 'year',
            'year': year or date.today().year,
            'month': month or date.today().month,
            'quarter': quarter or ((date.today().month - 1) // 3 + 1),
            'years': years,
            'months': list(range(1, 13)),
            'quarters': [1, 2, 3, 4],
            'month_names': month_names,
            'quarter_names': quarter_names,
            'filter_display': filter_display,
            'today': date.today(),
        })

    def _format_aml_name(self, line_name, line_ref, move_name):
        """Format the display name for an account move line"""
        names = []
        if move_name:
            names.append(move_name)
        if line_ref and line_ref != move_name:
            names.append(line_ref)
        if line_name and line_name not in names:
            names.append(line_name)
        return ' - '.join(filter(None, names)) or move_name or ''

    def _get_filter_display_text(self, filter_type, year, month, quarter, date_from, date_to, month_names):
        """Generate display text for the current filter"""
        if filter_type == 'month' and year and month:
            return f"{month_names.get(month, '')} {year}"
        elif filter_type == 'quarter' and year and quarter:
            quarter_months = {1: 'Jan - Mar', 2: 'Apr - Jun', 3: 'Jul - Sep', 4: 'Oct - Dec'}
            return f"{quarter_months.get(quarter, '')} {year}"
        elif filter_type == 'year' and year:
            return str(year)
        elif filter_type == 'custom' and date_from and date_to:
            return f"{date_from.strftime('%d/%m/%Y')} - {date_to.strftime('%d/%m/%Y')}"
        elif date_from and date_to:
            return f"{date_from.strftime('%d/%m/%Y')} - {date_to.strftime('%d/%m/%Y')}"
        else:
            return str(date.today().year)

    def _compute_date_range(self, filter_type, year, month, quarter, date_from, date_to):
        """Compute date range based on filter type"""
        today = date.today()

        if filter_type == 'year':
            y = year or today.year
            return date(y, 1, 1), date(y, 12, 31)

        elif filter_type == 'month':
            y = year or today.year
            m = month or today.month
            last_day = monthrange(y, m)[1]
            return date(y, m, 1), date(y, m, last_day)

        elif filter_type == 'quarter':
            y = year or today.year
            q = quarter or ((today.month - 1) // 3 + 1)
            start_month = 3 * (q - 1) + 1
            end_month = start_month + 2
            last_day = monthrange(y, end_month)[1]
            return date(y, start_month, 1), date(y, end_month, last_day)

        elif filter_type == 'custom':
            if date_from and isinstance(date_from, str):
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            if date_to and isinstance(date_to, str):
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            return date_from, date_to

        else:
            # Default to current year
            return date(today.year, 1, 1), date(today.year, 12, 31)

    @http.route(['/my/customer_statement/pdf'], type='http', auth="user", website=True)
    def portal_customer_statement_pdf(self, filter_type=None, year=None, month=None, quarter=None,
                                       date_from=None, date_to=None, **kw):
        """Generate PDF for Customer Statement"""
        # Parse filter parameters
        year = int(year) if year and year.isdigit() else None
        month = int(month) if month and month.isdigit() else None
        quarter = int(quarter) if quarter and quarter.isdigit() else None

        # Compute date range based on filter
        date_from, date_to = self._compute_date_range(
            filter_type, year, month, quarter, date_from, date_to
        )

        user = request.env.user
        partner = user.partner_id.commercial_partner_id
        company = request.env.company
        company_currency = company.currency_id

        # Get all partner IDs (including children)
        partner_ids = request.env['res.partner'].sudo().search([
            '|', ('id', '=', partner.id), ('parent_id', '=', partner.id)
        ]).ids

        # Build the query
        query = """
            SELECT
                aml.id,
                aml.date,
                aj.code AS journal_code,
                aml.account_id,
                COALESCE(aml.invoice_date, aml.date) AS invoice_date,
                COALESCE(aml.date_maturity, aml.date) AS due_date,
                aml.matching_number,
                aml.debit,
                aml.credit,
                aml.amount_currency,
                aml.currency_id,
                rc.symbol AS currency_symbol,
                rc.position AS currency_position,
                am.name AS move_name,
                aml.name AS line_name,
                aml.ref AS line_ref
            FROM account_move_line aml
            JOIN account_move am ON am.id = aml.move_id
            JOIN account_account aa ON aa.id = aml.account_id
            LEFT JOIN account_journal aj ON aj.id = aml.journal_id
            LEFT JOIN res_currency rc ON rc.id = aml.currency_id
            WHERE aml.partner_id IN %s
              AND aa.account_type IN ('asset_receivable', 'liability_payable')
              AND am.state = 'posted'
            ORDER BY aml.date ASC, aml.id ASC
        """
        request.env.cr.execute(query, (tuple(partner_ids),))
        all_rows = request.env.cr.fetchall()
        
        # Get account codes using ORM (code_store is company-dependent in Odoo 18)
        account_ids = list(set(row[3] for row in all_rows if row[3]))
        accounts = request.env['account.account'].sudo().browse(account_ids)
        account_code_map = {acc.id: acc.code for acc in accounts}

        # Process all lines
        full_lines = []
        running_balance = 0.0
        today = date.today()

        for row in all_rows:
            (_id, dt, journal_code, account_id, invoice_date, due_date, matching_number,
             debit, credit, amount_currency, currency_id, currency_symbol, currency_position,
             move_name, line_name, line_ref) = row

            balance_change = float(debit or 0) - float(credit or 0)
            running_balance += balance_change
            name = self._format_aml_name(line_name, line_ref, move_name)

            # Format dates for display
            invoice_date_display = invoice_date.strftime('%d/%m/%Y') if invoice_date else ''
            due_date_display = due_date.strftime('%d/%m/%Y') if due_date else ''
            is_overdue = bool(due_date and due_date < today)
            
            # Get account code from map
            account_code = account_code_map.get(account_id, '')

            full_lines.append({
                'id': _id,
                'date': dt,
                'journal_code': journal_code or '',
                'account_code': account_code,
                'invoice_date': invoice_date_display,
                'due_date': due_date_display,
                'is_overdue': is_overdue,
                'matching_number': matching_number or '',
                'debit': float(debit or 0),
                'credit': float(credit or 0),
                'amount_currency': float(amount_currency or 0),
                'currency_id': currency_id,
                'currency_symbol': currency_symbol,
                'currency_position': currency_position,
                'balance': running_balance,
                'name': name,
                'move_name': move_name,
            })

        # Filter by date range
        def in_range(line):
            line_date = line['date']
            if date_from and line_date < date_from:
                return False
            if date_to and line_date > date_to:
                return False
            return True

        # Build statement lines with initial balance
        statement_lines = []
        initial_balance = 0.0
        initial_debit = 0.0
        initial_credit = 0.0
        total_debit = 0.0
        total_credit = 0.0

        if date_from:
            # Calculate initial balance from lines before the date range
            prev_lines = [l for l in full_lines if l['date'] < date_from]
            for pl in prev_lines:
                initial_debit += pl['debit']
                initial_credit += pl['credit']
            initial_balance = initial_debit - initial_credit

            statement_lines.append({
                'is_initial_balance': True,
                'name': _('Initial Balance'),
                'journal_code': '',
                'account_code': '',
                'invoice_date': '',
                'due_date': '',
                'matching_number': '',
                'debit': initial_debit,
                'credit': initial_credit,
                'amount_currency': 0.0,
                'currency_symbol': None,
                'balance': initial_balance,
            })

        current_balance = initial_balance
        for line in full_lines:
            if in_range(line):
                current_balance += line['debit'] - line['credit']
                line['balance'] = current_balance
                statement_lines.append(line)
                total_debit += line['debit']
                total_credit += line['credit']

        total_balance = current_balance

        # Month names for display
        month_names = {
            1: _('January'), 2: _('February'), 3: _('March'), 4: _('April'),
            5: _('May'), 6: _('June'), 7: _('July'), 8: _('August'),
            9: _('September'), 10: _('October'), 11: _('November'), 12: _('December')
        }

        filter_display = self._get_filter_display_text(filter_type, year, month, quarter, date_from, date_to, month_names)

        # Render PDF template
        pdf_content = request.env['ir.actions.report']._render_qweb_pdf(
            'nexa_portal_customer_statement.customer_statement_pdf_report',
            [],
            data={
                'statement_lines': statement_lines,
                'partner': partner,
                'total_debit': total_debit,
                'total_credit': total_credit,
                'total_balance': total_balance,
                'currency': company_currency,
                'date_from': date_from,
                'date_to': date_to,
                'filter_display': filter_display,
                'company': company,
            }
        )[0]

        filename = f"Customer_Statement_{partner.name}_{filter_display.replace(' ', '_')}.pdf"
        
        return request.make_response(
            pdf_content,
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', f'attachment; filename="{filename}"'),
            ]
        )
