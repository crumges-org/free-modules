# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class WooCommerceProductTag(models.Model):
    """WooCommerce Product Tag Management"""
    _name = 'woocommerce.product.tag'
    _description = 'WooCommerce Product Tag'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(string='Tag Name', required=True, tracking=True)
    description = fields.Text(string='Description', tracking=True)
    slug = fields.Char(string='Slug', tracking=True, help="URL-friendly version of the tag name")
    active = fields.Boolean(string='Active', default=True, tracking=True)
    
    # Configuration Reference
    configuration_id = fields.Many2one(
        'woocommerce.configuration',
        string='WooCommerce Configuration',
        required=True,
        ondelete='cascade'
    )
    
    # WooCommerce Integration
    woocommerce_tag_id = fields.Char(string='WooCommerce Tag ID', help="ID in WooCommerce")
    exported_in_woocommerce = fields.Boolean(string='Exported in WooCommerce', default=False, tracking=True)
    last_sync_date = fields.Datetime(string='Last Sync Date', tracking=True)
    sync_status = fields.Selection([
        ('pending', 'Pending'),
        ('synced', 'Synced'),
        ('failed', 'Failed'),
        ('updated', 'Updated')
    ], string='Sync Status', default='pending', tracking=True)
    
    # Statistics
    count = fields.Integer(string='Product Count', default=0, tracking=True,
                          help="Number of products with this tag")
    
    # Product Relations
    product_ids = fields.Many2many('product.template', string='Products',
                                  help="Products that have this tag")
    
    # Company
    company_id = fields.Many2one('res.company', string='Company',
                                default=lambda self: self.env.company, required=True)
    
    # Constraints
    _sql_constraints = [
        ('name_unique', 'unique(name, configuration_id)', 'Tag name must be unique per configuration!')
    ]

    def action_export_to_woocommerce(self):
        """Export tag to WooCommerce"""
        self.ensure_one()
        try:
            # Prepare tag data for WooCommerce
            tag_data = {
                'name': self.name,
                'description': self.description or '',
                'slug': self.slug or self.name.lower().replace(' ', '-')
            }
            
            # Export via sync service
            sync_service = self.env['woocommerce.sync.service']
            result = sync_service.export_tag(self.configuration_id, tag_data)
            
            if result:
                self.write({
                    'exported_in_woocommerce': True,
                    'last_sync_date': fields.Datetime.now(),
                    'sync_status': 'synced',
                    'woocommerce_tag_id': result.get('id')
                })
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Tag exported to WooCommerce successfully'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
        except Exception as e:
            self.write({'sync_status': 'failed'})
            raise UserError(_('Failed to export tag: %s') % str(e))

    def action_import_from_woocommerce(self):
        """Import tag from WooCommerce"""
        self.ensure_one()
        try:
            # Import via sync service
            sync_service = self.env['woocommerce.sync.service']
            result = sync_service.import_tag(self.configuration_id, self.woocommerce_tag_id)
            
            if result:
                self._update_from_woocommerce_data(result)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Tag imported from WooCommerce successfully'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
        except Exception as e:
            raise UserError(_('Failed to import tag: %s') % str(e))

    def action_sync_all_tags(self):
        """Sync all tags for a configuration"""
        self.ensure_one()
        try:
            sync_service = self.env['woocommerce.sync.service']
            sync_service.sync_tags(self.configuration_id)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('All tags synchronized successfully'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(_('Failed to sync tags: %s') % str(e))

    def _update_from_woocommerce_data(self, woo_data):
        """Update tag from WooCommerce data"""
        self.write({
            'name': woo_data.get('name', self.name),
            'description': woo_data.get('description', ''),
            'slug': woo_data.get('slug', ''),
            'count': woo_data.get('count', 0),
            'last_sync_date': fields.Datetime.now(),
            'sync_status': 'synced'
        })

    def action_view_products(self):
        """View products with this tag"""
        return {
            'name': _('Products with Tag: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.product_ids.ids)],
        }

    def name_get(self):
        """Custom name display"""
        result = []
        for record in self:
            name = record.name
            if record.count > 0:
                name += f" ({record.count} products)"
            if not record.active:
                name += " [Inactive]"
            result.append((record.id, name))
        return result
