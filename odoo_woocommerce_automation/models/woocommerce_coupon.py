# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class WooCommerceCoupon(models.Model):
    """WooCommerce Coupon Management"""
    _name = 'woocommerce.coupon'
    _description = 'WooCommerce Coupon'
    _rec_name = 'code'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(string='Coupon Name', required=True, tracking=True)
    code = fields.Char(string='Coupon Code', required=True, tracking=True, help="Unique coupon code")
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
    woocommerce_coupon_id = fields.Char(string='WooCommerce ID', help="ID in WooCommerce")
    exported_in_woocommerce = fields.Boolean(string='Exported in WooCommerce', default=False, tracking=True)
    last_sync_date = fields.Datetime(string='Last Sync Date', tracking=True)
    sync_status = fields.Selection([
        ('pending', 'Pending'),
        ('synced', 'Synced'),
        ('failed', 'Failed'),
        ('updated', 'Updated')
    ], string='Sync Status', default='pending', tracking=True)
    
    # Discount Configuration
    discount_type = fields.Selection([
        ('percent', 'Percentage Discount'),
        ('fixed_cart', 'Fixed Cart Discount'),
        ('fixed_product', 'Fixed Product Discount'),
        ('smart_coupon', 'Smart Coupon')
    ], string='Discount Type', default='fixed_cart', required=True, tracking=True)
    
    amount = fields.Float(string='Discount Amount', required=True, tracking=True,
                         help="The amount of discount")
    
    # Usage Restrictions
    minimum_amount = fields.Float(string='Minimum Spend', tracking=True,
                                 help="Minimum order amount before coupon applies")
    maximum_amount = fields.Float(string='Maximum Spend', tracking=True,
                                 help="Maximum order amount allowed with coupon")
    
    # Usage Limits
    usage_limit = fields.Integer(string='Usage Limit Per Coupon', tracking=True,
                                help="How many times the coupon can be used in total")
    usage_limit_per_user = fields.Integer(string='Usage Limit Per User', tracking=True,
                                         help="How many times the coupon can be used per customer")
    limit_usage_to_x_items = fields.Integer(string='Limit Usage to X Items', tracking=True,
                                           help="Max number of items the coupon can be applied to")
    
    # Current Usage
    usage_count = fields.Integer(string='Usage Count', default=0, tracking=True,
                                help="Number of times the coupon has been used")
    used_by = fields.Text(string='Used By', help="List of users who have used this coupon")
    
    # Date Restrictions
    date_created = fields.Date(string='Date Created', default=fields.Date.today, tracking=True)
    expiry_date = fields.Date(string='Expiry Date', tracking=True)
    
    # Advanced Options
    individual_use = fields.Boolean(string='Individual Use Only', default=False, tracking=True,
                                   help="If true, this coupon cannot be used with other coupons")
    exclude_sale_items = fields.Boolean(string='Exclude Sale Items', default=False, tracking=True,
                                       help="If true, coupon will not apply to items on sale")
    free_shipping = fields.Boolean(string='Allow Free Shipping', default=False, tracking=True,
                                  help="If true, coupon grants free shipping")
    
    # Product Restrictions
    product_ids = fields.Many2many('product.template', string='Products',
                                  help="Products this coupon can be used on")
    exclude_product_ids = fields.Many2many('product.template', 'woo_coupon_exclude_product_rel',
                                          'coupon_id', 'product_id', string='Exclude Products',
                                          help="Products this coupon cannot be used on")
    
    product_category_ids = fields.Many2many('product.category', string='Product Categories',
                                           help="Categories this coupon can be used on")
    exclude_product_category_ids = fields.Many2many('product.category', 'woo_coupon_exclude_category_rel',
                                                   'coupon_id', 'category_id', string='Exclude Categories',
                                                   help="Categories this coupon cannot be used on")
    
    # Customer Restrictions
    customer_ids = fields.Many2many('res.partner', string='Customers',
                                   help="Specific customers who can use this coupon")
    email_restrictions = fields.Text(string='Email Restrictions',
                                    help="Comma-separated list of email addresses")
    
    # Company
    company_id = fields.Many2one('res.company', string='Company',
                                default=lambda self: self.env.company, required=True)
    
    # Constraints
    _sql_constraints = [
        ('code_unique', 'unique(code, configuration_id)', 'Coupon code must be unique per configuration!')
    ]

    @api.constrains('amount')
    def _check_amount(self):
        """Validate discount amount"""
        for record in self:
            if record.amount <= 0:
                raise UserError(_('Discount amount must be greater than zero.'))
            if record.discount_type == 'percent' and record.amount > 100:
                raise UserError(_('Percentage discount cannot exceed 100%.'))

    @api.constrains('expiry_date')
    def _check_expiry_date(self):
        """Validate expiry date"""
        for record in self:
            if record.expiry_date and record.expiry_date < fields.Date.today():
                raise UserError(_('Expiry date cannot be in the past.'))

    def action_export_to_woocommerce(self):
        """Export coupon to WooCommerce"""
        self.ensure_one()
        try:
            # Prepare coupon data for WooCommerce
            coupon_data = self._prepare_woocommerce_data()
            
            # Export via sync service
            sync_service = self.env['woocommerce.sync.service']
            result = sync_service.export_coupon(self.configuration_id, coupon_data)
            
            if result:
                self.write({
                    'exported_in_woocommerce': True,
                    'last_sync_date': fields.Datetime.now(),
                    'sync_status': 'synced',
                    'woocommerce_coupon_id': result.get('id')
                })
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Coupon exported to WooCommerce successfully'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
        except Exception as e:
            self.write({
                'sync_status': 'failed'
            })
            raise UserError(_('Failed to export coupon: %s') % str(e))

    def action_import_from_woocommerce(self):
        """Import coupon from WooCommerce"""
        self.ensure_one()
        try:
            # Import via sync service
            sync_service = self.env['woocommerce.sync.service']
            result = sync_service.import_coupon(self.configuration_id, self.woocommerce_coupon_id)
            
            if result:
                self._update_from_woocommerce_data(result)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Coupon imported from WooCommerce successfully'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
        except Exception as e:
            raise UserError(_('Failed to import coupon: %s') % str(e))

    def action_sync_all_coupons(self):
        """Sync all coupons for a configuration"""
        self.ensure_one()
        try:
            sync_service = self.env['woocommerce.sync.service']
            sync_service.sync_coupons(self.configuration_id)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('All coupons synchronized successfully'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(_('Failed to sync coupons: %s') % str(e))

    def _prepare_woocommerce_data(self):
        """Prepare coupon data for WooCommerce API"""
        return {
            'code': self.code,
            'amount': str(self.amount),
            'discount_type': self.discount_type,
            'description': self.description or '',
            'date_expires': self.expiry_date.isoformat() if self.expiry_date else None,
            'minimum_amount': str(self.minimum_amount) if self.minimum_amount else '',
            'maximum_amount': str(self.maximum_amount) if self.maximum_amount else '',
            'individual_use': self.individual_use,
            'exclude_sale_items': self.exclude_sale_items,
            'free_shipping': self.free_shipping,
            'usage_limit': self.usage_limit or None,
            'usage_limit_per_user': self.usage_limit_per_user or None,
            'limit_usage_to_x_items': self.limit_usage_to_x_items or None,
            'product_ids': [p.id for p in self.product_ids],
            'exclude_product_ids': [p.id for p in self.exclude_product_ids],
            'product_category_ids': [c.id for c in self.product_category_ids],
            'exclude_product_category_ids': [c.id for c in self.exclude_product_category_ids],
            'email_restrictions': self.email_restrictions or '',
        }

    def _update_from_woocommerce_data(self, woo_data):
        """Update coupon from WooCommerce data"""
        self.write({
            'name': woo_data.get('description', self.name),
            'amount': float(woo_data.get('amount', 0)),
            'discount_type': woo_data.get('discount_type', 'fixed_cart'),
            'usage_count': woo_data.get('usage_count', 0),
            'used_by': woo_data.get('used_by', ''),
            'date_created': woo_data.get('date_created'),
            'last_sync_date': fields.Datetime.now(),
            'sync_status': 'synced'
        })

    def action_view_usage_history(self):
        """View coupon usage history"""
        return {
            'name': _('Coupon Usage History'),
            'type': 'ir.actions.act_window',
            'res_model': 'woocommerce.coupon.usage',
            'view_mode': 'list,form',
            'domain': [('coupon_id', '=', self.id)],
            'context': {'default_coupon_id': self.id},
        }

    def action_test_coupon(self):
        """Test coupon validity"""
        self.ensure_one()
        if not self.active:
            raise UserError(_('This coupon is not active.'))
        
        if self.expiry_date and self.expiry_date < fields.Date.today():
            raise UserError(_('This coupon has expired.'))
        
        if self.usage_limit and self.usage_count >= self.usage_limit:
            raise UserError(_('This coupon has reached its usage limit.'))
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Valid'),
                'message': _('Coupon is valid and ready to use'),
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model
    def create(self, vals):
        """Override create to set default values"""
        if not vals.get('name') and vals.get('code'):
            vals['name'] = vals['code']
        return super(WooCommerceCoupon, self).create(vals)

    def write(self, vals):
        """Override write to track changes"""
        if 'code' in vals and not vals.get('name'):
            vals['name'] = vals['code']
        return super(WooCommerceCoupon, self).write(vals)

    def name_get(self):
        """Custom name display"""
        result = []
        for record in self:
            name = f"{record.code}"
            if record.discount_type == 'percent':
                name += f" ({record.amount}%)"
            else:
                name += f" (${record.amount})"
            if not record.active:
                name += " [Inactive]"
            result.append((record.id, name))
        return result
