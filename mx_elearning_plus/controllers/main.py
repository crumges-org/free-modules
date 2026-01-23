# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import http, tools, _
from odoo.http import request
from odoo.tools import plaintext2html
from odoo.addons.website_slides.controllers.main import WebsiteSlides


class SlideController(http.Controller):

    @http.route(['/website/publish/slide'], type='json', auth="user", website=True)
    def publish(self, id):
        slide_id = request.env['slide.slide'].browse(id)
        return bool(slide_id.website_published)
    
    @http.route(['/slides/slide/mx/like'], type='json', auth="public", website=True)
    def slide_like_dislike(self, slide_id):
        slide = request.env['slide.slide'].browse(slide_id)
        return {
            'user_vote': slide.user_vote,
            'likes': tools.misc.format_decimalized_number(slide.likes),
            'dislikes': tools.misc.format_decimalized_number(slide.dislikes),
        }
    
    def _portal_post_has_content(self, res_model, res_id, message, attachment_ids=None, **kw):
        """ Tells if we can effectively post on the model based on content. """
        return bool(message) or bool(attachment_ids)
    
    @http.route(['/mail/slide/comment'], type='json', methods=['POST'], auth='public', website=True)
    def portal_chatter_post(self, res_model, res_id, message, attachment_ids=None, attachment_tokens=None, **kw):
        """Create a new `mail.message` with the given `message` and/or `attachment_ids` and return new message values."""
        if not self._portal_post_has_content(res_model, res_id, message,
                                             attachment_ids=attachment_ids, attachment_tokens=attachment_tokens,
                                             **kw):
            return
        res_id = int(res_id)
        result = {'default_message': message}
        # message is received in plaintext and saved in html
        if message:
            message = plaintext2html(message)
        vals = ({
            'email_from': request.env.user.email_formatted,
            'author_id': request.env.user.partner_id.id,
            'message_type':'comment',
            'body':message if message else '',
            'subtype_id': 1,
            'model':res_model,
            'res_id': res_id,
            # 'attachment_ids': False,
            'record_name': (request.env[str(res_model)].browse(res_id)).name
        })
        message=request.env['mail.message'].sudo().create(vals)
        result.update({'default_message_id': message.id})

        if attachment_ids:
            # sudo write the attachment to bypass the read access
            # verification in mail message
            record = request.env[res_model].browse(res_id)
            message_values = {'res_id': res_id, 'model': res_model}
            attachments = record._message_post_process_attachments([], attachment_ids, message_values)

            if attachments.get('attachment_ids'):
                message.sudo().write(attachments)

            result.update({'default_attachment_ids': message.attachment_ids.sudo().read(['id', 'name', 'mimetype', 'file_size', 'access_token'])})
        return result
        
class WebsiteSlideController(WebsiteSlides):

    @http.route('/slides/slide/like', type='json', auth="public", website=True)
    def slide_like(self, slide_id, upvote):
        res = super(WebsiteSlideController, self).slide_like(slide_id, upvote)
        return res