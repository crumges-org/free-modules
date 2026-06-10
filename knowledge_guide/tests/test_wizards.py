# -*- coding: utf-8 -*-
from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'knowledge_guide')
class TestViewSourceWizard(TransactionCase):
    """Tests for knowledge.guide.view.source.wizard."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Wizard = cls.env['knowledge.guide.view.source.wizard']
        cls.page = cls.env['knowledge.guide.page'].create({
            'name': 'Source viewer page',
            'category': 'Test',
            'content_html': '<p><strong>raw</strong> content</p>',
        })

    def test_source_code_returns_content_html(self):
        """source_code mirrors the page's original content_html, raw."""
        wizard = self.Wizard.create({'page_id': self.page.id})
        self.assertEqual(wizard.source_code, '<p><strong>raw</strong> content</p>')

    def test_source_code_empty_when_no_content(self):
        """An empty content_html yields an empty source_code, not None."""
        empty_page = self.env['knowledge.guide.page'].create({
            'name': 'Empty', 'category': 'Test',
        })
        wizard = self.Wizard.create({'page_id': empty_page.id})
        self.assertEqual(wizard.source_code, '')


@tagged('post_install', '-at_install', 'knowledge_guide')
class TestSendWizard(TransactionCase):
    """Tests for knowledge.guide.send.wizard."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Wizard = cls.env['knowledge.guide.send.wizard']
        cls.book = cls.env['knowledge.guide.book'].create({
            'name': 'Sendable book',
            'slug': 'sendable-book',
            'is_published': True,
        })
        cls.partner_with_email = cls.env['res.partner'].create({
            'name': 'Recipient One',
            'email': 'recipient@example.com',
        })

    def test_default_get_prefills_subject_and_body(self):
        """default_get pre-fills subject + body from the email template."""
        wizard = self.Wizard.with_context(default_book_id=self.book.id).create({})
        self.assertTrue(wizard.subject)
        self.assertIn(self.book.name, wizard.subject)
        self.assertTrue(wizard.body)

    def test_action_send_without_recipients_raises(self):
        """Sending with no recipient must raise a UserError."""
        wizard = self.Wizard.create({
            'book_id': self.book.id,
            'subject': 'Hello',
            'body': '<p>Body</p>',
        })
        with self.assertRaises(UserError):
            wizard.action_send()

    def test_action_send_creates_mail_records(self):
        """Sending creates one mail.mail per recipient with email."""
        wizard = self.Wizard.create({
            'book_id': self.book.id,
            'subject': 'Hello',
            'body': '<p>Body</p>',
            'partner_ids': [(6, 0, [self.partner_with_email.id])],
        })

        before = self.env['mail.mail'].search_count([
            ('email_to', '=', self.partner_with_email.email_formatted),
            ('subject', '=', 'Hello'),
        ])
        wizard.action_send()
        after = self.env['mail.mail'].search_count([
            ('email_to', '=', self.partner_with_email.email_formatted),
            ('subject', '=', 'Hello'),
        ])
        self.assertEqual(after - before, 1)


@tagged('post_install', '-at_install', 'knowledge_guide')
class TestBookCreateWizard(TransactionCase):
    """Tests for knowledge.guide.book.create.wizard."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Wizard = cls.env['knowledge.guide.book.create.wizard']
        cls.Page = cls.env['knowledge.guide.page']
        cls.Book = cls.env['knowledge.guide.book']

        cls.free_page_a = cls.Page.create({
            'name': 'Free page A', 'category': 'Test',
        })
        cls.free_page_b = cls.Page.create({
            'name': 'Free page B', 'category': 'Test',
        })
        cls.existing_book = cls.Book.create({
            'name': 'Existing book', 'slug': 'existing-book',
        })
        cls.attached_page = cls.Page.create({
            'name': 'Attached page', 'category': 'Test',
            'book_id': cls.existing_book.id,
        })

    def _open_wizard(self, page_ids, name='Tmp', slug='tmp'):
        return self.Wizard.with_context(
            active_model='knowledge.guide.page',
            active_ids=page_ids,
        ).create({'name': name, 'slug': slug})

    def test_default_page_ids_from_context(self):
        """Pages selected in the list view are pre-filled in the wizard."""
        wizard = self._open_wizard([self.free_page_a.id, self.free_page_b.id])
        self.assertEqual(
            set(wizard.page_ids.ids),
            {self.free_page_a.id, self.free_page_b.id},
        )

    def test_default_page_ids_ignores_other_models(self):
        """Wizard opened from another model's selection stays empty."""
        wizard = self.Wizard.with_context(
            active_model='res.partner',
            active_ids=[1, 2, 3],
        ).create({'name': 'Tmp', 'slug': 'tmp'})
        self.assertFalse(wizard.page_ids)

    def test_onchange_name_sets_slug(self):
        """The slug is auto-derived from the name when empty."""
        wizard = self.Wizard.new({'name': 'My Brand New Book!'})
        wizard._onchange_name_set_slug()
        self.assertEqual(wizard.slug, 'my-brand-new-book')

    def test_onchange_name_does_not_overwrite_existing_slug(self):
        """A user-defined slug is never overwritten by the onchange."""
        wizard = self.Wizard.new({'name': 'Anything', 'slug': 'my-slug'})
        wizard._onchange_name_set_slug()
        self.assertEqual(wizard.slug, 'my-slug')

    def test_create_book_attaches_free_pages(self):
        """Creating a book from free pages writes book_id on each."""
        wizard = self._open_wizard(
            [self.free_page_a.id, self.free_page_b.id],
            name='Brand New Book', slug='brand-new-book',
        )

        action = wizard.action_create_book()

        self.assertEqual(action['res_model'], 'knowledge.guide.book')
        new_book = self.Book.browse(action['res_id'])
        self.assertEqual(new_book.name, 'Brand New Book')
        self.assertEqual(new_book.slug, 'brand-new-book')
        self.assertEqual(
            set(new_book.page_ids.ids),
            {self.free_page_a.id, self.free_page_b.id},
        )

    def test_create_book_blocks_when_pages_already_attached(self):
        """Pages already attached to another book block the creation."""
        wizard = self._open_wizard(
            [self.free_page_a.id, self.attached_page.id],
            name='Should Not Pass', slug='nope',
        )

        with self.assertRaises(ValidationError):
            wizard.action_create_book()

        # Free page must remain free, no orphan book is left behind.
        self.assertFalse(self.free_page_a.book_id)
        self.assertFalse(self.Book.search([('slug', '=', 'nope')]))

    def test_create_book_without_pages_raises(self):
        """The wizard refuses to create a book with zero pages."""
        wizard = self.Wizard.create({
            'name': 'Empty', 'slug': 'empty',
        })
        with self.assertRaises(ValidationError):
            wizard.action_create_book()

    def test_blocked_page_ids_compute(self):
        """blocked_page_ids reflects only the pages already in a book."""
        wizard = self._open_wizard([self.free_page_a.id, self.attached_page.id])
        self.assertEqual(wizard.blocked_page_ids.ids, [self.attached_page.id])
        self.assertTrue(wizard.has_blocked)

    def test_blocked_page_ids_empty_when_all_free(self):
        """has_blocked is False when no page has a book_id yet."""
        wizard = self._open_wizard([self.free_page_a.id, self.free_page_b.id])
        self.assertFalse(wizard.blocked_page_ids)
        self.assertFalse(wizard.has_blocked)
