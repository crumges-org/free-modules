from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class AdvancedCustomerFeedbackReport(models.Model):
    _name = 'advanced.customer.feedback.report'
    _description = 'Customer Feedback Report'
    _auto = False

    name = fields.Char(string='Report Name')
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    
    # Statistics
    total_feedbacks = fields.Integer(string='Total Feedbacks')
    average_satisfaction_rating = fields.Float(string='Average Satisfaction Rating')
    resolution_rate = fields.Float(string='Resolution Rate (%)')
    most_common_category = fields.Char(string='Most Common Category')
    
    def init(self):
        """Initialize the report view"""
        # This is a virtual model, so we don't create actual tables
        pass
    
    @api.model
    def generate_report(self, date_from=None, date_to=None, category_id=None):
        """Generate feedback report with specified parameters"""
        domain = []
        
        if date_from:
            domain.append(('create_date', '>=', date_from))
        if date_to:
            domain.append(('create_date', '<=', date_to))
        if category_id:
            domain.append(('category_id', '=', category_id))
        
        feedbacks = self.env['advanced.customer.feedback'].search(domain)
        
        if not feedbacks:
            raise UserError(_('No feedback data found for the specified criteria.'))
        
        # Calculate statistics
        total_feedbacks = len(feedbacks)
        
        # Average satisfaction rating
        ratings = [f.satisfaction_rating for f in feedbacks if f.satisfaction_rating]
        average_rating = sum(ratings) / len(ratings) if ratings else 0.0
        
        # Resolution rate
        resolved_count = len(feedbacks.filtered(lambda f: f.state in ['resolved', 'closed']))
        resolution_rate = (resolved_count / total_feedbacks * 100) if total_feedbacks > 0 else 0.0
        
        # Most common category
        category_counts = {}
        for feedback in feedbacks:
            if feedback.category_id:
                category_name = feedback.category_id.name
                category_counts[category_name] = category_counts.get(category_name, 0) + 1
        
        most_common_category = max(category_counts.items(), key=lambda x: x[1])[0] if category_counts else ''
        
        return {
            'name': f'Feedback Report ({date_from or "All"} - {date_to or "All"})',
            'date_from': date_from,
            'date_to': date_to,
            'total_feedbacks': total_feedbacks,
            'average_satisfaction_rating': average_rating,
            'resolution_rate': resolution_rate,
            'most_common_category': most_common_category,
        }


class FeedbackSummary(models.Model):
    _name = 'feedback.summary'
    _description = 'Feedback Summary'
    _auto = False

    category_id = fields.Many2one('feedback.category', string='Category')
    total_feedbacks = fields.Integer(string='Total Feedbacks')
    average_rating = fields.Float(string='Average Rating')
    resolved_count = fields.Integer(string='Resolved Count')
    pending_count = fields.Integer(string='Pending Count')
    
    def init(self):
        """Initialize the summary view"""
        pass
