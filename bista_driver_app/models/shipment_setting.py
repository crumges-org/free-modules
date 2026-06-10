# -*- coding: utf-8 -*-
from odoo import fields, models, http, api, Command, _, SUPERUSER_ID
from odoo.exceptions import UserError
import logging
from datetime import timedelta
import re

_logger = logging.getLogger(__name__)

class ShipmentSettings(models.Model):
    _name = "shipment.settings"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Settings"

    name = fields.Char(string="Name", required=True, tracking=True)
    value = fields.Integer(string="Value", required=True, tracking=True)
    url_value_en = fields.Char(string="URL(EN)", tracking=True) # T2787: url field name change
    url_value_es = fields.Char(string="URL(ES)", tracking=True) # T2787
    unit = fields.Char(string="Unit", required=True, tracking=True)
    description = fields.Char(string="Description")
    active = fields.Boolean(default=True, tracking=True)
    is_fleet_system_url = fields.Boolean(string="Is Fleet System URL", default=False, tracking=True)


    def get_raidus(self, name):
        return self.env['shipment.settings'].search_read([('name', '=', name)], fields=['value', 'unit'])

    @api.model
    def web_search_read(self, domain, specification, offset=0, limit=None, order=None, count_limit=None):
        if not self.env.user.has_group(
                'bista_driver_app.group_shipment_dispatcher_access') and not self.env.user.has_group(
            'base.group_system'):
            raise UserError(_('You are not allowed to access this Record'))
        res = super().web_search_read(domain, specification, offset=offset, limit=limit, order=order,
                                      count_limit=count_limit)
        return res

    # T2545 ELD Integration & Master Table Set up
    def write(self, vals):
        # Post a message when the description is changed.
        if vals.get('description'):
            for rec in self:
                rec.message_post(body=f"""<b>Description Changed</b> :
                    <details>
                        <summary style="color: #017e84; font-weight: bold;">Show More</summary>
                        {rec.description}
                        <h2><b><i class='fa fa-long-arrow-right'></i></b></h2>
                        {vals.get('description')}
                    </details>""", body_is_html=True)

        res = super(ShipmentSettings, self).write(vals)

        for shipment_settings_id in self:
            if vals.get('value') and shipment_settings_id == self.env.ref('bista_driver_app.shipment_settings_location_reporting_frequency'):
                try:
                    cron_values = {
                        'interval_number': shipment_settings_id.value,
                        'interval_type': 'minutes',
                        'nextcall': fields.Datetime.now() + timedelta(minutes=shipment_settings_id.value),
                    }


                    # cron_id.sudo().interval_number = shipment_settings_id.value
                    # cron_id.sudo().interval_type = 'minutes'
                    # cron_id.sudo().nextcall = fields.Datetime.now() + timedelta(minutes=shipment_settings_id.value)
                   
                except Exception as err:
                    _logger.warning("Error updating Driver\Shipments\Tracker Devices Scheduled Action", err)
        return res

    # T2787: To remove HTML tags from description field
    def action_update_data(self):
        for setting_id in self:
            if setting_id.description:
                final_data = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ',  setting_id.description)).strip()
                setting_id.sudo().write({'description': final_data})
