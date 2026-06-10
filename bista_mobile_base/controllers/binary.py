from odoo import http
import logging
from odoo.addons.web.controllers.binary import Binary
from odoo.addons.bista_mobile_base.common import validate_token
from odoo.http import request
from odoo.tools import str2bool
from odoo.tools.image import image_guess_size_from_field_name


_logger = logging.getLogger(__name__)


class Binary(Binary):

    @validate_token
    @http.route(
        [
            "/api/v1/web/image",
            "/api/v1/web/image/<string:xmlid>",
            "/api/v1/web/image/<string:xmlid>/<string:filename>",
            "/api/v1/web/image/<string:xmlid>/<int:width>x<int:height>",
            "/api/v1/web/image/<string:xmlid>/<int:width>x<int:height>/<string:filename>",
            "/api/v1/web/image/<string:model>/<int:id>/<string:field>",
            "/api/v1/web/image/<string:model>/<int:id>/<string:field>/<string:filename>",
            "/api/v1/web/image/<string:model>/<int:id>/<string:field>/<int:width>x<int:height>",
            "/api/v1/web/image/<string:model>/<int:id>/<string:field>/<int:width>x<int:height>/<string:filename>",
            "/api/v1/web/image/<int:id>",
            "/api/v1/web/image/<int:id>/<string:filename>",
            "/api/v1/web/image/<int:id>/<int:width>x<int:height>",
            "/api/v1/web/image/<int:id>/<int:width>x<int:height>/<string:filename>",
            "/api/v1/web/image/<int:id>-<string:unique>",
            "/api/v1/web/image/<int:id>-<string:unique>/<string:filename>",
            "/api/v1/web/image/<int:id>-<string:unique>/<int:width>x<int:height>",
            "/api/v1/web/image/<int:id>-<string:unique>/<int:width>x<int:height>/<string:filename>",
        ],
        type="http",
        auth="public",
    )
    def download_content_image(
        self,
        xmlid=None,
        model="ir.attachment",
        id=None,
        field="raw",
        filename_field="name",
        filename=None,
        mimetype=None,
        unique=False,
        download=False,
        width=0,
        height=0,
        crop=False,
        access_token=None,
        nocache=False,
    ):
        record_id = request.env[model].sudo().browse(id)
        if record_id.exists() and record_id._fields.get("image_1920") and not record_id.image_1920:
            # Use the ratio of the requested field_name instead of "raw"
            if (int(width), int(height)) == (0, 0):
                width, height = image_guess_size_from_field_name(field)
            record = request.env.ref('bista_mobile_base.mobile_app_image_placeholder', raise_if_not_found=False)
            if record:
                record = record.sudo()
                stream = request.env['ir.binary']._get_image_stream_from(
                    record, 'raw', width=int(width), height=int(height), crop=crop,
                )
                stream.public = False

                send_file_kwargs = {'as_attachment': str2bool(download)}
                if unique:
                    send_file_kwargs['immutable'] = True
                    send_file_kwargs['max_age'] = http.STATIC_CACHE_LONG
                if nocache:
                    send_file_kwargs['max_age'] = None
                return stream.get_response(**send_file_kwargs)
            else:
                _logger.info("Mobile App default placeholder not found")

        return self.content_image(
            xmlid=xmlid,
            model=model,
            id=id,
            field=field,
            filename_field=filename_field,
            filename=filename,
            mimetype=mimetype,
            unique=unique,
            download=download,
            width=width,
            height=height,
            crop=crop,
            access_token=access_token,
            nocache=nocache,
        )
