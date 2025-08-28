# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class WooCommerceWebhookLog(models.Model):
	"""Webhook Delivery Logs"""
	_name = 'woocommerce.webhook.log'
	_description = 'WooCommerce Webhook Delivery Log'
	_order = 'delivery_date desc'

	webhook_id = fields.Many2one('woocommerce.webhook', string='Webhook', required=True, ondelete='cascade')
	topic = fields.Char(string='Topic')
	payload = fields.Text(string='Payload')
	status = fields.Selection([
		('success', 'Success'),
		('failed', 'Failed')
	], string='Status', default='success')
	error_message = fields.Text(string='Error Message')
	delivery_date = fields.Datetime(string='Delivery Date', default=fields.Datetime.now)
	response_code = fields.Char(string='Response Code')
	response_message = fields.Char(string='Response Message')
	company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)
