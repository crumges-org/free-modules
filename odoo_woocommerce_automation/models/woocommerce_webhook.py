# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import logging
import json
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class WooCommerceWebhook(models.Model):
    """WooCommerce Webhook Management for Real-time Event Handling"""
    _name = 'woocommerce.webhook'
    _description = 'WooCommerce Webhook'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(string='Webhook Name', required=True, tracking=True)
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
    woocommerce_webhook_id = fields.Char(string='WooCommerce Webhook ID', help="ID in WooCommerce")
    topic = fields.Selection([
        ('order.created', 'Order Created'),
        ('order.updated', 'Order Updated'),
        ('order.deleted', 'Order Deleted'),
        ('order.restored', 'Order Restored'),
        ('product.created', 'Product Created'),
        ('product.updated', 'Product Updated'),
        ('product.deleted', 'Product Deleted'),
        ('product.restored', 'Product Restored'),
        ('customer.created', 'Customer Created'),
        ('customer.updated', 'Customer Updated'),
        ('customer.deleted', 'Customer Deleted'),
        ('coupon.created', 'Coupon Created'),
        ('coupon.updated', 'Coupon Updated'),
        ('coupon.deleted', 'Coupon Deleted'),
        ('coupon.restored', 'Coupon Restored'),
        ('product.category.created', 'Product Category Created'),
        ('product.category.updated', 'Product Category Updated'),
        ('product.category.deleted', 'Product Category Deleted'),
        ('product.tag.created', 'Product Tag Created'),
        ('product.tag.updated', 'Product Tag Updated'),
        ('product.tag.deleted', 'Product Tag Deleted'),
    ], string='Webhook Topic', required=True, tracking=True)
    
    # Status and Delivery
    status = fields.Selection([
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('disabled', 'Disabled')
    ], string='Status', default='active', tracking=True)
    
    delivery_url = fields.Char(string='Delivery URL', required=True, tracking=True,
                              help="URL where webhook payload will be delivered")
    
    # Security
    secret = fields.Char(string='Secret Key', tracking=True,
                        help="Secret key for webhook signature verification")
    
    # Statistics
    delivery_count = fields.Integer(string='Delivery Count', default=0, tracking=True)
    failure_count = fields.Integer(string='Failure Count', default=0, tracking=True)
    last_delivery = fields.Datetime(string='Last Delivery', tracking=True)
    last_failure = fields.Datetime(string='Last Failure', tracking=True)
    last_failure_reason = fields.Text(string='Last Failure Reason')
    
    # Company
    company_id = fields.Many2one('res.company', string='Company',
                                default=lambda self: self.env.company, required=True)
    
    # Constraints
    _sql_constraints = [
        ('topic_unique', 'unique(topic, configuration_id)', 'Webhook topic must be unique per configuration!')
    ]

    def action_create_in_woocommerce(self):
        """Create webhook in WooCommerce"""
        self.ensure_one()
        try:
            # Prepare webhook data
            webhook_data = {
                'name': self.name,
                'topic': self.topic,
                'status': self.status,
                'delivery_url': self.delivery_url,
                'secret': self.secret or '',
            }
            
            # Create via sync service
            sync_service = self.env['woocommerce.sync.service']
            result = sync_service.create_webhook(self.configuration_id, webhook_data)
            
            if result:
                self.write({
                    'woocommerce_webhook_id': result.get('id'),
                    'status': result.get('status', 'active')
                })
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Webhook created in WooCommerce successfully'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
        except Exception as e:
            raise UserError(_('Failed to create webhook: %s') % str(e))

    def action_delete_from_woocommerce(self):
        """Delete webhook from WooCommerce"""
        self.ensure_one()
        if not self.woocommerce_webhook_id:
            raise UserError(_('Webhook not yet created in WooCommerce'))
        
        try:
            # Delete via sync service
            sync_service = self.env['woocommerce.sync.service']
            sync_service.delete_webhook(self.configuration_id, self.woocommerce_webhook_id)
            
            self.write({
                'woocommerce_webhook_id': False,
                'status': 'disabled'
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Webhook deleted from WooCommerce successfully'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(_('Failed to delete webhook: %s') % str(e))

    def action_toggle_status(self):
        """Toggle webhook status between Active and Paused"""
        self.ensure_one()
        if not self.woocommerce_webhook_id:
            raise UserError(_('Webhook not yet created in WooCommerce'))
        
        try:
            new_status = 'paused' if self.status == 'active' else 'active'
            
            # Update via sync service
            sync_service = self.env['woocommerce.sync.service']
            sync_service.update_webhook_status(self.configuration_id, self.woocommerce_webhook_id, new_status)
            
            self.write({'status': new_status})
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Webhook status updated successfully'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(_('Failed to update webhook status: %s') % str(e))

    def action_test_webhook(self):
        """Test webhook delivery"""
        self.ensure_one()
        try:
            # Test via sync service
            sync_service = self.env['woocommerce.sync.service']
            result = sync_service.test_webhook(self.configuration_id, self.woocommerce_webhook_id)
            
            if result:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Webhook test successful'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
        except Exception as e:
            raise UserError(_('Webhook test failed: %s') % str(e))

    def action_view_delivery_logs(self):
        """View webhook delivery logs"""
        return {
            'name': _('Webhook Delivery Logs'),
            'type': 'ir.actions.act_window',
            'res_model': 'woocommerce.webhook.log',
            'view_mode': 'list,form',
            'domain': [('webhook_id', '=', self.id)],
            'context': {'default_webhook_id': self.id},
        }

    def process_webhook_payload(self, payload, headers):
        """Process incoming webhook payload"""
        self.ensure_one()
        
        try:
            # Verify webhook signature if secret is set
            if self.secret and not self._verify_signature(payload, headers):
                raise UserError(_('Invalid webhook signature'))
            
            # Parse payload
            data = json.loads(payload) if isinstance(payload, str) else payload
            
            # Process based on topic
            if self.topic.startswith('order.'):
                self._process_order_webhook(data)
            elif self.topic.startswith('product.'):
                self._process_product_webhook(data)
            elif self.topic.startswith('customer.'):
                self._process_customer_webhook(data)
            elif self.topic.startswith('coupon.'):
                self._process_coupon_webhook(data)
            elif self.topic.startswith('product.category.'):
                self._process_category_webhook(data)
            elif self.topic.startswith('product.tag.'):
                self._process_tag_webhook(data)
            
            # Update statistics
            self.write({
                'delivery_count': self.delivery_count + 1,
                'last_delivery': fields.Datetime.now()
            })
            
            # Create log entry
            self.env['woocommerce.webhook.log'].create({
                'webhook_id': self.id,
                'topic': self.topic,
                'payload': json.dumps(data, indent=2),
                'status': 'success',
                'delivery_date': fields.Datetime.now()
            })
            
        except Exception as e:
            # Update failure statistics
            self.write({
                'failure_count': self.failure_count + 1,
                'last_failure': fields.Datetime.now(),
                'last_failure_reason': str(e)
            })
            
            # Create failure log entry
            self.env['woocommerce.webhook.log'].create({
                'webhook_id': self.id,
                'topic': self.topic,
                'payload': json.dumps(payload, indent=2) if isinstance(payload, dict) else str(payload),
                'status': 'failed',
                'error_message': str(e),
                'delivery_date': fields.Datetime.now()
            })
            
            _logger.error(f"Webhook processing failed: {str(e)}")
            raise

    def _verify_signature(self, payload, headers):
        """Verify webhook signature"""
        # Implementation depends on WooCommerce signature verification
        # This is a placeholder for the actual verification logic
        return True

    def _process_order_webhook(self, data):
        """Process order-related webhook"""
        order_id = data.get('id')
        if order_id:
            sync_service = self.env['woocommerce.sync.service']
            if self.topic == 'order.created':
                sync_service.import_order(self.configuration_id, order_id)
            elif self.topic == 'order.updated':
                sync_service.update_order(self.configuration_id, order_id)
            elif self.topic == 'order.deleted':
                sync_service.delete_order(self.configuration_id, order_id)

    def _process_product_webhook(self, data):
        """Process product-related webhook"""
        product_id = data.get('id')
        if product_id:
            sync_service = self.env['woocommerce.sync.service']
            if self.topic == 'product.created':
                sync_service.import_product(self.configuration_id, product_id)
            elif self.topic == 'product.updated':
                sync_service.update_product(self.configuration_id, product_id)
            elif self.topic == 'product.deleted':
                sync_service.delete_product(self.configuration_id, product_id)

    def _process_customer_webhook(self, data):
        """Process customer-related webhook"""
        customer_id = data.get('id')
        if customer_id:
            sync_service = self.env['woocommerce.sync.service']
            if self.topic == 'customer.created':
                sync_service.import_customer(self.configuration_id, customer_id)
            elif self.topic == 'customer.updated':
                sync_service.update_customer(self.configuration_id, customer_id)
            elif self.topic == 'customer.deleted':
                sync_service.delete_customer(self.configuration_id, customer_id)

    def _process_coupon_webhook(self, data):
        """Process coupon-related webhook"""
        coupon_id = data.get('id')
        if coupon_id:
            sync_service = self.env['woocommerce.sync.service']
            if self.topic == 'coupon.created':
                sync_service.import_coupon(self.configuration_id, coupon_id)
            elif self.topic == 'coupon.updated':
                sync_service.update_coupon(self.configuration_id, coupon_id)
            elif self.topic == 'coupon.deleted':
                sync_service.delete_coupon(self.configuration_id, coupon_id)

    def _process_category_webhook(self, data):
        """Process category-related webhook"""
        category_id = data.get('id')
        if category_id:
            sync_service = self.env['woocommerce.sync.service']
            if self.topic == 'product.category.created':
                sync_service.import_category(self.configuration_id, category_id)
            elif self.topic == 'product.category.updated':
                sync_service.update_category(self.configuration_id, category_id)
            elif self.topic == 'product.category.deleted':
                sync_service.delete_category(self.configuration_id, category_id)

    def _process_tag_webhook(self, data):
        """Process tag-related webhook"""
        tag_id = data.get('id')
        if tag_id:
            sync_service = self.env['woocommerce.sync.service']
            if self.topic == 'product.tag.created':
                sync_service.import_tag(self.configuration_id, tag_id)
            elif self.topic == 'product.tag.updated':
                sync_service.update_tag(self.configuration_id, tag_id)
            elif self.topic == 'product.tag.deleted':
                sync_service.delete_tag(self.configuration_id, tag_id)

    @api.model
    def create(self, vals):
        """Override create to set default delivery URL"""
        if not vals.get('delivery_url'):
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            vals['delivery_url'] = f"{base_url}/woocommerce/webhook/{vals.get('topic', 'default')}"
        return super(WooCommerceWebhook, self).create(vals)

    def name_get(self):
        """Custom name display"""
        result = []
        for record in self:
            name = f"{record.name} ({record.topic})"
            if record.status != 'active':
                name += f" [{record.status}]"
            result.append((record.id, name))
        return result
