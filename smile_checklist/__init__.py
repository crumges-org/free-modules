# -*- coding: utf-8 -*-
# (C) 2020 Smile (<http://www.smile.fr>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from . import models
from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG


def uninstall_hook(env):
    # Set the MODULE_UNINSTALL_FLAG in the context
    context_flags = {
        MODULE_UNINSTALL_FLAG: True,
        "purge": True,
    }
    # Search for the fields and unlink them
    env['ir.model.fields'].search([
        (
            'name', 'in', [
                "x_checklist_task_instance_ids",
                "x_checklist_progress_rate",
                "x_checklist_progress_rate_mandatory"
            ]
        )
    ]).with_context(**context_flags).unlink()
