# -*- coding: utf-8 -*-

from datetime import timedelta
from odoo import models, fields, _, api
from odoo.exceptions import UserError


class SoltApiConnector(models.Model):
    _inherit = 'solt.api.connector'

    orders_count = fields.Integer(
        string='Total Orders',
        compute='_compute_orders_count',
        store=False,
    )

    orders_today_count = fields.Integer(
        string='Today Orders',
        compute='_compute_orders_today_count',
        store=False,
    )
    show_button_wh_tn = fields.Boolean(compute="_compute_show_button_wh_tn")

    def toggle_active(self):
        res = super().toggle_active()
        # Propagate active state to children
        for connector in self.with_context(active_test=False):
            for company in connector.company_ids:
                connector = connector.with_company(company)
                # Deactivate configured webhooks
                domain = [('connector_id', '=', connector.id), ('company_id', '=', company.id)]

                try:
                    if connector.active:
                        domain.append(('active', '=', False))
                        wh_ids = self.env['solt.register.webhook'].with_context(active_test=False).search(domain)
                        wh_ids.with_context(wh_action='public').toggle_active()
                    else:
                        wh_ids = self.env['solt.register.webhook'].search(domain)
                        wh_ids.with_context(wh_action='delete').toggle_active()
                except Exception as e:
                    raise UserError(f"Error: {str(e)}")
        return res

    def _compute_orders_count(self):
        """
        Compute number of orders for all companies associated with the connector
        """
        for connector in self:
            connector.orders_count = self.env['sale.order'].search_count([
                ('order_number', 'not in', ['', False]),
                ('company_id', 'in', connector.company_ids.ids),
            ])

    def _compute_orders_today_count(self):
        """
        Compute number of orders created today for all companies associated with the connector
        """
        for connector in self:
            connector.orders_today_count = self.env['sale.order'].search_count([
                ('order_number', 'not in', ['', False]),
                ('company_id', 'in', connector.company_ids.ids),
                ('create_date', '>=', fields.Datetime.now() - timedelta(days=1)),
            ])

    def unlink(self):
        for connector in self:
            if connector.active:
                raise UserError(_('Cannot delete the API connector while active.'))
            # Delete webhooks configuration
            wh_ids = self.env['solt.register.webhook'].with_context(active_test=False).search([('connector_id', '=', connector.id)])
            wh_ids.unlink()
        return super(SoltApiConnector, self).unlink()

    @api.depends_context('company')
    @api.depends('active', 'company_ids')
    def _compute_show_button_wh_tn(self):
        for connector in self:
            _has_webhook, wh_ids = connector._has_webhook_tn(self.env.company)
            if connector.active and not _has_webhook:
                connector.show_button_wh_tn = True
            else:
                connector.show_button_wh_tn = False

    def _has_webhook_tn(self, company):
        """
        Verifica si el conector tiene creado los webhooks de Tiendanube
        :param company:
        :return: Tuple(boolean, recordset)
        """
        self.ensure_one()
        wh_ids = self.env['solt.register.webhook'].with_company(company).with_context(active_test=False).search([
            ('company_id', '=', company.id), ('connector_id', '=', self.id)
        ])
        return bool(wh_ids), wh_ids

    def action_create_tn_webhooks(self):
        self.ensure_one()
        automation_ids = self.automation_ids.filtered(lambda a: a.trigger == 'on_webhook' and a.event)
        to_create = []
        company = self.env.company
        for automation in automation_ids:
            to_create.append(automation._prepare_tn_webhooks(company))
        if to_create:
            self.env['solt.register.webhook'].with_company(company).create(to_create)
