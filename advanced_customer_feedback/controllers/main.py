from odoo import http
from odoo.http import request
import json


class CustomerFeedbackController(http.Controller):

    @http.route('/feedback/submit', type='http', auth='public', methods=['POST'], csrf=False)
    def submit_feedback(self, **post):
        """Submit feedback from portal"""
        try:
            # Extract data from form
            title = post.get('title', '')
            description = post.get('description', '')
            category_id = post.get('category_id')
            customer_name = post.get('customer_name', '')
            customer_email = post.get('customer_email', '')
            customer_phone = post.get('customer_phone', '')
            priority = post.get('priority', 'medium')
            feedback_type = post.get('feedback_type', 'general')
            
            # Create feedback record
            feedback_data = {
                'title': title,
                'description': description,
                'category_id': int(category_id) if category_id else False,
                'customer_name': customer_name,
                'customer_email': customer_email,
                'customer_phone': customer_phone,
                'priority': priority,
                'feedback_type': feedback_type,
                'source': 'portal',
            }
            
            feedback = request.env['advanced.customer.feedback'].sudo().create(feedback_data)
            
            return json.dumps({
                'success': True,
                'message': 'Thank you for your feedback! We will review it shortly.',
                'feedback_id': feedback.id
            })
            
        except Exception as e:
            return json.dumps({
                'success': False,
                'message': 'An error occurred while submitting feedback. Please try again.'
            })

    @http.route('/feedback/categories', type='json', auth='public')
    def get_categories(self):
        """Get active feedback categories"""
        categories = request.env['feedback.category'].sudo().search([
            ('active', '=', True)
        ])
        
        return [{
            'id': cat.id,
            'name': cat.name,
            'description': cat.description
        } for cat in categories]

    @http.route('/feedback/templates', type='json', auth='public')
    def get_templates(self, category_id=None):
        """Get feedback templates"""
        domain = [('active', '=', True)]
        if category_id:
            domain.append(('category_id', '=', int(category_id)))
            
        templates = request.env['feedback.template'].sudo().search(domain)
        
        return [{
            'id': template.id,
            'name': template.name,
            'title': template.title,
            'description': template.description,
            'category_id': template.category_id.id,
            'fields': [{
                'name': field.name,
                'field_type': field.field_type,
                'required': field.required,
                'help_text': field.help_text,
                'selection_options': field.selection_options.split('\n') if field.selection_options else []
            } for field in template.fields_ids]
        } for template in templates]

    @http.route('/feedback/dashboard', type='http', auth='user')
    def feedback_dashboard(self):
        """Display feedback dashboard"""
        user = request.env.user
        
        # Get feedback statistics
        total_feedback = request.env['advanced.customer.feedback'].search_count([])
        pending_feedback = request.env['advanced.customer.feedback'].search_count([
            ('state', '=', 'new')
        ])
        resolved_feedback = request.env['advanced.customer.feedback'].search_count([
            ('state', '=', 'resolved')
        ])
        
        # Get recent feedback
        recent_feedback = request.env['advanced.customer.feedback'].search([
            ('state', '!=', 'cancelled')
        ], limit=10, order='create_date desc')
        
        return request.render('advanced_customer_feedback.feedback_dashboard_template', {
            'total_feedback': total_feedback,
            'pending_feedback': pending_feedback,
            'resolved_feedback': resolved_feedback,
            'recent_feedback': recent_feedback,
            'user': user
        })

    @http.route('/feedback/portal', type='http', auth='public')
    def feedback_portal(self):
        """Public feedback submission portal"""
        categories = request.env['feedback.category'].sudo().search([
            ('active', '=', True)
        ])
        
        templates = request.env['feedback.template'].sudo().search([
            ('active', '=', True)
        ])
        
        return request.render('advanced_customer_feedback.feedback_portal_template', {
            'categories': categories,
            'templates': templates
        })
