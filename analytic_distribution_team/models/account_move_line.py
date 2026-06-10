# -*- coding: utf-8 -*-
# Copyright 2025 Lune Makers SL
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html).
from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_analytic_distribution_arguments(self, root_plans):
        """Add the sales team to the arguments used by the analytic
        distribution matcher. This is the hook officially exposed by
        Odoo for this purpose.
        """
        arguments = super()._get_analytic_distribution_arguments(root_plans)
        arguments['team_id'] = self.move_id.team_id.id
        return arguments
