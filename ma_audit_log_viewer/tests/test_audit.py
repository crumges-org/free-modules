from datetime import timedelta
from odoo import fields as F
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAuditLog(TransactionCase):

    def setUp(self):
        super().setUp()
        self.partner_model = self.env['ir.model'].search(
            [('model', '=', 'res.partner')], limit=1
        )
        self.name_field = self.env['ir.model.fields'].search([
            ('model_id', '=', self.partner_model.id),
            ('name', '=', 'name'),
        ], limit=1)

    def _make_config(self, **kwargs):
        vals = {
            'model_id': self.partner_model.id,
            'field_ids': [(4, self.name_field.id)],
        }
        vals.update(kwargs)
        return self.env['audit.config'].create(vals)

    def test_log_line_create(self):
        line = self.env['audit.log.line'].sudo().create({
            'model_name': 'res.partner',
            'res_id': 1,
            'res_name': 'Test Partner',
            'field_name': 'name',
            'field_label': 'Name',
            'old_value': 'Old',
            'new_value': 'New',
            'user_id': self.env.uid,
            'operation': 'write',
        })
        self.assertEqual(line.model_name, 'res.partner')
        self.assertEqual(line.operation, 'write')

    def test_config_create(self):
        config = self._make_config(retention_days=30)
        self.assertEqual(config.model_name, 'res.partner')
        self.assertTrue(config.active)

    def test_get_active_config(self):
        config = self._make_config()
        found = self.env['audit.config']._get_active_config('res.partner')
        self.assertEqual(found.id, config.id)

    def test_write_creates_log(self):
        self._make_config()
        self.env['audit.config']._setup_audit_hooks()
        partner = self.env['res.partner'].create({'name': 'Before'})
        count_before = self.env['audit.log.line'].search_count([])
        partner.write({'name': 'After'})
        self.assertEqual(self.env['audit.log.line'].search_count([]), count_before + 1)
        log = self.env['audit.log.line'].search(
            [('res_id', '=', partner.id), ('operation', '=', 'write')], limit=1
        )
        self.assertEqual(log.old_value, 'Before')
        self.assertEqual(log.new_value, 'After')

    def test_write_no_change_not_logged(self):
        self._make_config()
        self.env['audit.config']._setup_audit_hooks()
        partner = self.env['res.partner'].create({'name': 'Same'})
        count = self.env['audit.log.line'].search_count([])
        partner.write({'name': 'Same'})
        self.assertEqual(self.env['audit.log.line'].search_count([]), count)

    def test_create_creates_log(self):
        self._make_config()
        self.env['audit.config']._setup_audit_hooks()
        partner = self.env['res.partner'].create({'name': 'New Partner'})
        log = self.env['audit.log.line'].search([
            ('res_id', '=', partner.id), ('operation', '=', 'create')
        ], limit=1)
        self.assertTrue(log)
        self.assertEqual(log.new_value, 'New Partner')
        self.assertEqual(log.old_value, '')

    def test_unlink_creates_log(self):
        self._make_config()
        self.env['audit.config']._setup_audit_hooks()
        partner = self.env['res.partner'].create({'name': 'To Delete'})
        partner_id = partner.id
        partner.unlink()
        log = self.env['audit.log.line'].search([
            ('res_id', '=', partner_id), ('operation', '=', 'unlink')
        ], limit=1)
        self.assertTrue(log)
        self.assertEqual(log.old_value, 'To Delete')
        self.assertEqual(log.new_value, '')

    def test_alert_sends_mail(self):
        admin = self.env.ref('base.user_admin')
        self._make_config(
            notify_user_id=admin.id,
            notify_on_field_ids=[(4, self.name_field.id)],
        )
        self.env['audit.config']._setup_audit_hooks()
        partner = self.env['res.partner'].create({'name': 'Before Alert'})
        mail_count = self.env['mail.mail'].search_count([])
        partner.write({'name': 'After Alert'})
        self.assertGreater(self.env['mail.mail'].search_count([]), mail_count)

    def test_cron_deletes_old_logs(self):
        config = self._make_config(retention_days=10)
        old = self.env['audit.log.line'].sudo().create({
            'config_id': config.id,
            'model_name': 'res.partner',
            'res_id': 1,
            'res_name': 'Test',
            'field_name': 'name',
            'field_label': 'Name',
            'old_value': 'A',
            'new_value': 'B',
            'operation': 'write',
            'date': F.Datetime.now() - timedelta(days=20),
        })
        new = self.env['audit.log.line'].sudo().create({
            'config_id': config.id,
            'model_name': 'res.partner',
            'res_id': 1,
            'res_name': 'Test',
            'field_name': 'name',
            'field_label': 'Name',
            'old_value': 'B',
            'new_value': 'C',
            'operation': 'write',
            'date': F.Datetime.now() - timedelta(days=5),
        })
        self.env['audit.config']._cron_delete_old_logs()
        self.assertFalse(self.env['audit.log.line'].search([('id', '=', old.id)]))
        self.assertTrue(self.env['audit.log.line'].search([('id', '=', new.id)]))
