from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class DynamicFormFieldOptionsWizard(models.TransientModel):
    _name = 'dynamic.form.field.options.wizard'
    _description = 'Dynamic Form Field Options Wizard'

    form_id = fields.Many2one('dynamic.form', 'Form', required=True)
    field_ids = fields.Many2many('dynamic.form.field', string='Fields Needing Options')
    
    # Dynamic fields for each field that needs options
    field_options_data = fields.Text('Field Options Data', default='{}')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('default_form_id'):
            form_id = self.env.context.get('default_form_id')
            form = self.env['dynamic.form'].browse(form_id)
            
            # Get fields that need options
            fields_needing_options = form.field_ids.filtered(
                lambda f: f.field_type in ['select', 'radio', 'checkbox'] and not f.options
            )
            
            res.update({
                'form_id': form_id,
                'field_ids': [(6, 0, fields_needing_options.ids)],
            })
        return res

    def action_save_options(self):
        """Save options for all fields"""
        import json
        
        try:
            options_data = json.loads(self.field_options_data or '{}')
            
            for field_id, options in options_data.items():
                field = self.env['dynamic.form.field'].browse(int(field_id))
                if field.exists():
                    field.write({
                        'options': options.get('options', ''),
                        'help_text': options.get('help_text', ''),
                    })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': 'Field options have been saved successfully!',
                    'type': 'success',
                }
            }
            
        except Exception as e:
            raise ValidationError(_('Error saving options: %s') % str(e))

    def action_cancel(self):
        """Cancel the wizard"""
        return {'type': 'ir.actions.act_window_close'}


class DynamicFormFieldOptionsWizardLine(models.TransientModel):
    _name = 'dynamic.form.field.options.wizard.line'
    _description = 'Dynamic Form Field Options Wizard Line'

    wizard_id = fields.Many2one('dynamic.form.field.options.wizard', 'Wizard')
    field_id = fields.Many2one('dynamic.form.field', 'Field', required=True)
    field_label = fields.Char(related='field_id.label', readonly=True)
    field_type = fields.Selection(related='field_id.field_type', readonly=True)
    options = fields.Text('Options (one per line)', 
                         help='Enter each option on a separate line')
    help_text = fields.Text('Help Text', 
                           help='Optional help text for this field')

    @api.model_create_multi
    def create(self, vals_list):
        """Set default options from field if available"""
        for vals in vals_list:
            if 'field_id' in vals and not vals.get('options'):
                field = self.env['dynamic.form.field'].browse(vals['field_id'])
                if field.exists():
                    if field.options:
                        vals['options'] = field.options
                    if field.help_text:
                        vals['help_text'] = field.help_text
        return super().create(vals_list)
