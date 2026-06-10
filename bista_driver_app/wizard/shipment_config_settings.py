from odoo import fields, models, api


class ShipmentConfigSettings(models.TransientModel):
    _name = 'shipment.config.settings'
    _description = 'Description'

    # T2787: new shipment setting for custom layout

    location_reporting_freq_id = fields.Many2one('shipment.settings',default=lambda self: self.env.ref('bista_driver_app.shipment_settings_location_reporting_frequency'))
    location_reporting_freq_id_name = fields.Char(related='location_reporting_freq_id.name',readonly=False)
    location_reporting_freq_id_value = fields.Integer(related='location_reporting_freq_id.value',readonly=False)
    location_reporting_freq_id_unit = fields.Char(related='location_reporting_freq_id.unit')
    location_reporting_freq_id_description = fields.Char(related='location_reporting_freq_id.description',readonly=False)

    location_timeout_threshold_id = fields.Many2one('shipment.settings',default=lambda self: self.env.ref('bista_driver_app.shipment_settings_location_timeout_threshold'))
    location_timeout_threshold_id_name = fields.Char(related='location_timeout_threshold_id.name',readonly=False)
    location_timeout_threshold_id_value = fields.Integer(related='location_timeout_threshold_id.value',readonly=False)
    location_timeout_threshold_id_unit = fields.Char(related='location_timeout_threshold_id.unit')
    location_timeout_threshold_id_description = fields.Char(related='location_timeout_threshold_id.description',readonly=False)

    image_compression_ratio_id = fields.Many2one('shipment.settings',default=lambda self: self.env.ref('bista_driver_app.shipment_settings_image_compression_ratio'))
    image_compression_ratio_id_name = fields.Char(related='image_compression_ratio_id.name',readonly=False)
    image_compression_ratio_id_value = fields.Integer(related='image_compression_ratio_id.value',readonly=False)
    image_compression_ratio_id_unit = fields.Char(related='image_compression_ratio_id.unit')
    image_compression_ratio_id_description = fields.Char(related='image_compression_ratio_id.description',readonly=False)

    auto_refresh_interval_id = fields.Many2one('shipment.settings',default=lambda self: self.env.ref('bista_driver_app.shipment_settings_auto_refresh_interval'))
    auto_refresh_interval_id_name = fields.Char(related='auto_refresh_interval_id.name',readonly=False)
    auto_refresh_interval_id_value = fields.Integer(related='auto_refresh_interval_id.value',readonly=False)
    auto_refresh_interval_id_unit = fields.Char(related='auto_refresh_interval_id.unit')
    auto_refresh_interval_id_description = fields.Char(related='auto_refresh_interval_id.description',readonly=False)

    geofence_radius_id = fields.Many2one('shipment.settings',default=lambda self: self.env.ref('bista_driver_app.shipment_settings_geofence_radius'))
    geofence_radius_id_name = fields.Char(related='geofence_radius_id.name',readonly=False)
    geofence_radius_id_value = fields.Integer(related='geofence_radius_id.value',readonly=False)
    geofence_radius_id_unit = fields.Char(related='geofence_radius_id.unit')
    geofence_radius_id_description = fields.Char(related='geofence_radius_id.description',readonly=False)

    location_distance_filter_id = fields.Many2one('shipment.settings',default=lambda self: self.env.ref('bista_driver_app.shipment_settings_location_reporting_distance_filter'))
    location_distance_filter_id_name = fields.Char(related='location_distance_filter_id.name',readonly=False)
    location_distance_filter_id_value = fields.Integer(related='location_distance_filter_id.value',readonly=False)
    location_distance_filter_id_unit = fields.Char(related='location_distance_filter_id.unit')
    location_distance_filter_id_description = fields.Char(related='location_distance_filter_id.description',readonly=False)

    privacy_policy_id = fields.Many2one('shipment.settings',default=lambda self: self.env.ref('bista_driver_app.shipment_settings_privacy_policy_url'))
    privacy_policy_id_name = fields.Char(related='privacy_policy_id.name',readonly=False)
    privacy_policy_id_url_value_en = fields.Char(related='privacy_policy_id.url_value_en',readonly=False)
    privacy_policy_id_url_value_es= fields.Char(related='privacy_policy_id.url_value_es',readonly=False)
    privacy_policy_id_description = fields.Char(related='privacy_policy_id.description',readonly=False)

    terms_and_condition_id = fields.Many2one('shipment.settings',default=lambda self: self.env.ref('bista_driver_app.shipment_settings_terms_and_conditions_url'))
    terms_and_condition_id_name = fields.Char(related='terms_and_condition_id.name',readonly=False)
    terms_and_condition_id_url_value_en = fields.Char(related='terms_and_condition_id.url_value_en',readonly=False)
    terms_and_condition_id_url_value_es = fields.Char(related='terms_and_condition_id.url_value_es',readonly=False)
    terms_and_condition_id_description = fields.Char(related='terms_and_condition_id.description',readonly=False)
    # T2851: SMS frequency for location timeout
    location_timeout_freq_id = fields.Many2one('shipment.settings',default=lambda self: self.env.ref('bista_driver_app.shipment_settings_location_time_out_sms_frequency'))
    location_timeout_freq_id_name = fields.Char(related='location_timeout_freq_id.name',readonly=False)
    location_timeout_freq_id_value = fields.Integer(related='location_timeout_freq_id.value',readonly=False)
    location_timeout_freq_id_unit = fields.Char(related='location_timeout_freq_id.unit')
    location_timeout_freq_id_description = fields.Char(related='location_timeout_freq_id.description',readonly=False)



    # @api.model
    def execute(self):

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
