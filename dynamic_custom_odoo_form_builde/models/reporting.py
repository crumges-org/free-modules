from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import json
import base64
from io import BytesIO, StringIO
import csv
import logging

_logger = logging.getLogger(__name__)


class DynamicFormsAnalytics(models.TransientModel):
    _name = 'dynamic.forms.analytics'
    _description = 'Dynamic Forms Analytics Dashboard'

    @api.model
    def get_analytics_data(self, form_ids=None, date_from=None, date_to=None):
        """Get comprehensive analytics data for forms"""
        domain = []
        
        if form_ids:
            domain.append(('id', 'in', form_ids))
        
        forms = self.env['dynamic.form'].search(domain)
        
        # Date range filtering
        submission_domain = []
        if date_from:
            submission_domain.append(('create_date', '>=', date_from))
        if date_to:
            submission_domain.append(('create_date', '<=', date_to))
        
        # Overall Statistics
        total_forms = len(forms)
        total_submissions = self.env['dynamic.form.submission'].search_count(submission_domain)
        total_views = sum(forms.mapped('view_count'))
        avg_conversion_rate = sum(forms.mapped('conversion_rate')) / total_forms if total_forms > 0 else 0
        
        # Form-level statistics
        form_stats = []
        for form in forms:
            form_submissions = form.submission_ids.filtered(
                lambda s: (not date_from or s.create_date >= date_from) and 
                         (not date_to or s.create_date <= date_to)
            )
            
            form_stats.append({
                'id': form.id,
                'name': form.name,
                'view_count': form.view_count,
                'submission_count': len(form_submissions),
                'conversion_rate': form.conversion_rate,
                'status': form.status,
                'is_published': form.is_published,
                'last_submission_date': form.last_submission_date and form.last_submission_date.strftime('%Y-%m-%d %H:%M:%S') or '',
                'active_field_count': form.active_field_count,
                'target_model': form.target_model_id.name or '',
            })
        
        # Time-based statistics (last 30 days by default)
        time_stats = []
        if not date_from:
            date_from = datetime.now() - timedelta(days=30)
        if not date_to:
            date_to = datetime.now()
        
        current_date = date_from
        while current_date <= date_to:
            day_start = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            day_submissions = self.env['dynamic.form.submission'].search_count([
                ('create_date', '>=', day_start),
                ('create_date', '<', day_end)
            ] + submission_domain)
            
            time_stats.append({
                'date': day_start.strftime('%Y-%m-%d'),
                'submissions': day_submissions,
            })
            
            current_date += timedelta(days=1)
        
        # Status breakdown
        status_breakdown = {
            'draft': len(forms.filtered(lambda f: f.status == 'draft')),
            'ready': len(forms.filtered(lambda f: f.status == 'ready')),
            'published': len(forms.filtered(lambda f: f.status == 'published')),
        }
        
        # Submission state breakdown
        submission_state_breakdown = {}
        states = ['draft', 'submitted', 'processed', 'error']
        for state in states:
            submission_state_breakdown[state] = self.env['dynamic.form.submission'].search_count(
                [('state', '=', state)] + submission_domain
            )
        
        return {
            'overall': {
                'total_forms': total_forms,
                'total_submissions': total_submissions,
                'total_views': total_views,
                'avg_conversion_rate': round(avg_conversion_rate, 2),
            },
            'form_stats': form_stats,
            'time_stats': time_stats,
            'status_breakdown': status_breakdown,
            'submission_state_breakdown': submission_state_breakdown,
        }


class DynamicFormsReporting(models.TransientModel):
    _name = 'dynamic.forms.reporting'
    _description = 'Dynamic Forms Reporting'

    def export_submissions_to_csv(self, submission_ids):
        """Export submissions to CSV format"""
        if not submission_ids:
            raise UserError(_('No submissions selected for export.'))
        
        submissions = self.env['dynamic.form.submission'].browse(submission_ids)
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Submission ID',
            'Form Name',
            'Status',
            'Created Date',
            'IP Address',
            'User Agent',
            'Referrer',
            'Target Model',
            'Target Record ID',
            'Form Data (JSON)',
        ])
        
        # Write data rows
        for submission in submissions:
            try:
                form_data_json = submission.formatted_json_data or submission.form_data or '{}'
            except:
                form_data_json = '{}'
            
            writer.writerow([
                submission.name or '',
                submission.form_name or '',
                submission.state or '',
                submission.create_date and submission.create_date.strftime('%Y-%m-%d %H:%M:%S') or '',
                submission.ip_address or '',
                submission.user_agent or '',
                submission.referrer or '',
                submission.target_model or '',
                submission.target_record_id or '',
                form_data_json,
            ])
        
        output.seek(0)
        csv_data = output.read()
        output.close()
        
        # Encode CSV data to bytes for Python 3
        csv_data_bytes = csv_data.encode('utf-8')
        
        # Create attachment
        filename = 'dynamic_forms_submissions_export_%s.csv' % datetime.now().strftime('%Y%m%d_%H%M%S')
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(csv_data_bytes),
            'res_model': 'dynamic.form.submission',
            'res_id': False,
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }
    
    def export_analytics_to_csv(self, analytics_data):
        """Export analytics data to CSV format"""
        output = StringIO()
        writer = csv.writer(output)
        
        # Overall statistics
        writer.writerow(['Overall Statistics'])
        writer.writerow(['Metric', 'Value'])
        writer.writerow(['Total Forms', analytics_data['overall']['total_forms']])
        writer.writerow(['Total Submissions', analytics_data['overall']['total_submissions']])
        writer.writerow(['Total Views', analytics_data['overall']['total_views']])
        writer.writerow(['Average Conversion Rate (%)', analytics_data['overall']['avg_conversion_rate']])
        writer.writerow([])
        
        # Form statistics
        writer.writerow(['Form Statistics'])
        writer.writerow([
            'Form Name',
            'Views',
            'Submissions',
            'Conversion Rate (%)',
            'Status',
            'Published',
            'Last Submission',
            'Fields',
            'Target Model',
        ])
        
        for form_stat in analytics_data['form_stats']:
            writer.writerow([
                form_stat['name'],
                form_stat['view_count'],
                form_stat['submission_count'],
                form_stat['conversion_rate'],
                form_stat['status'],
                'Yes' if form_stat['is_published'] else 'No',
                form_stat['last_submission_date'],
                form_stat['active_field_count'],
                form_stat['target_model'],
            ])
        
        writer.writerow([])
        
        # Time-based statistics
        writer.writerow(['Time-based Statistics'])
        writer.writerow(['Date', 'Submissions'])
        for time_stat in analytics_data['time_stats']:
            writer.writerow([
                time_stat['date'],
                time_stat['submissions'],
            ])
        
        output.seek(0)
        csv_data = output.read()
        output.close()
        
        # Encode CSV data to bytes for Python 3
        csv_data_bytes = csv_data.encode('utf-8')
        
        # Create attachment
        filename = 'dynamic_forms_analytics_export_%s.csv' % datetime.now().strftime('%Y%m%d_%H%M%S')
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(csv_data_bytes),
            'res_model': 'dynamic.forms.analytics',
            'res_id': False,
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }

