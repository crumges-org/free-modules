from odoo import models, fields, api, _


class FeedbackTag(models.Model):
    _name = 'feedback.tag'
    _description = 'Feedback Tag'
    _order = 'sequence, name'

    name = fields.Char(string='Tag Name', required=True, translate=True)
    color = fields.Integer(string='Color Index', default=0)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    description = fields.Text(string='Description')
    
    # Statistics
    feedback_count = fields.Integer(string='Feedback Count', compute='_compute_feedback_count')
    
    @api.depends('name')
    def _compute_feedback_count(self):
        for tag in self:
            tag.feedback_count = self.env['advanced.customer.feedback'].search_count([
                ('tags', 'in', tag.id)
            ])
    
    @api.model
    def create(self, vals):
        # Ensure unique tag names
        if vals.get('name'):
            existing_tag = self.search([('name', '=', vals['name'])], limit=1)
            if existing_tag:
                return existing_tag
        return super().create(vals)
    
    def name_get(self):
        result = []
        for tag in self:
            name = tag.name
            if tag.feedback_count > 0:
                name += f' ({tag.feedback_count})'
            result.append((tag.id, name))
        return result
