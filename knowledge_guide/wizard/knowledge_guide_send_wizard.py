# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class KnowledgeGuideSendWizard(models.TransientModel):
    """Wizard used to send a guide by email.

    Allows the user to:
    - pick recipients (partners with an email address)
    - freely edit the subject and the body of the message
    - send the email with the guide link (tracked when available)
    """
    _name = 'knowledge.guide.send.wizard'
    _description = 'Knowledge Guide Email Wizard'

    book_id = fields.Many2one(
        'knowledge.guide.book',
        string='Guide',
        required=True,
        readonly=True,
        help='The book/guide to be sent.',
    )

    partner_ids = fields.Many2many(
        'res.partner',
        'knowledge_guide_send_wizard_partner_rel',
        'wizard_id',
        'partner_id',
        string='Recipients',
        required=True,
        domain=[('email', '!=', False)],
        help='Select the contacts that will receive the email.',
    )

    subject = fields.Char(
        string='Subject',
        required=True,
        help='Email subject.',
    )

    body = fields.Html(
        string='Message',
        required=True,
        sanitize=False,
        help='Email body (editable).',
    )

    @api.model
    def default_get(self, fields_list):
        """Pre-fill the wizard from the email template."""
        res = super().default_get(fields_list)

        book_id = self.env.context.get('default_book_id')
        if not book_id:
            book_id = self.env.context.get('active_id')

        if book_id:
            book = self.env['knowledge.guide.book'].browse(book_id)
            res['book_id'] = book.id

            template = self.env.ref(
                'knowledge_guide.email_template_send_guide',
                raise_if_not_found=False,
            )
            if template:
                rendered_subject = template._render_field('subject', [book.id])
                res['subject'] = rendered_subject[book.id]

                rendered_body = template._render_field('body_html', [book.id])
                res['body'] = rendered_body[book.id]

        return res

    def action_send(self):
        """Send the email to the selected recipients."""
        self.ensure_one()

        if not self.partner_ids:
            raise UserError(_('Please select at least one recipient.'))

        MailMail = self.env['mail.mail']

        for partner in self.partner_ids:
            if not partner.email:
                continue

            mail_values = {
                'subject': self.subject,
                'body_html': self.body,
                'email_to': partner.email_formatted,
                'email_from': self.env.user.email_formatted,
                'author_id': self.env.user.partner_id.id,
                'auto_delete': False,
                'is_notification': True,
            }

            mail = MailMail.sudo().create(mail_values)
            mail.send()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _(
                    'The guide has been sent to %s recipient(s).',
                    len(self.partner_ids),
                ),
                'type': 'success',
                'sticky': False,
            }
        }
