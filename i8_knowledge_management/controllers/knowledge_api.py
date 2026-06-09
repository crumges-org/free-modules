from odoo import http
from odoo.http import request

class KnowledgeController(http.Controller):

    @http.route('/knowledge/article/<int:article_id>/messages', type='json', auth='user')
    def get_article_messages(self, article_id):
        article = request.env['knowledge.article'].browse(article_id).exists()
        if not article:
            return []

        messages = article.message_ids.filtered(lambda m: m.message_type == 'comment').sorted('date')
        return [{
            'id': msg.id,
            'parent_id': msg.parent_id.id if msg.parent_id and msg.parent_id.id in messages.ids else None,
            'author': msg.author_id.name,
            'body': msg.body,
            'date': msg.date.strftime('%Y-%m-%d %H:%M:%S'),
        } for msg in messages]

    @http.route(['/knowledge/article/<string:token>'], type='http', auth='public', website=True)
    def article_public_view(self, token, **kwargs):
        article = request.env['knowledge.article'].sudo().search([('share_token', '=', token)], limit=1)
        if not article:
            return request.not_found()

        return request.render('i8_knowledge_management.article_public_template', {
            'article': article,
        })

    @http.route('/knowledge/article/increment_view', type='json', auth='user')
    def increment_view(self, article_id):
        article = request.env['knowledge.article'].sudo().browse(article_id)
        if article.exists():
            article.views_count += 1
            request.env['knowledge.article.view.log'].sudo().create({
                'article_id': article.id,
                'user_id': request.env.user.id
            })

    @http.route('/knowledge/article/toggle_like', type='json', auth='user')
    def toggle_like(self, article_id):
        article = request.env['knowledge.article'].sudo().browse(article_id)
        user = request.env.user

        if not user.exists() or not user.id:
            return {'error': 'Invalid user'}

        if not article.exists():
            return {'error': 'Invalid article'}

        if user in article.liked_by_ids:
            article.liked_by_ids = [(3, user.id)]
        else:
            article.liked_by_ids = [(4, user.id)]

        return {'new_count': len(article.liked_by_ids.ids)}
