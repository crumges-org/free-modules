from odoo import models, fields, api


class FeedbackCategory(models.Model):
    _name = 'feedback.category'
    _description = 'Feedback Category'
    _order = 'sequence, name'

    name = fields.Char(string='Category Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Text(string='Description')
    is_active = fields.Boolean(string='Active', default=True)
    color = fields.Integer(string='Color Index')
    
    # Related fields
    feedback_count = fields.Integer(
        string='Feedback Count',
        compute='_compute_feedback_count',
        store=True
    )
    
    @api.depends('feedback_ids')
    def _compute_feedback_count(self):
        for category in self:
            category.feedback_count = len(category.feedback_ids)
    
    # Relations
    feedback_ids = fields.One2many(
        'advanced.customer.feedback',
        'category_id',
        string='Feedbacks'
    )
