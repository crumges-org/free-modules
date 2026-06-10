# -*- coding: utf-8 -*-
from odoo import fields, models, http, api, Command, _, SUPERUSER_ID


class ShipmentDocument(models.Model):
    _name = 'shipment.document'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Shipment Document'
    _rec_name = 'filename'
    _order = 'id desc'

    filename = fields.Char(string='Filename', required=True)
    file = fields.Binary(string="File", required=True, attachment=True)
    description = fields.Char(string='Description')
    carrier_id = fields.Many2one('shipment.carrier', string="Carrier")
    document_type_id = fields.Many2one('driver.documents.type', domain=[('is_shipment_document', '=', True)], string="Document Type")
    shipment_id = fields.Many2one('shipment.shipment', string="Shipment", ondelete='cascade')
    driver_id = fields.Many2one('fleet.driver', string="Driver")
    truck_number = fields.Char(related="driver_id.truck_no" ,readonly=False, string="Truck No")
    driver_phone = fields.Char(related='driver_id.phone', readonly=False, string="Driver Phone")
    driver_user_id = fields.Many2one('res.users', related='driver_id.user_id', readonly=False, string="Driver User")
    active = fields.Boolean(default=True, tracking=True)
    date = fields.Datetime(string="Upload Date")
    is_signature = fields.Boolean(string="Signature", default=False)
    document_signature = fields.Binary(string="Document Signature", attachment=True)
    original_file = fields.Binary(string="Original File", attachment=True) # in this field initial document is kept for future signature update
    signature_time_data = fields.Json(string="Signature Time Data") 
    signed_by = fields.Char(string='Signed By')
    @api.model
    def create(self, vals):
        user = self.env.user
        # Check if user has type 'driver_user'
        # if user.standard_template_integration_user_type == 'driver_user':
        if user.has_group('bista_driver_app.group_shipment_driver_user_access') and not user.has_group('bista_driver_app.group_shipment_dispatcher_access'):
            driver = self.env['fleet.driver'].search([('user_id', '=', user.id)], limit=1)
            if driver:
                vals['driver_id'] = driver.id
                vals['truck_number'] = driver.truck_no
                vals['driver_phone'] = driver.phone
        res = super(ShipmentDocument, self).create(vals)
        # T2843:timeline record for document upload
        for rec in res:
            if rec.document_type_id:
                self.env['shipment.timeline'].create({
                    'name': f"{rec.document_type_id.display_name} document has been uploaded",
                    'datetime': fields.Datetime.now(),
                    'user_id': self.env.user.id,
                    'user_name': self.env.user.name,
                    'driver_id': rec.shipment_id.driver_id.id if rec.shipment_id.driver_id else False,
                    'source_id': self.sudo().env.ref('bista_driver_app.source_manual_update').id,
                    'shipment_id': rec.shipment_id.id,
                })
        return res

### driver.documents.type model Related Work ###
    def write(self, vals):
        # T2843:timeline record for document update
        message = False
        if vals.get('document_type_id') and vals['document_type_id'] != self.document_type_id.id and vals.get('file'):
            new_doc_type_id = self.env['driver.documents.type'].sudo().browse(int(vals['document_type_id']))
            message = f'Document type changed from {self.document_type_id.display_name} to {new_doc_type_id.display_name} and file has been updated'
        elif vals.get('document_type_id') and vals['document_type_id'] != self.document_type_id.id:
            new_doc_type_id = self.env['driver.documents.type'].sudo().browse(int(vals['document_type_id']))
            message = f'Document type changed from {self.document_type_id.display_name} to {new_doc_type_id.display_name}'
        elif vals.get('file'):
            message = f'{self.document_type_id.display_name} document file has been updated'
        if message:
            self.env['shipment.timeline'].create({
                'name': message,
                'datetime': fields.Datetime.now(),
                'user_id': self.env.user.id,
                'user_name': self.env.user.name,
                'driver_id': self.shipment_id.driver_id.id if self.shipment_id.driver_id else False,
                'source_id': self.sudo().env.ref('bista_driver_app.source_manual_update').id,
                'shipment_id': self.shipment_id.id,
            })
        return super(ShipmentDocument, self).write(vals)

### driver.documents.type model Related Work ###
    def unlink(self):
        # T2843:timeline record for document delete
        for rec in self:
            if rec.document_type_id:
                self.env['shipment.timeline'].create({
                    'name': f'{rec.document_type_id.display_name} document has been deleted',
                    'datetime': fields.Datetime.now(),
                    'user_id': self.env.user.id,
                    'user_name': self.env.user.name,
                    'driver_id': rec.shipment_id.driver_id.id if rec.shipment_id.driver_id else False,
                    'source_id': self.sudo().env.ref('bista_driver_app.source_manual_update').id,
                    'shipment_id': rec.shipment_id.id,
                })
        return super(ShipmentDocument, self).unlink()
    