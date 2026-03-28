from odoo import models, fields, api
from odoo.exceptions import ValidationError

class YouTubeApiSettings(models.Model):
    _name = 'youtube.api.settings'
    _description = 'YouTube API Settings'

    name = fields.Char(string='Name', default='YouTube API Settings')
    client_secrets_attachment_id = fields.Many2one(
        'ir.attachment',
        string='Client Secrets JSON',
        domain=[('mimetype', '=', 'application/json')],
        help='Upload the client_secrets.json file downloaded from Google Cloud Console.'
    )
    file_name = fields.Char("File Name")
    file_data = fields.Binary("Upload File")

    @api.onchange('file_data')
    def _onchange_file_data(self):
        """When a file is uploaded, create an ir.attachment and link it."""
        if self.file_data:
            attachment = self.env['ir.attachment'].create({
                'name': self.file_name or "client_json",
                'datas': self.file_data,
                'mimetype': 'application/json',  # Or detect from filename
                'res_model': self._name,
                'res_id': self.id or 0,
            })
            self.client_secrets_attachment_id = attachment.id

    @api.constrains('client_secrets_attachment_id')
    def _check_client_secrets(self):
        for record in self:
            if record.client_secrets_attachment_id and record.client_secrets_attachment_id.mimetype != 'application/json':
                raise ValidationError('The uploaded file must be a JSON file (client_secrets.json).')

    @api.model
    def create(self, vals):
        # Ensure only one settings record exists
        if self.search_count([]) > 0:
            raise ValidationError('Only one YouTube API Settings record is allowed.')
        return super().create(vals)
