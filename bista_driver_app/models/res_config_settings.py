from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    shipment_google_map_api_key = fields.Char(string="Shipment Google Map API Key", config_parameter='bista_driver_app.shipment_google_map_api_key')
    fleet_google_map_api_key = fields.Char(string="Fleet Google Map API Key", config_parameter='bista_driver_app.fleet_google_map_api_key')
    
    # NOTE: For Fleet app separate firebase configuration is being used. Following fields is being used to maintain Fleet specific
    # firebase configuration only 
    fleet_firebase_name = fields.Char('Firebase Project Name')
    fleet_firebase_id = fields.Char('Firebase Project ID')
    fleet_firebase_key_file = fields.Binary('Firebase Admin Key File')

    @api.model
    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        set_param = self.env['ir.config_parameter'].set_param
        set_param('bista_driver_app.fleet_firebase_project_name', self.fleet_firebase_name)
        set_param('bista_driver_app.fleet_firebase_project_id', self.fleet_firebase_id)
        set_param('bista_driver_app.fleet_firebase_admin_key_file', self.fleet_firebase_key_file)
        return res

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        firebase_project_name = self.env['ir.config_parameter'].sudo().get_param(
            'bista_driver_app.fleet_firebase_project_name')
        firebase_project_id = self.env['ir.config_parameter'].sudo().get_param(
            'bista_driver_app.fleet_firebase_project_id')
        firebase_admin_key_file = self.env['ir.config_parameter'].sudo().get_param(
            'bista_driver_app.fleet_firebase_admin_key_file')
        res.update(
            fleet_firebase_name=firebase_project_name,
            fleet_firebase_id=firebase_project_id,
            fleet_firebase_key_file=firebase_admin_key_file,
        )
        return res