from odoo import http
import logging
from odoo.http import request, Response
from odoo import SUPERUSER_ID, _, http
from odoo.tools.misc import file_path

from odoo.addons.bista_mobile_base.controllers.binary import Binary
# from odoo.addons.bista_driver_app.controllers.fleet_api import validate_fleet_token
from odoo.addons.bista_mobile_base.common import validate_token
from odoo.addons.base.models.assetsbundle import ANY_UNIQUE

_logger = logging.getLogger(__name__)



class Binary(Binary):

    @validate_token
    @http.route(['/api/web/content',
        '/api/web/content/<string:xmlid>',
        '/api/web/content/<string:xmlid>/<string:filename>',
        '/api/web/content/<int:id>',
        '/api/web/content/<int:id>/<string:filename>',
        '/api/web/content/<string:model>/<int:id>/<string:field>',
        '/api/web/content/<string:model>/<int:id>/<string:field>/<string:filename>'], 
        type='http', auth="public", csrf=False)

    def fleet_content_common(self, xmlid=None, model='ir.attachment', id=None, field='raw',
                       filename=None, filename_field='name', mimetype=None, unique=False,
                       download=False, access_token=None, nocache=False):

        return self.content_common(xmlid=xmlid, model=model, id=id, field=field,
                       filename=filename, filename_field=filename_field, mimetype=mimetype, unique=unique,
                       download=download, access_token=access_token, nocache=nocache)
    @http.route(['/api/web/image',
        '/api/web/image/<string:xmlid>',
        '/api/web/image/<string:xmlid>/<string:filename>',
        '/api/web/image/<string:xmlid>/<int:width>x<int:height>',
        '/api/web/image/<string:xmlid>/<int:width>x<int:height>/<string:filename>',
        '/api/web/image/<string:model>/<int:id>/<string:field>',
        '/api/web/image/<string:model>/<int:id>/<string:field>/<string:filename>',
        '/api/web/image/<string:model>/<int:id>/<string:field>/<int:width>x<int:height>',
        '/api/web/image/<string:model>/<int:id>/<string:field>/<int:width>x<int:height>/<string:filename>',
        '/api/web/image/<int:id>',
        '/api/web/image/<int:id>/<string:filename>',
        '/api/web/image/<int:id>/<int:width>x<int:height>',
        '/api/web/image/<int:id>/<int:width>x<int:height>/<string:filename>',
        '/api/web/image/<int:id>-<string:unique>',
        '/api/web/image/<int:id>-<string:unique>/<string:filename>',
        '/api/web/image/<int:id>-<string:unique>/<int:width>x<int:height>',
        '/api/web/image/<int:id>-<string:unique>/<int:width>x<int:height>/<string:filename>'], type='http', auth="public")
    def fleet_content_image(self, xmlid=None, model='ir.attachment', id=None, field='raw',
                      filename_field='name', filename=None, mimetype=None, unique=False,
                      download=False, width=0, height=0, crop=False, access_token=None,
                      nocache=False):
        return self.download_content_image(self,xmlid=xmlid, model='ir.attachment', id=id, field=field,
                      filename_field=filename_field, filename=filename, mimetype=mimetype, unique=unique,
                      download=download, width=width, height=height, crop=crop, access_token=access_token,
                      nocache=nocache)
        # return self.content_image(xmlid=xmlid, model='ir.attachment', id=id, field=field,
        #               filename_field=filename_field, filename=filename, mimetype=mimetype, unique=unique,
        #               download=download, width=width, height=height, crop=crop, access_token=access_token,
        #               nocache=nocache)

    @http.route([
        '/api/shipment/assets/<string:filename>'], type='http', auth="public")
    def shipment_content_assets(self, filename=None, unique=ANY_UNIQUE, nocache=False, assets_params=None):
        if unique== '_______':
            assets_params = assets_params or {}
            assert isinstance(assets_params, dict)
            debug_assets = unique == 'debug'
            if unique in ('any', '%'):
                unique = ANY_UNIQUE
            attachment = None
            if unique != 'debug':
                url = f'{filename}'
                assert not '%' in url
                domain = [
                    ('public', '=', True),
                    ('url', '!=', False),
                    ('url', '=like', url),
                    ('res_model', '=', 'ir.ui.view'),
                    ('res_id', '=', 0),
                    ('create_uid', '=', SUPERUSER_ID),
                ]
                attachment = request.env['ir.attachment'].sudo().search(domain, limit=1)
            if not attachment:
                # try to generate one
                try:
                    if filename.endswith('.map'):
                        _logger.error(".map should have been generated through debug assets, (version %s most likely outdated)", unique)
                        raise request.not_found()
                    bundle_name, rtl, asset_type = request.env['ir.asset']._parse_bundle_name(filename, debug_assets)
                    css = asset_type == 'css'
                    js = asset_type == 'js'
                    bundle = request.env['ir.qweb']._get_asset_bundle(
                        bundle_name,
                        css=css,
                        js=js,
                        debug_assets=debug_assets,
                        rtl=rtl,
                        assets_params=assets_params,
                    )
                    # check if the version matches. If not, redirect to the last version
                    if not debug_assets and unique != ANY_UNIQUE and unique != bundle.get_version(asset_type):
                        return request.redirect(bundle.get_link(asset_type))
                    if css and bundle.stylesheets:
                        attachment = bundle.css()
                    elif js and bundle.javascripts:
                        attachment = bundle.js()
                except ValueError as e:
                    _logger.warning("Parsing asset bundle %s has failed: %s", filename, e)
                    raise request.not_found() from e
            if not attachment:
                raise request.not_found()
            stream = request.env['ir.binary']._get_stream_from(attachment, 'raw', filename)
            send_file_kwargs = {'as_attachment': False}
            if unique and unique != 'debug':
                send_file_kwargs['immutable'] = True
                send_file_kwargs['max_age'] = http.STATIC_CACHE_LONG
            if nocache:
                send_file_kwargs['max_age'] = None

            return stream.get_response(**send_file_kwargs)
        else:
            res = super(Binary, self).content_assets(filename, unique, nocache, assets_params)
            return res