# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class WooCommerceCouponUsage(models.Model):
	"""Coupon Usage Log"""
	_name = 'woocommerce.coupon.usage'
	_description = 'WooCommerce Coupon Usage'
	_order = 'usage_date desc'

	coupon_id = fields.Many2one('woocommerce.coupon', string='Coupon', required=True, ondelete='cascade')
	order_id = fields.Many2one('sale.order', string='Order')
	customer_id = fields.Many2one('res.partner', string='Customer')
	amount = fields.Float(string='Discount Amount')
	usage_date = fields.Datetime(string='Usage Date', default=fields.Datetime.now)
	notes = fields.Text(string='Notes')
	company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)
