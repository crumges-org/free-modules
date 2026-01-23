"""
Post-installation hooks for dynamic_forms module
"""
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """
    Post-installation hook to update demo forms with correct target models
    This runs after the module is installed/upgraded
    """
    try:
        
        # Mapping of form XML IDs to their target models
        form_model_mapping = {
            'demo_crm_lead_form': 'crm.lead',
            'demo_project_task_form': 'project.task',
            'demo_sale_order_form': 'sale.order',
            'demo_product_inquiry_form': 'product.template',
            'demo_product_review_form': 'product.template',
        }
        
        # Get ir.model.data to find form records
        IrModelData = env['ir.model.data']
        IrModel = env['ir.model']
        DynamicForm = env['dynamic.form']
        
        for form_xmlid, model_name in form_model_mapping.items():
            try:
                # Find the form by XML ID
                form_data = IrModelData.search([
                    ('module', '=', 'dynamic_custom_odoo_form_builde'),
                    ('name', '=', form_xmlid),
                    ('model', '=', 'dynamic.form')
                ], limit=1)
                
                if form_data and form_data.res_id:
                    form = DynamicForm.browse(form_data.res_id)
                    if form.exists():
                        # Check if the target model exists
                        target_model = IrModel.search([
                            ('model', '=', model_name)
                        ], limit=1)
                        
                        if target_model:
                            # Update the form's target model
                            form.target_model_id = target_model
                            _logger.info('Updated %s to use model %s', form.name, model_name)
                        else:
                            _logger.info('Model %s not found, keeping default for %s', model_name, form.name)
            except Exception as e:
                _logger.warning('Error updating form %s: %s', form_xmlid, str(e))
                
    except Exception as e:
        _logger.warning('Error in post_init_hook for dynamic_custom_odoo_form_builde: %s', str(e))

