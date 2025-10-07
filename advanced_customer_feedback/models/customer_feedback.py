from odoo import models, fields, api, _, tools
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta



class CustomerFeedback(models.Model):
    _name = 'advanced.customer.feedback'
    _description = 'Advanced Customer Feedback'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char('Feedback Number', required=True, copy=False, readonly=True, 
                      default=lambda self: _('New'))
    title = fields.Char('Title', required=True)
    description = fields.Text('Description', required=True)
    
    customer_id = fields.Many2one(
        'res.partner', 
        string='Customer',
        required=False
    )
    customer_email = fields.Char('Customer Email', compute='_compute_customer_info', store=True)
    customer_phone = fields.Char('Customer Phone', compute='_compute_customer_info', store=True)
    
    category_id = fields.Many2one(
        'feedback.category',
        string='Category',
        required=False
    )
    
    template_id = fields.Many2one(
        'feedback.template',
        string='Template'
    )
    
    feedback_type = fields.Selection([
        ('suggestion', 'Suggestion'),
        ('complaint', 'Complaint'),
        ('compliment', 'Compliment'),
        ('bug_report', 'Bug Report'),
        ('feature_request', 'Feature Request'),
        ('general', 'General'),
    ], string='Feedback Type', required=True, default='general')
    
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Medium'),
        ('2', 'High'),
        ('3', 'Critical'),
    ], string='Priority', default='1', tracking=True)
    
    state = fields.Selection([
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
        ('rejected', 'Rejected'),
    ], string='Status', default='new', tracking=True)
    
    assigned_to_id = fields.Many2one(
        'res.users',
        string='Assigned To'
    )
    
    # Related records
    product_id = fields.Many2one('product.product', string='Related Product')
    sale_order_id = fields.Many2one('sale.order', string='Related Sale Order')
    project_id = fields.Many2one('project.project', string='Related Project')
    
    # Customer satisfaction
    satisfaction_rating = fields.Selection([
        ('1', 'Very Dissatisfied'),
        ('2', 'Dissatisfied'),
        ('3', 'Neutral'),
        ('4', 'Satisfied'),
        ('5', 'Very Satisfied'),
    ], string='Satisfaction Rating')
    
    # Additional fields
    source = fields.Selection([
        ('portal', 'Customer Portal'),
        ('website', 'Website Form'),
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('social_media', 'Social Media'),
        ('other', 'Other'),
    ], string='Source', default='portal')
    
    tags = fields.Many2many('feedback.tag', string='Tags')
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    
    # Internal notes
    internal_notes = fields.Text('Internal Notes')
    resolution_notes = fields.Text('Resolution Notes')
    
    # Dates
    create_date = fields.Datetime('Created Date', readonly=True)
    write_date = fields.Datetime('Last Updated', readonly=True)
    resolved_date = fields.Datetime('Resolved Date')
    closed_date = fields.Datetime('Closed Date')
    
    # Computed fields
    days_open = fields.Integer('Days Open', compute='_compute_days_open')
    is_overdue = fields.Boolean('Is Overdue', compute='_compute_is_overdue')
    
    @api.model
    def create(self, vals):
        # First, try to clean up any corrupted data before creating
        try:
            self.env.cr.execute("""
                UPDATE advanced_customer_feedback 
                SET customer_id = NULL 
                WHERE customer_id IS NOT NULL 
                AND customer_id NOT IN (SELECT id FROM res_partner WHERE id = customer_id)
            """)
            self.env.cr.execute("""
                UPDATE advanced_customer_feedback 
                SET category_id = NULL 
                WHERE category_id IS NOT NULL 
                AND category_id NOT IN (SELECT id FROM feedback_category WHERE id = category_id)
            """)
            self.env.cr.execute("""
                UPDATE advanced_customer_feedback 
                SET assigned_to_id = NULL 
                WHERE assigned_to_id IS NOT NULL 
                AND assigned_to_id NOT IN (SELECT id FROM res_users WHERE id = assigned_to_id)
            """)
            self.env.cr.commit()
        except:
            pass
        
        # Generate sequence number
        if vals.get('name', _('New')) == _('New'):
            try:
                vals['name'] = self.env['ir.sequence'].next_by_code('advanced.customer.feedback') or _('New')
            except:
                # Fallback if sequence doesn't exist
                vals['name'] = _('New')
        
        # Ensure category_id is valid
        if vals.get('category_id'):
            try:
                category = self.env['feedback.category'].browse(vals['category_id'])
                if not category.exists():
                    vals['category_id'] = False
            except:
                vals['category_id'] = False
        
        # Ensure customer_id is valid
        if vals.get('customer_id'):
            try:
                customer = self.env['res.partner'].browse(vals['customer_id'])
                if not customer.exists():
                    vals['customer_id'] = False
            except:
                vals['customer_id'] = False
        
        return super().create(vals)
    
    @api.depends('customer_id')
    def _compute_customer_info(self):
        for feedback in self:
            try:
                if feedback.customer_id and feedback.customer_id.exists():
                    feedback.customer_email = feedback.customer_id.email
                    feedback.customer_phone = feedback.customer_id.phone
                else:
                    feedback.customer_email = False
                    feedback.customer_phone = False
            except Exception:
                # Handle any issues with customer_id reference
                feedback.customer_email = False
                feedback.customer_phone = False
    
    @api.depends('create_date', 'state')
    def _compute_days_open(self):
        for feedback in self:
            if feedback.create_date and feedback.state not in ['resolved', 'closed']:
                delta = fields.Datetime.now() - feedback.create_date
                feedback.days_open = delta.days
            else:
                feedback.days_open = 0
    
    @api.depends('days_open', 'priority')
    def _compute_is_overdue(self):
        for feedback in self:
            if feedback.state in ['new', 'in_progress']:
                if feedback.priority == '3' and feedback.days_open > 1:  # Critical
                    feedback.is_overdue = True
                elif feedback.priority == '2' and feedback.days_open > 3:  # High
                    feedback.is_overdue = True
                elif feedback.priority == '1' and feedback.days_open > 7:  # Medium
                    feedback.is_overdue = True
                elif feedback.priority == '0' and feedback.days_open > 14:  # Low
                    feedback.is_overdue = True
                else:
                    feedback.is_overdue = False
            else:
                feedback.is_overdue = False
    
    def action_assign_to_me(self):
        """Assign feedback to current user"""
        self.ensure_one()
        self.assigned_to_id = self.env.user
        self.state = 'in_progress'
    
    def action_start_progress(self):
        """Start working on feedback"""
        self.ensure_one()
        if not self.assigned_to_id:
            self.assigned_to_id = self.env.user
        self.state = 'in_progress'
    
    def action_resolve(self):
        """Mark feedback as resolved"""
        self.ensure_one()
        self.state = 'resolved'
        self.resolved_date = fields.Datetime.now()
    
    def action_close(self):
        """Close feedback"""
        self.ensure_one()
        self.state = 'closed'
        self.closed_date = fields.Datetime.now()
    
    def action_reject(self):
        """Reject feedback"""
        self.ensure_one()
        self.state = 'rejected'
    
    def action_reopen(self):
        """Reopen feedback"""
        self.ensure_one()
        self.state = 'in_progress'
        self.resolved_date = False
        self.closed_date = False
    
    def write(self, vals):
        """Override write to ensure data integrity"""
        # Ensure category_id is valid
        if vals.get('category_id'):
            try:
                category = self.env['feedback.category'].browse(vals['category_id'])
                if not category.exists():
                    vals['category_id'] = False
            except:
                vals['category_id'] = False
        
        # Ensure customer_id is valid
        if vals.get('customer_id'):
            try:
                customer = self.env['res.partner'].browse(vals['customer_id'])
                if not customer.exists():
                    vals['customer_id'] = False
            except:
                vals['customer_id'] = False
        
        return super().write(vals)
    

    

    
    def _send_customer_notification(self, template_ref):
        """Send notification to customer"""
        template = self.env.ref(template_ref)
        if template and self.customer_id.email:
            template.send_mail(self.id, force_send=True)
    
    @api.model
    def cleanup_corrupted_data(self):
        """Manual method to clean up corrupted data"""
        try:
            # Clean up corrupted foreign key references
            self.env.cr.execute("""
                UPDATE advanced_customer_feedback 
                SET customer_id = NULL 
                WHERE customer_id IS NOT NULL 
                AND customer_id NOT IN (SELECT id FROM res_partner WHERE id = customer_id)
            """)
            self.env.cr.execute("""
                UPDATE advanced_customer_feedback 
                SET category_id = NULL 
                WHERE category_id IS NOT NULL 
                AND category_id NOT IN (SELECT id FROM feedback_category WHERE id = category_id)
            """)
            self.env.cr.execute("""
                UPDATE advanced_customer_feedback 
                SET assigned_to_id = NULL 
                WHERE assigned_to_id IS NOT NULL 
                AND assigned_to_id NOT IN (SELECT id FROM res_users WHERE id = assigned_to_id)
            """)
            self.env.cr.commit()
            return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {
                'title': 'Success',
                'message': 'Corrupted data has been cleaned up successfully.',
                'type': 'success',
            }}
        except Exception as e:
            return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {
                'title': 'Error',
                'message': f'Error during cleanup: {str(e)}',
                'type': 'danger',
            }}
    



class FeedbackTag(models.Model):
    _name = 'feedback.tag'
    _description = 'Feedback Tag'
    _order = 'name'

    name = fields.Char('Tag Name', required=True)
    color = fields.Integer('Color Index')
    description = fields.Text('Description')
    
    feedback_count = fields.Integer('Feedback Count', compute='_compute_feedback_count')
    
    @api.depends('name')
    def _compute_feedback_count(self):
        for tag in self:
            tag.feedback_count = self.env['advanced.customer.feedback'].search_count([
                ('tags', 'in', tag.id)
            ])



class FeedbackReport(models.Model):
    _name = 'advanced.customer.feedback.report'
    _description = 'Advanced Customer Feedback Report'
    _auto = False
    
    feedback_id = fields.Many2one('advanced.customer.feedback', string='Feedback')
    customer_id = fields.Many2one('res.partner', string='Customer')
    category_id = fields.Many2one('feedback.category', string='Category')
    feedback_type = fields.Selection([
        ('suggestion', 'Suggestion'),
        ('complaint', 'Complaint'),
        ('compliment', 'Compliment'),
        ('bug_report', 'Bug Report'),
        ('feature_request', 'Feature Request'),
        ('general', 'General'),
    ], string='Feedback Type')
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Medium'),
        ('2', 'High'),
        ('3', 'Critical'),
    ], string='Priority')
    state = fields.Selection([
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
        ('rejected', 'Rejected'),
    ], string='Status')
    satisfaction_rating = fields.Selection([
        ('1', 'Very Dissatisfied'),
        ('2', 'Dissatisfied'),
        ('3', 'Neutral'),
        ('4', 'Satisfied'),
        ('5', 'Very Satisfied'),
    ], string='Satisfaction Rating')
    source = fields.Selection([
        ('portal', 'Customer Portal'),
        ('website', 'Website Form'),
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('social_media', 'Social Media'),
        ('other', 'Other'),
    ], string='Source')
    create_date = fields.Datetime('Created Date')
    resolved_date = fields.Datetime('Resolved Date')
    days_open = fields.Integer('Days Open')
    
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE or REPLACE VIEW %s as (
                SELECT 
                    row_number() OVER () as id,
                    cf.id as feedback_id,
                    cf.customer_id,
                    cf.category_id,
                    cf.feedback_type,
                    cf.priority,
                    cf.state,
                    cf.satisfaction_rating,
                    cf.source,
                    cf.create_date,
                    cf.resolved_date,
                    CASE 
                        WHEN cf.create_date IS NOT NULL AND cf.state NOT IN ('resolved', 'closed') 
                        THEN EXTRACT(DAY FROM (NOW() - cf.create_date))
                        ELSE 0
                    END as days_open
                FROM advanced_customer_feedback cf
            )
        """ % self._table)
