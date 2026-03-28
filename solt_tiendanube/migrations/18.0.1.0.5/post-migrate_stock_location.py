import logging
from odoo.api import SUPERUSER_ID, Environment
_logger = logging.Logger(__name__)


def migrate(cr, version):
    """Recreate essential locations per company after module update."""

    if not version:
        return
    env = Environment(cr, SUPERUSER_ID, {})
    target_company_id = 2

    # Fields to clean in ir.default
    field_model = env['ir.model.fields']
    ir_default = env['ir.default'].sudo()

    field_inventory = field_model._get('product.template', 'property_stock_inventory')
    field_production = field_model._get('product.template', 'property_stock_production')

    for field in [field_inventory, field_production]:
        defaults = ir_default.search([
            ('field_id', '=', field.id),
            ('company_id', '=', target_company_id)
        ])
        for default in defaults:
            print(f"Removing ir.default for field_id={field.id} and company_id={target_company_id}")
            default.unlink()

    for company in env['res.company'].search([('id', '=', 2), ('email', '=', 'tienda@online.com')]):
        company.create_missing_transit_location()
        # company.create_missing_warehouse()
        company.create_missing_inventory_loss_location()
        company.create_missing_production_location()
        company.create_missing_scrap_location()
        company.create_missing_scrap_sequence()