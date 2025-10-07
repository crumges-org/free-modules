from odoo import models, fields, api


class FeedbackTemplate(models.Model):
    _name = 'feedback.template'
    _description = 'Feedback Template'
    _order = 'name'

    name = fields.Char(string='Template Name', required=True)
    category_id = fields.Many2one(
        'feedback.category',
        string='Category',
        required=True
    )
    title = fields.Char(string='Title', required=True)
    description = fields.Text(string='Description')
    is_active = fields.Boolean(string='Active', default=True)
    
    # Template fields
    fields_ids = fields.One2many(
        'feedback.template.field',
        'template_id',
        string='Template Fields'
    )
    
    # Usage tracking
    usage_count = fields.Integer(
        string='Usage Count',
        compute='_compute_usage_count',
        store=True
    )
    
    @api.depends('feedback_ids')
    def _compute_usage_count(self):
        for template in self:
            template.usage_count = len(template.feedback_ids)
    
    # Relations
    feedback_ids = fields.One2many(
        'advanced.customer.feedback',
        'template_id',
        string='Feedbacks'
    )



