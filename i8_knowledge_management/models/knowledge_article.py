from odoo import models, fields, api, exceptions,_
from odoo.exceptions import UserError
from bs4 import BeautifulSoup
import uuid

class KnowledgeArticle(models.Model):
    _name = 'knowledge.article'
    _description = 'Knowledge Article'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    _sql_indexes = [
        ("parent_id", "btree(parent_id)"),
        ("active_is_published", "btree(active, is_published)"),
        ("write_date_idx", "btree(write_date)"),
        ("create_date_idx", "btree(create_date)"),
    ]

    name = fields.Char(required=True, tracking=True)
    display_name = fields.Char(compute='_compute_display_name', compute_sudo=True)
    content = fields.Html('Content')
    category_id = fields.Many2one('knowledge.category', string='Category', tracking=True)
    tag_ids = fields.Many2many('knowledge.tag', string='Tags')
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    version = fields.Integer(default=1)
    is_published = fields.Boolean(default=True, tracking=True)
    author_id = fields.Many2one('res.users', string='Author', default=lambda self: self.env.user)
    editor_ids = fields.Many2many('res.users', 'knowledge_article_editor_rel', 'article_id', 'user_id')
    viewer_ids = fields.Many2many('res.users', 'knowledge_article_viewer_rel', 'article_id', 'user_id')
    is_locked = fields.Boolean(default=False)
    parent_id = fields.Many2one('knowledge.article', string="Parent Article", ondelete="restrict")
    child_ids = fields.One2many('knowledge.article', 'parent_id', string="Child Articles")
    active = fields.Boolean(default=True)

    # Access rights
    view_everyone = fields.Boolean(string="View: Everyone", default=True, help="Applies to this article and cascades to children unless overridden.")
    view_user_ids = fields.Many2many(
        'res.users',
        'knowledge_article_view_users_rel',
        'article_id', 'user_id',
        string='View: Specific Users',
        domain="[('employee_id', '!=', False), ('employee_id.active', '=', True)]",
        help="Inherited from parent if not changed."
    )
    view_department_ids = fields.Many2many(
        'hr.department',
        'knowledge_article_view_dept_rel',
        'article_id', 'department_id',
        string='View: Specific Departments',
        help="Inherited from parent if not changed."
    )
    edit_everyone = fields.Boolean(string="Edit: Everyone", default=True, help="Applies to this article and cascades to children unless overridden.")
    edit_user_ids = fields.Many2many(
        'res.users',
        'knowledge_article_edit_users_rel',
        'article_id', 'user_id',
        string='Edit: Specific Users',
        domain="[('employee_id', '!=', False), ('employee_id.active', '=', True)]",
        help="Inherited from parent if not changed."
    )
    edit_department_ids = fields.Many2many(
        'hr.department',
        'knowledge_article_edit_dept_rel',
        'article_id', 'department_id',
        string='Edit: Specific Departments',
        help="Inherited from parent if not changed."
    )

    access_inherited = fields.Boolean(string="Access Inherited", compute='_compute_access_inherited', store=False)
    version_ids = fields.One2many('knowledge.article.version', 'article_id', string="Versions")

    share_token = fields.Char(string="Share Token", readonly=True, index=True)
    views_count = fields.Integer(string="Views", readonly=True)
    liked_by_ids = fields.Many2many(
        "res.users", string="Liked By", relation="knowledge_article_likes_rel", readonly=True
    )
    likes_count = fields.Integer(string="Likes", compute="_compute_likes_count", store=True)

    @api.depends('liked_by_ids')
    def _compute_likes_count(self):
        for rec in self:
            rec.likes_count = len(rec.liked_by_ids)

    def _compute_display_name(self):
        for article in self:
            names = []
            current = article
            while current:
                names.append(current.name or '')
                current = current.parent_id
            article.display_name = " / ".join(reversed(names))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Versioning + Author
            vals['version'] = 1
            if 'author_id' not in vals:
                vals['author_id'] = self.env.uid

            if vals.get('content'):
                vals['content'] = self.clean_article_content(vals['content'])

            # Share token
            if not vals.get('share_token'):
                vals['share_token'] = uuid.uuid4().hex

        articles = super().create(vals_list)

        # Access inheritance from parent
        for article in articles:
            if article.parent_id:
                parent = article.parent_id
                article.sudo().write({
                    'view_everyone': parent.view_everyone,
                    'view_user_ids': [(6, 0, parent.view_user_ids.ids)],
                    'view_department_ids': [(6, 0, parent.view_department_ids.ids)],
                    'edit_everyone': parent.edit_everyone,
                    'edit_user_ids': [(6, 0, parent.edit_user_ids.ids)],
                    'edit_department_ids': [(6, 0, parent.edit_department_ids.ids)]
                })

        return articles

    def write(self, vals):
        if "tag_ids" in vals:
            tag_ids = vals["tag_ids"]
            if isinstance(tag_ids, list) and all(isinstance(i, int) for i in tag_ids):
                vals["tag_ids"] = [[6, 0, tag_ids]]
            elif isinstance(tag_ids, list) and len(tag_ids) == 3 and tag_ids[0] == 6:
                vals["tag_ids"] = [tag_ids]
            elif isinstance(tag_ids, list) and all(isinstance(cmd, list) and len(cmd) == 3 for cmd in tag_ids):
                pass
            else:
                raise UserError(_("Invalid tag_ids format: %s") % tag_ids)

        restricted_keys = {
            'name', 'content', 'tag_ids', 'parent_id', 'active',
            'is_published', 'share_token'  # add more if needed
        }
        safe_keys = {'liked_by_ids', 'views_count'}

        keys = set(vals.keys())

        if keys & restricted_keys:
            for rec in self:
                if not rec.can_edit():
                    raise UserError(_("You don't have edit access to this article."))

            if 'content' in vals:
                for rec in self:
                    vals['content'] = self.clean_article_content(vals.get('content', ''))
                    rec.env['knowledge.article.version'].create({
                        'article_id': rec.id,
                        'content': rec.content,
                        'version_number': rec.version,
                        'user_id': self.env.uid,
                    })
                    rec.version += 1

            return super().write(vals)

        if keys and keys.issubset(safe_keys):
            return super().write(vals)

        return super().write(vals)

    def unlink(self):
        for article in self:
            if article.is_published and not self.env.user.has_group('base.group_system'):
                raise UserError("Published articles cannot be deleted. Please archive them instead.")
            if not self.env.user.has_group('base.group_system'):
                raise exceptions.AccessError("Only admins can archive articles.")
        return super().unlink()

    def _cascade_archive(self):
        for article in self:
            children = self.search([('parent_id', '=', article.id), ('active', '=', True)])
            children.write({'active': False})

    def _cascade_access_rights(self):
        for article in self:
            children = self.search([('parent_id', '=', article.id)])
            values = {
                'view_everyone': article.view_everyone,
                'view_user_ids': [(6, 0, article.view_user_ids.ids)],
                'view_department_ids': [(6, 0, article.view_department_ids.ids)],
                'edit_everyone': article.edit_everyone,
                'edit_user_ids': [(6, 0, article.edit_user_ids.ids)],
                'edit_department_ids': [(6, 0, article.edit_department_ids.ids)],
            }
            children.write(values)
            children._cascade_access_rights()

    def _compute_access_inherited(self):
        for rec in self:
            if rec.parent_id:
                rec.access_inherited = (
                    rec.view_everyone == rec.parent_id.view_everyone and
                    set(rec.view_user_ids.ids) == set(rec.parent_id.view_user_ids.ids) and
                    set(rec.view_department_ids.ids) == set(rec.parent_id.view_department_ids.ids) and
                    rec.edit_everyone == rec.parent_id.edit_everyone and
                    set(rec.edit_user_ids.ids) == set(rec.parent_id.edit_user_ids.ids) and
                    set(rec.edit_department_ids.ids) == set(rec.parent_id.edit_department_ids.ids)
                )
            else:
                rec.access_inherited = False

    def can_view(self):
        self.ensure_one()
        user = self.env.user

        if user.has_group("base.group_system"):
            return True
        if self.view_everyone or user in self.view_user_ids or self.author_id == user:
            return True
        if user.employee_id and user.employee_id.department_id in self.view_department_ids:
            return True
        return False

    def can_edit(self):
        self.ensure_one()
        user = self.env.user

        if user.has_group("base.group_system"):
            return True
        if self.edit_everyone or self.author_id == user or user in self.edit_user_ids:
            return True
        if user.employee_id and user.employee_id.department_id in self.edit_department_ids:
            return True

        return False

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form' and not self.access_inherited:
            for node in arch.xpath("//group[@name='access_rights']"):
                node.set('string', 'Access Rights (Inherited from Parent Article)')
        return arch, view

    def action_view_versions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Version History',
            'res_model': 'knowledge.article.version',
            'view_mode': 'tree,form',
            'domain': [('article_id', '=', self.id)],
            'context': {'default_article_id': self.id},
            'target': 'current',
            'create': False,
        }

    @api.model
    def search(self, domain=None, offset=0, limit=None, order=None):
        if args and isinstance(args[0], list) and args[0][0] == '__search':
            term = args[0][2]
            args = ['|', ('name', 'ilike', term), ('content', 'ilike', term)]

        records = super().search(domain or [], offset=offset, limit=limit, order=order)
        return records

    def _message_compute_parent_id(self, parent_id):
        if not parent_id:
            return parent_id
        return self.env['mail.message'].search(
            [('id', '=', parent_id),
             ('model', '=', self._name),
             ('res_id', '=', self.id)
            ]).id

    def clean_article_content(self, html):
        soup = BeautifulSoup(html or "", "html.parser")
        for img in soup.find_all("img"):
            if img.get("src", "").startswith("file://"):
                img.decompose()
        return str(soup)

    @api.model
    def _check_read(self, article_id):
        rec = self.browse(article_id)
        rec.check_access_rights('read')
        rec.check_access_rule('read')
        return rec

    @api.model
    def action_toggle_like(self, article_id):
        rec = self.browse(article_id).exists()
        rec.check_access_rights('read')
        rec.check_access_rule('read')

        uid = self.env.user.id
        liked_ids = rec.sudo().liked_by_ids.ids
        you_liked = uid not in liked_ids
        cmd = [(4, uid)] if you_liked else [(3, uid)]

        rec.sudo().write({'liked_by_ids': cmd})
        fresh = self.sudo().browse(rec.id)
        likes_ids = fresh.liked_by_ids.ids
        return {
            'you_liked': you_liked,
            'liked_by_ids': likes_ids,
            'likes_count': len(likes_ids),
        }

    @api.model
    def action_toggle_follow(self, article_id):
        rec = self.browse(article_id).exists()
        rec.check_access_rights('read')
        rec.check_access_rule('read')

        partner = self.env.user.partner_id
        Followers = self.env['mail.followers'].sudo()
        is_following = bool(Followers.search_count([
            ('res_model', '=', 'knowledge.article'),
            ('res_id', '=', rec.id),
            ('partner_id', '=', partner.id),
        ]))
        if is_following:
            rec.sudo().message_unsubscribe(partner_ids=[partner.id])
            following = False
        else:
            rec.sudo().message_subscribe(partner_ids=[partner.id])
            following = True
        return {'following': following}

    @api.model
    def can_archive(self, article_id):
        rec = self.browse(article_id).exists()
        allowed = (rec.create_uid.id == self.env.user.id) or self.env.user.has_group('base.group_system')
        return {'allowed': allowed}

