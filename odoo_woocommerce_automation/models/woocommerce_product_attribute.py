# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class WooCommerceProductAttribute(models.Model):
    """WooCommerce Product Attribute Management"""
    _name = 'woocommerce.product.attribute'
    _description = 'WooCommerce Product Attribute'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(string='Attribute Name', required=True, tracking=True)
    slug = fields.Char(string='Slug', tracking=True, help="URL-friendly version of the attribute name")
    description = fields.Text(string='Description', tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)
    
    # Configuration Reference
    configuration_id = fields.Many2one(
        'woocommerce.configuration',
        string='WooCommerce Configuration',
        required=True,
        ondelete='cascade'
    )
    
    # WooCommerce Integration
    woocommerce_attribute_id = fields.Char(string='WooCommerce Attribute ID', help="ID in WooCommerce")
    exported_in_woocommerce = fields.Boolean(string='Exported in WooCommerce', default=False, tracking=True)
    last_sync_date = fields.Datetime(string='Last Sync Date', tracking=True)
    sync_status = fields.Selection([
        ('pending', 'Pending'),
        ('synced', 'Synced'),
        ('failed', 'Failed'),
        ('updated', 'Updated')
    ], string='Sync Status', default='pending', tracking=True)
    
    # Attribute Properties
    order_by = fields.Selection([
        ('menu_order', 'Menu Order'),
        ('name', 'Name'),
        ('name_num', 'Name (Numeric)'),
        ('id', 'ID')
    ], string='Order By', default='menu_order', tracking=True)
    
    has_archives = fields.Boolean(string='Has Archives', default=True, tracking=True,
                                 help="Enable/disable the attribute archives page")
    
    # Statistics
    count = fields.Integer(string='Term Count', default=0, tracking=True,
                          help="Number of terms for this attribute")
    
    # Terms
    attribute_term_ids = fields.One2many('woocommerce.product.attribute.term', 'attribute_id', string='Attribute Terms')
    
    # Company
    company_id = fields.Many2one('res.company', string='Company',
                                default=lambda self: self.env.company, required=True)
    
    # Constraints
    _sql_constraints = [
        ('name_unique', 'unique(name, configuration_id)', 'Attribute name must be unique per configuration!')
    ]

    def action_export_to_woocommerce(self):
        """Export attribute to WooCommerce"""
        self.ensure_one()
        try:
            # Prepare attribute data for WooCommerce
            attribute_data = {
                'name': self.name,
                'slug': self.slug or self.name.lower().replace(' ', '-'),
                'description': self.description or '',
                'order_by': self.order_by,
                'has_archives': self.has_archives
            }
            
            # Export via sync service
            sync_service = self.env['woocommerce.sync.service']
            result = sync_service.export_attribute(self.configuration_id, attribute_data)
            
            if result:
                self.write({
                    'exported_in_woocommerce': True,
                    'last_sync_date': fields.Datetime.now(),
                    'sync_status': 'synced',
                    'woocommerce_attribute_id': result.get('id')
                })
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Attribute exported to WooCommerce successfully'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
        except Exception as e:
            self.write({'sync_status': 'failed'})
            raise UserError(_('Failed to export attribute: %s') % str(e))

    def action_import_from_woocommerce(self):
        """Import attribute from WooCommerce"""
        self.ensure_one()
        try:
            # Import via sync service
            sync_service = self.env['woocommerce.sync.service']
            result = sync_service.import_attribute(self.configuration_id, self.woocommerce_attribute_id)
            
            if result:
                self._update_from_woocommerce_data(result)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Attribute imported from WooCommerce successfully'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
        except Exception as e:
            raise UserError(_('Failed to import attribute: %s') % str(e))

    def action_sync_all_attributes(self):
        """Sync all attributes for a configuration"""
        self.ensure_one()
        try:
            sync_service = self.env['woocommerce.sync.service']
            sync_service.sync_attributes(self.configuration_id)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('All attributes synchronized successfully'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(_('Failed to sync attributes: %s') % str(e))

    def _update_from_woocommerce_data(self, woo_data):
        """Update attribute from WooCommerce data"""
        self.write({
            'name': woo_data.get('name', self.name),
            'slug': woo_data.get('slug', ''),
            'description': woo_data.get('description', ''),
            'order_by': woo_data.get('order_by', 'menu_order'),
            'has_archives': woo_data.get('has_archives', True),
            'count': woo_data.get('count', 0),
            'last_sync_date': fields.Datetime.now(),
            'sync_status': 'synced'
        })

    def action_view_terms(self):
        """View attribute terms"""
        return {
            'name': _('Attribute Terms: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'woocommerce.product.attribute.term',
            'view_mode': 'list,form',
            'domain': [('attribute_id', '=', self.id)],
            'context': {'default_attribute_id': self.id},
        }

    def name_get(self):
        """Custom name display"""
        result = []
        for record in self:
            name = record.name
            if record.count > 0:
                name += f" ({record.count} terms)"
            if not record.active:
                name += " [Inactive]"
            result.append((record.id, name))
        return result


class WooCommerceProductAttributeTerm(models.Model):
    """WooCommerce Product Attribute Term"""
    _name = 'woocommerce.product.attribute.term'
    _description = 'WooCommerce Product Attribute Term'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(string='Term Name', required=True, tracking=True)
    slug = fields.Char(string='Slug', tracking=True, help="URL-friendly version of the term name")
    description = fields.Text(string='Description', tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)
    
    # Attribute Reference
    attribute_id = fields.Many2one(
        'woocommerce.product.attribute',
        string='Attribute',
        required=True,
        ondelete='cascade'
    )
    
    # WooCommerce Integration
    woocommerce_term_id = fields.Char(string='WooCommerce Term ID', help="ID in WooCommerce")
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
                          help="Number of products with this term")
    
    # Menu Order
    menu_order = fields.Integer(string='Menu Order', default=0, tracking=True)
    
    # Company
    company_id = fields.Many2one('res.company', string='Company',
                                default=lambda self: self.env.company, required=True)
    
    # Constraints
    _sql_constraints = [
        ('name_unique', 'unique(name, attribute_id)', 'Term name must be unique per attribute!')
    ]

    def action_export_to_woocommerce(self):
        """Export term to WooCommerce"""
        self.ensure_one()
        try:
            # Prepare term data for WooCommerce
            term_data = {
                'name': self.name,
                'slug': self.slug or self.name.lower().replace(' ', '-'),
                'description': self.description or '',
                'menu_order': self.menu_order
            }
            
            # Export via sync service
            sync_service = self.env['woocommerce.sync.service']
            result = sync_service.export_attribute_term(self.attribute_id.configuration_id, self.attribute_id.woocommerce_attribute_id, term_data)
            
            if result:
                self.write({
                    'exported_in_woocommerce': True,
                    'last_sync_date': fields.Datetime.now(),
                    'sync_status': 'synced',
                    'woocommerce_term_id': result.get('id')
                })
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Term exported to WooCommerce successfully'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
        except Exception as e:
            self.write({'sync_status': 'failed'})
            raise UserError(_('Failed to export term: %s') % str(e))

    def action_import_from_woocommerce(self):
        """Import term from WooCommerce"""
        self.ensure_one()
        try:
            # Import via sync service
            sync_service = self.env['woocommerce.sync.service']
            result = sync_service.import_attribute_term(self.attribute_id.configuration_id, self.attribute_id.woocommerce_attribute_id, self.woocommerce_term_id)
            
            if result:
                self._update_from_woocommerce_data(result)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Term imported from WooCommerce successfully'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
        except Exception as e:
            raise UserError(_('Failed to import term: %s') % str(e))

    def _update_from_woocommerce_data(self, woo_data):
        """Update term from WooCommerce data"""
        self.write({
            'name': woo_data.get('name', self.name),
            'slug': woo_data.get('slug', ''),
            'description': woo_data.get('description', ''),
            'count': woo_data.get('count', 0),
            'menu_order': woo_data.get('menu_order', 0),
            'last_sync_date': fields.Datetime.now(),
            'sync_status': 'synced'
        })

    def name_get(self):
        """Custom name display"""
        result = []
        for record in self:
            name = f"{record.attribute_id.name}: {record.name}"
            if record.count > 0:
                name += f" ({record.count} products)"
            if not record.active:
                name += " [Inactive]"
            result.append((record.id, name))
        return result
