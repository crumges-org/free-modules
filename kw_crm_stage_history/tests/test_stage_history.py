from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestStageHistory(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.History = cls.env['kw.crm.stage.history']
        cls.stage_new = cls.env.ref('crm.stage_lead1')
        cls.stage_qualified = cls.env.ref('crm.stage_lead2')
        cls.stage_proposition = cls.env.ref('crm.stage_lead3')
        cls.stage_won = cls.env.ref('crm.stage_lead4')

    def _create_lead(self, name='Test Lead', stage=None):
        vals = {
            'name': name,
            'type': 'opportunity',
        }
        if stage:
            vals['stage_id'] = stage.id
        return self.env['crm.lead'].create(vals)

    def test_history_created_on_lead_create(self):
        lead = self._create_lead()
        history = self.History.search([('lead_id', '=', lead.id)])
        self.assertEqual(len(history), 1)
        self.assertFalse(history.stage_from_id)
        self.assertEqual(history.stage_to_id, self.stage_new)
        self.assertTrue(history.date_in)
        self.assertFalse(history.date_out)
        self.assertEqual(history.date_in_by_id, self.env.user)

    def test_history_on_stage_change(self):
        lead = self._create_lead()
        lead.stage_id = self.stage_qualified
        history = self.History.search(
            [('lead_id', '=', lead.id)], order='date_in asc')
        self.assertEqual(len(history), 2)

        first = history[0]
        self.assertTrue(first.date_out)
        self.assertEqual(first.date_out_by_id, self.env.user)

        second = history[1]
        self.assertEqual(second.stage_from_id, first.stage_to_id)
        self.assertEqual(second.stage_to_id, self.stage_qualified)
        self.assertFalse(second.date_out)

    def test_multiple_stage_changes(self):
        lead = self._create_lead()
        lead.stage_id = self.stage_qualified
        lead.stage_id = self.stage_proposition
        lead.stage_id = self.stage_won

        history = self.History.search(
            [('lead_id', '=', lead.id)], order='date_in asc')
        self.assertEqual(len(history), 4)

        for rec in history[:-1]:
            self.assertTrue(rec.date_out)
        self.assertFalse(history[-1].date_out)

        self.assertEqual(
            history[1].stage_from_id, history[0].stage_to_id)
        self.assertEqual(
            history[2].stage_from_id, history[1].stage_to_id)
        self.assertEqual(
            history[3].stage_from_id, history[2].stage_to_id)

    def test_time_diff_computed(self):
        now = fields.Datetime.now()
        lead = self._create_lead()
        history = self.History.search([('lead_id', '=', lead.id)])

        history.write({
            'date_in': now - timedelta(days=2, hours=5),
            'date_out': now,
        })
        history.flush_recordset()
        history.invalidate_recordset()

        self.assertEqual(history.day_diff, 2)
        self.assertAlmostEqual(history.time_diff, 5.0, places=1)
        self.assertAlmostEqual(
            history.total_time_diff, 53.0, places=1)

    def test_time_diff_no_date_out(self):
        lead = self._create_lead()
        history = self.History.search([('lead_id', '=', lead.id)])
        self.assertEqual(history.day_diff, 0)
        self.assertEqual(history.time_diff, 0.0)
        self.assertEqual(history.total_time_diff, 0.0)

    def test_lead_delete_cascades_history(self):
        lead = self._create_lead()
        lead.stage_id = self.stage_qualified
        lead_id = lead.id
        lead.unlink()
        history = self.History.search([('lead_id', '=', lead_id)])
        self.assertFalse(history)

    def test_one2many_relation(self):
        lead = self._create_lead()
        lead.stage_id = self.stage_qualified
        self.assertEqual(len(lead.kw_stage_history_ids), 2)

    def test_create_with_specific_stage(self):
        lead = self._create_lead(stage=self.stage_proposition)
        history = self.History.search([('lead_id', '=', lead.id)])
        self.assertEqual(len(history), 1)
        self.assertEqual(
            history.stage_to_id, self.stage_proposition)

    def test_no_history_on_non_stage_write(self):
        lead = self._create_lead()
        initial_count = self.History.search_count(
            [('lead_id', '=', lead.id)])
        lead.name = 'Updated Name'
        after_count = self.History.search_count(
            [('lead_id', '=', lead.id)])
        self.assertEqual(initial_count, after_count)
