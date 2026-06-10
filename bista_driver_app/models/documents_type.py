from odoo import models,fields,api,_
from odoo.exceptions import UserError



class DriverDocumentsType(models.Model):
    _name = 'driver.documents.type'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Documents Types'
    _rec_name = 'type_name'
    _order = 'type_name asc'

    type_name = fields.Char(string="Name", required=True, tracking=True)
    description = fields.Text(string="Description", tracking=True)
    # is_shipment_document = fields.Boolean(string="Shipment Document", default=False)
    is_inventory_document = fields.Boolean(string="Inventory Document", default=False, tracking=True)
    active = fields.Boolean(default=True, tracking=True)


    is_shipment_document = fields.Boolean(string="Shipment Document", default=False, tracking=True)
    is_default_shipment_document = fields.Boolean(string="Default Shipment Document", default=False, tracking=True)

    def check_default_shipment_doc(self, vals):
        """
        This function checks if there's already a document type is assigned as default shipment document
        :return: Raise UserError if there is already a default shipment document
        """
        for rec in self:
            if vals.get('is_default_shipment_document'):
                default_shipment_doc = self.search([('is_default_shipment_document', '=', True)])
                if default_shipment_doc and default_shipment_doc != rec:
                    raise UserError(_("There is already a default shipment document type: %s") % (default_shipment_doc.type_name))
        return True

    def create(self, vals):
        if 'is_default_shipment_document' in vals:
            self.check_default_shipment_doc(vals)
        return super(DriverDocumentsType, self).create(vals)

    def write(self, vals):
        if 'is_default_shipment_document' in vals:
            self.check_default_shipment_doc(vals)
        return super(DriverDocumentsType, self).write(vals)

    def unlink(self):
        for rec in self:
            if rec == self.env.ref('bista_driver_app.driver_document_type_pod_fleet'):
                raise UserError(f"{rec.description} can not be deleted")
        return super(DriverDocumentsType, self).unlink()

    @api.model
    def web_search_read(self, domain, specification, offset=0, limit=None, order=None, count_limit=None):
        if not self.env.user.has_group(
                'bista_driver_app.group_shipment_dispatcher_access') and not self.env.user.has_group(
            'base.group_system'):
            raise UserError(_('You are not allowed to access this Record'))
        res = super().web_search_read(domain, specification, offset=offset, limit=limit, order=order,
                                      count_limit=count_limit)
        return res