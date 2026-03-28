import os
import pickle
import logging
import base64
import tempfile
from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import UserError
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

_logger = logging.getLogger(__name__)


class YouTubeVideoUpload(models.Model):
    _name = 'youtube.video.upload'
    _description = 'YouTube Video Upload'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Title', required=True)
    description = fields.Text(string='Description')
    tags = fields.Char(string='Tags', help='Comma-separated tags, e.g., video,odoo,automation')
    category_id = fields.Selection([
        ('1', 'Film & Animation'),
        ('2', 'Autos & Vehicles'),
        ('10', 'Music'),
        ('15', 'Pets & Animals'),
        ('17', 'Sports'),
        ('19', 'Travel & Events'),
        ('20', 'Gaming'),
        ('22', 'People & Blogs'),
        ('23', 'Comedy'),
        ('24', 'Entertainment'),
        ('25', 'News & Politics'),
        ('26', 'Howto & Style'),
        ('27', 'Education'),
        ('28', 'Science & Technology'),
        ('29', 'Nonprofits & Activism'),
    ], string='Category', default='22')
    privacy_status = fields.Selection([
        ('public', 'Public'),
        ('private', 'Private'),
        ('unlisted', 'Unlisted'),
    ], string='Privacy Status', default='private')
    attachment_id = fields.Many2one('ir.attachment', string='Video File', required=True,
                                    domain=[('mimetype', 'in', ['video/mp4', 'video/mov', 'video/avi'])])
    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('uploaded', 'Uploaded'),
        ('failed', 'Failed'),
    ], string='Status', default='draft', readonly=True)
    video_upload = fields.Binary("Upload Video")
    video_filename = fields.Char("Video Filename")
    schedule_date = fields.Datetime(string='Schedule Date')
    youtube_video_id = fields.Char(string='YouTube Video ID', readonly=True)
    error_message = fields.Text(string='Error Message', readonly=True)

    @api.onchange('video_upload')
    def _onchange_video_upload(self):
        """When a file is uploaded, create an ir.attachment and link it."""
        if self.video_upload:
            attachment = self.env['ir.attachment'].create({
                'name': self.video_filename or "video_upload",
                'datas': self.video_upload,
                'mimetype': 'video/mp4',  # Or detect from filename
                'res_model': self._name,
                'res_id': self.id or 0,
            })
            self.attachment_id = attachment.id

    def _get_youtube_service(self):
        """Authenticate and return YouTube API service."""
        SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
        pickle_file = os.path.join(os.path.dirname(__file__), '../static/token_youtube_v3.pickle')

        # Retrieve client_secrets.json from settings
        settings = self.env['youtube.api.settings'].search([], limit=1)
        if not settings or not settings.client_secrets_attachment_id:
            raise UserError('Please upload client_secrets.json in YouTube API Settings.')

        # Save client_secrets.json to temporary file
        client_secrets_data = base64.b64decode(settings.client_secrets_attachment_id.datas)
        temp_client_secrets = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        temp_client_secrets.write(client_secrets_data)
        temp_client_secrets.close()

        credentials = None
        if os.path.exists(pickle_file):
            with open(pickle_file, 'rb') as token:
                credentials = pickle.load(token)

        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(temp_client_secrets.name, SCOPES)
                credentials = flow.run_local_server(port=0)
                with open(pickle_file, 'wb') as token:
                    pickle.dump(credentials, token)

        # Clean up temporary file
        os.unlink(temp_client_secrets.name)

        return build('youtube', 'v3', credentials=credentials)

    def action_schedule_upload(self):
        """Schedule the video upload."""
        for record in self:
            if not record.schedule_date:
                raise UserError('Please set a schedule date.')
            if record.state == 'draft':
                record.state = 'scheduled'
                record.message_post(body='Video upload scheduled for %s' % record.schedule_date)

    def action_upload_now(self):
        """Manually trigger upload to YouTube."""
        for record in self:
            if not record.attachment_id:
                raise UserError('No video file attached.')
            try:
                youtube = self._get_youtube_service()
                file_path = self._get_attachment_file_path()
                tags_list = [tag.strip() for tag in record.tags.split(',')] if record.tags else []

                body = {
                    'snippet': {
                        'title': record.name,
                        'description': record.description or '',
                        'tags': tags_list,
                        'categoryId': record.category_id,
                    },
                    'status': {
                        'privacyStatus': record.privacy_status,
                    }
                }

                media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
                request = youtube.videos().insert(
                    part='snippet,status',
                    body=body,
                    media_body=media
                )

                response = None
                while response is None:
                    status, response = request.next_chunk()
                    if status:
                        _logger.info('Uploaded %d%% for video %s', int(status.progress() * 100), record.name)

                record.youtube_video_id = response['id']
                record.state = 'uploaded'
                record.message_post(body='Video uploaded successfully. YouTube Video ID: %s' % response['id'])
            except Exception as e:
                print('faleddd')
                record.state = 'failed'
                record.error_message = str(e)
                record.message_post(body='Upload failed: %s' % str(e))
                _logger.error('YouTube upload failed for %s: %s', record.name, str(e))

    def _get_attachment_file_path(self):
        """Get the file path of the attachment."""
        self.ensure_one()
        attachment = self.attachment_id
        if not attachment.datas:
            raise UserError('Attachment has no data.')
        # Save attachment to temporary file
        import base64
        import tempfile
        file_data = base64.b64decode(attachment.datas)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.' + attachment.mimetype.split('/')[-1])
        temp_file.write(file_data)
        temp_file.close()
        return temp_file.name

    @api.model
    def _run_scheduled_uploads(self):
        """Cron job to process scheduled uploads."""
        now = fields.Datetime.now()
        scheduled_uploads = self.search([
            ('state', '=', 'scheduled'),
            ('schedule_date', '<=', now),
        ])
        for upload in scheduled_uploads:
            upload.action_upload_now()
