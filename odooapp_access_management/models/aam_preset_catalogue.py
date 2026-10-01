"""The preset catalogue: ready-made profiles for the apps people actually run.

Presets live here as plain Python rather than as XML data records because a data
file would have to reference ``sale.order``, ``mrp.production`` and friends by
external id, and those do not exist in a base-only database - the module would
fail to install. Everything here is resolved against the *live* registry when a
preset is applied, so a preset silently degrades to whatever the database has
and the wizard says out loud which parts it had to skip.

Adding a preset means adding one entry below. It shows up in the Preset Library,
in the wizard and in the tests without another line of code.

Field and model names were checked against the Odoo 18 source, which matters
more than it sounds: this is the 18 branch, so the model is ``hr.contract`` (19
renamed it ``hr.version``) and the computed wage lives on ``hr.contract`` too,
not on ``hr.employee`` as it does in 19. ``maintenance.request`` names its
responsible ``technician_user_id``, not ``user_id``. A wrong name here does not
raise - it silently drops the line, so the preset still advertises a restriction
count while applying nothing - which is why
``test_l9_catalogue_names_resolve_where_the_app_is_installed`` asserts every
reference resolves in a database where the app is installed. It is the only
thing that catches this class of mistake.
"""

#: Groupings shown in the Preset Library and used as the wizard's category
#: filter. Ordered the way the Odoo apps menu orders them, not alphabetically.
PRESET_CATEGORIES = [
    ('general', 'Cross-App'),
    ('sales', 'Sales'),
    ('crm', 'CRM'),
    ('purchase', 'Purchase'),
    ('inventory', 'Inventory'),
    ('manufacturing', 'Manufacturing'),
    ('accounting', 'Accounting'),
    ('hr', 'Human Resources'),
    ('project', 'Project & Services'),
    ('pos', 'Point of Sale'),
    ('helpdesk', 'Helpdesk'),
]

#: Each preset becomes one profile plus one rule.
#:
#: Recognised keys: ``name``, ``category``, ``apps`` (human-readable, for the
#: card), ``description``, ``rule`` (global toggles on ``aam.rule``),
#: ``model_lines``, ``field_lines``, ``search_lines``, ``chatter_lines`` (all
#: keyed by ``model``, plus ``field`` for field lines) and ``menu_lines``
#: (keyed by ``xmlid``).
PRESETS = {

    # -- Cross-app: work on any database, including a base-only one ---------

    'auditor': {
        'name': "Read-only Auditor",
        'category': 'general',
        'apps': "Any database",
        'description': "Can see everything they already have access to, but cannot "
                       "change anything, export data, or post to the chatter.",
        'rule': {
            'readonly_user': True,
            'hide_export': True,
            'hide_send_message': True,
            'hide_log_note': True,
            'disable_developer_mode': True,
        },
    },
    'contractor': {
        'name': "External Contractor",
        'category': 'general',
        'apps': "Any database",
        'description': "Locked down hard: read-only, no export, no import, no chatter, "
                       "no developer mode, no app management.",
        'rule': {
            'readonly_user': True,
            'hide_export': True,
            'hide_import': True,
            'hide_chatter': True,
            'disable_developer_mode': True,
            'restrict_module_manage': True,
            'hide_custom_filter': True,
        },
    },
    'no_data_out': {
        'name': "No Data Leaves the System",
        'category': 'general',
        'apps': "Any database",
        'description': "Keeps full working access but closes every route data takes on "
                       "its way out: export, spreadsheet, print and attachments.",
        'rule': {
            'hide_export': True,
            'hide_spreadsheet': True,
            'hide_print': True,
            'hide_attachments': True,
            'restrict_rpc': True,
        },
    },
    'no_settings': {
        'name': "No Settings, No Apps",
        'category': 'general',
        'apps': "Any database",
        'description': "Hides the Settings app and blocks installing, updating or "
                       "removing modules. The usual first rule on any shared database.",
        'rule': {
            'restrict_module_manage': True,
            'disable_developer_mode': True,
        },
        'menu_lines': [
            {'xmlid': 'base.menu_administration', 'include_children': True},
        ],
    },
    'contact_privacy': {
        'name': "Contact Data Privacy",
        'category': 'general',
        'apps': "Any database",
        'description': "Masks personal contact details on partners - email, phone "
                       "and VAT - server-side, so an export or an RPC call sees the "
                       "mask too.",
        'rule': {},
        'field_lines': [
            {'model': 'res.partner', 'field': 'email', 'mask_type': 'email'},
            {'model': 'res.partner', 'field': 'phone', 'mask_type': 'phone'},
            {'model': 'res.partner', 'field': 'vat', 'mask_type': 'partial'},
        ],
    },

    # -- Sales --------------------------------------------------------------

    'sales_own': {
        'name': "Sales Rep - Own Records",
        'category': 'sales',
        'apps': "Sales, CRM",
        'description': "Sees only the orders and leads they are the salesperson for, "
                       "and cannot delete them.",
        'rule': {},
        'model_lines': [
            {'model': 'sale.order', 'no_unlink': True, 'hide_duplicate': True,
             'domain': "[('user_id', '=', user.id)]",
             'domain_on_read': True, 'domain_on_write': True, 'domain_on_unlink': True},
            {'model': 'crm.lead', 'no_unlink': True,
             'domain': "[('user_id', '=', user.id)]",
             'domain_on_read': True, 'domain_on_write': True, 'domain_on_unlink': True},
        ],
    },
    'sales_no_discount': {
        'name': "Sales Rep - Fixed Pricing",
        'category': 'sales',
        'apps': "Sales",
        'description': "Can quote and sell, but cannot move a unit price or hand out a "
                       "discount - the two fields are read-only, enforced on write.",
        'rule': {},
        'field_lines': [
            {'model': 'sale.order.line', 'field': 'price_unit', 'readonly': True},
            {'model': 'sale.order.line', 'field': 'discount', 'readonly': True},
        ],
    },
    'sales_manager_nodelete': {
        'name': "Sales Manager - No Delete",
        'category': 'sales',
        'apps': "Sales",
        'description': "Full sales access with deletion blocked, so a cancelled order "
                       "stays on the record instead of disappearing.",
        'rule': {},
        'model_lines': [
            {'model': 'sale.order', 'no_unlink': True, 'hide_archive': True},
            {'model': 'sale.order.line', 'no_unlink': True},
        ],
    },
    'sales_viewer': {
        'name': "Sales Viewer",
        'category': 'sales',
        'apps': "Sales",
        'description': "Read-only on the sales pipeline: no editing, no export, no "
                       "spreadsheet - for finance or management who only need to look.",
        'rule': {},
        'model_lines': [
            {'model': 'sale.order', 'readonly_model': True, 'hide_export': True,
             'hide_spreadsheet': True, 'hide_action_button': True},
        ],
        'chatter_lines': [
            {'model': 'sale.order', 'hide_send_message': True, 'hide_log_note': True},
        ],
    },

    # -- CRM ----------------------------------------------------------------

    'crm_own_pipeline': {
        'name': "CRM Rep - Own Pipeline",
        'category': 'crm',
        'apps': "CRM",
        'description': "Only their own leads and opportunities, with no way to delete "
                       "one or reassign it out of sight.",
        'rule': {},
        'model_lines': [
            {'model': 'crm.lead', 'no_unlink': True, 'hide_duplicate': True,
             'domain': "[('user_id', '=', user.id)]",
             'domain_on_read': True, 'domain_on_write': True, 'domain_on_unlink': True},
        ],
        'field_lines': [
            {'model': 'crm.lead', 'field': 'user_id', 'readonly': True},
        ],
    },
    'crm_no_lead_export': {
        'name': "CRM - No Lead Export",
        'category': 'crm',
        'apps': "CRM",
        'description': "The leaver's-USB-stick rule: the pipeline stays fully usable, "
                       "but contact details cannot be exported out of it.",
        'rule': {},
        'model_lines': [
            {'model': 'crm.lead', 'hide_export': True, 'hide_spreadsheet': True},
        ],
        'field_lines': [
            {'model': 'crm.lead', 'field': 'email_from', 'no_export': True},
            {'model': 'crm.lead', 'field': 'phone', 'no_export': True},
        ],
    },

    # -- Purchase -----------------------------------------------------------

    'purchase_requester': {
        'name': "Purchase Requester - Own Orders",
        'category': 'purchase',
        'apps': "Purchase",
        'description': "Raises requests for quotation and follows their own orders, "
                       "without touching anybody else's or deleting one.",
        'rule': {},
        'model_lines': [
            {'model': 'purchase.order', 'no_unlink': True,
             'domain': "[('user_id', '=', user.id)]",
             'domain_on_read': True, 'domain_on_write': True, 'domain_on_unlink': True},
        ],
    },
    'purchase_nodelete': {
        'name': "Purchase - No Delete",
        'category': 'purchase',
        'apps': "Purchase",
        'description': "Full purchasing access with deletion blocked on orders and "
                       "vendor bills, which is what an audit trail needs.",
        'rule': {},
        'model_lines': [
            {'model': 'purchase.order', 'no_unlink': True},
            {'model': 'purchase.order.line', 'no_unlink': True},
        ],
    },

    # -- Inventory ----------------------------------------------------------

    'warehouse': {
        'name': "Warehouse Operator",
        'category': 'inventory',
        'apps': "Inventory",
        'description': "Handles stock, but cannot see pricing or delete anything.",
        'rule': {'hide_export': True, 'restrict_module_manage': True},
        'model_lines': [
            {'model': 'stock.picking', 'no_unlink': True},
            {'model': 'product.template', 'no_create': True, 'no_unlink': True},
        ],
        'field_lines': [
            {'model': 'product.template', 'field': 'list_price', 'invisible': True},
            {'model': 'product.template', 'field': 'standard_price', 'invisible': True},
            # Hiding a field does not hide what is computed *from* it:
            # `tax_string` renders the sales price with tax, so leaving it would
            # put the number back on the form under another label.
            {'model': 'product.template', 'field': 'tax_string', 'invisible': True},
        ],
    },
    'receiving_clerk': {
        'name': "Receiving Clerk",
        'category': 'inventory',
        'apps': "Inventory",
        'description': "Receives and moves goods. Cannot create products, cannot run an "
                       "inventory adjustment, cannot delete a transfer.",
        'rule': {},
        'model_lines': [
            {'model': 'stock.picking', 'no_unlink': True, 'hide_duplicate': True},
            {'model': 'stock.quant', 'readonly_model': True},
            {'model': 'product.template', 'no_create': True, 'no_unlink': True},
        ],
    },
    'inventory_no_cost': {
        'name': "Inventory - Hide Costs",
        'category': 'inventory',
        'apps': "Inventory",
        'description': "Everything in Inventory except money: cost and sales price are "
                       "removed from the view and from exports.",
        'rule': {},
        'field_lines': [
            {'model': 'product.template', 'field': 'standard_price', 'invisible': True},
            {'model': 'product.template', 'field': 'list_price', 'invisible': True},
            {'model': 'product.template', 'field': 'tax_string', 'invisible': True},
            {'model': 'product.product', 'field': 'standard_price', 'invisible': True},
        ],
    },

    # -- Manufacturing ------------------------------------------------------

    'mrp_operator': {
        'name': "Manufacturing Operator",
        'category': 'manufacturing',
        'apps': "Manufacturing",
        'description': "Works the orders assigned to them on the shop floor. Bills of "
                       "material are read-only and nothing can be deleted.",
        'rule': {},
        'model_lines': [
            {'model': 'mrp.production', 'no_unlink': True, 'hide_duplicate': True,
             'domain': "[('user_id', '=', user.id)]",
             'domain_on_read': True, 'domain_on_write': True, 'domain_on_unlink': True},
            {'model': 'mrp.bom', 'readonly_model': True},
        ],
    },
    'mrp_bom_readonly': {
        'name': "Manufacturing - Read-only BoM",
        'category': 'manufacturing',
        'apps': "Manufacturing",
        'description': "Plan and run production freely, but the bills of material - the "
                       "part everybody downstream depends on - cannot be edited.",
        'rule': {},
        'model_lines': [
            {'model': 'mrp.bom', 'readonly_model': True, 'hide_action_button': True},
            {'model': 'mrp.bom.line', 'readonly_model': True},
        ],
    },

    # -- Accounting ---------------------------------------------------------

    'accountant_nodelete': {
        'name': "Accountant - No Delete",
        'category': 'accounting',
        'apps': "Accounting",
        'description': "Full accounting access with deletion blocked, which is what "
                       "most audit regimes actually require.",
        'rule': {'restrict_module_manage': True},
        'model_lines': [
            {'model': 'account.move', 'no_unlink': True},
            {'model': 'account.move.line', 'no_unlink': True},
            {'model': 'account.payment', 'no_unlink': True},
        ],
    },
    'account_viewer': {
        'name': "Accounting Viewer",
        'category': 'accounting',
        'apps': "Accounting",
        'description': "Read-only on journal entries and payments, with export off - "
                       "for an external accountant or an internal reviewer.",
        'rule': {},
        'model_lines': [
            {'model': 'account.move', 'readonly_model': True, 'hide_export': True},
            {'model': 'account.payment', 'readonly_model': True, 'hide_export': True},
        ],
    },
    'account_no_bank_details': {
        'name': "Accounting - No Bank Details",
        'category': 'accounting',
        'apps': "Accounting",
        'description': "Masks account numbers on partner bank records, so the people "
                       "who reconcile payments never see the full number.",
        'rule': {},
        'field_lines': [
            {'model': 'res.partner.bank', 'field': 'acc_number',
             'mask_type': 'partial', 'no_export': True},
            # And the same number again: `sanitized_acc_number` is a stored
            # compute holding the full account number with the spaces stripped.
            # Masking only `acc_number` left it readable over RPC and export -
            # hiding a field does not hide what is computed from it.
            {'model': 'res.partner.bank', 'field': 'sanitized_acc_number',
             'mask_type': 'partial', 'no_export': True},
        ],
    },

    # -- Human Resources ----------------------------------------------------

    'hr_self_service': {
        'name': "Employee Self-Service",
        'category': 'hr',
        'apps': "Employees",
        'description': "Sees their own employee record and nobody else's, and cannot "
                       "create or delete one.",
        'rule': {},
        'model_lines': [
            {'model': 'hr.employee', 'no_create': True, 'no_unlink': True,
             'domain': "[('user_id', '=', user.id)]",
             'domain_on_read': True, 'domain_on_write': True, 'domain_on_unlink': True},
        ],
    },
    'hr_no_salary': {
        'name': "HR Officer - No Salary Data",
        'category': 'hr',
        'apps': "Employees",
        'description': "Day-to-day HR work without pay: wages are hidden on the "
                       "employee's contract record and excluded from exports.",
        'rule': {},
        'field_lines': [
            {'model': 'hr.contract', 'field': 'wage', 'invisible': True},
            # The computed one as well: hiding `wage` alone leaves a field that
            # renders the same number. On Odoo 18 both live on `hr.contract` -
            # `hr.employee` has no `contract_wage` here (that is a 19 arrangement).
            {'model': 'hr.contract', 'field': 'contract_wage', 'invisible': True},
        ],
    },
    'recruiter_own': {
        'name': "Recruiter - Own Openings",
        'category': 'hr',
        'apps': "Recruitment",
        'description': "Only the applicants they are recruiting for, with candidate "
                       "email and phone excluded from exports.",
        'rule': {},
        'model_lines': [
            {'model': 'hr.applicant', 'no_unlink': True,
             'domain': "[('user_id', '=', user.id)]",
             'domain_on_read': True, 'domain_on_write': True, 'domain_on_unlink': True},
        ],
        'field_lines': [
            {'model': 'hr.applicant', 'field': 'email_from', 'no_export': True},
        ],
    },
    'expense_own': {
        'name': "Expenses - Own Only",
        'category': 'hr',
        'apps': "Expenses",
        'description': "Files and follows their own expenses. Cannot see a colleague's, "
                       "cannot delete a submitted one.",
        'rule': {},
        'model_lines': [
            {'model': 'hr.expense', 'no_unlink': True,
             'domain': "[('employee_id.user_id', '=', user.id)]",
             'domain_on_read': True, 'domain_on_write': True, 'domain_on_unlink': True},
        ],
    },
    'fleet_viewer': {
        'name': "Fleet Viewer",
        'category': 'hr',
        'apps': "Fleet",
        'description': "Looks up vehicles and drivers without being able to change a "
                       "contract, a cost or an odometer reading.",
        'rule': {},
        'model_lines': [
            {'model': 'fleet.vehicle', 'readonly_model': True, 'hide_export': True},
        ],
    },
    'maintenance_technician': {
        'name': "Maintenance Technician",
        'category': 'hr',
        'apps': "Maintenance",
        'description': "Works the maintenance requests assigned to them and cannot "
                       "delete one or edit the equipment master data.",
        'rule': {},
        'model_lines': [
            {'model': 'maintenance.request', 'no_unlink': True,
             'domain': "[('technician_user_id', '=', user.id)]",
             'domain_on_read': True, 'domain_on_write': True, 'domain_on_unlink': True},
            {'model': 'maintenance.equipment', 'readonly_model': True},
        ],
    },

    # -- Project & Services -------------------------------------------------

    'project_member': {
        'name': "Project Member - Own Tasks",
        'category': 'project',
        'apps': "Project",
        'description': "Sees the tasks they are assigned to. Projects themselves are "
                       "read-only, so nobody reshapes the plan by accident.",
        'rule': {},
        'model_lines': [
            {'model': 'project.task', 'no_unlink': True,
             'domain': "[('user_ids', 'in', user.id)]",
             'domain_on_read': True, 'domain_on_write': True, 'domain_on_unlink': True},
            {'model': 'project.project', 'readonly_model': True},
        ],
    },
    'timesheet_own': {
        'name': "Timesheets - Own Entries",
        'category': 'project',
        'apps': "Timesheets",
        'description': "Logs and edits their own time only. Somebody else's timesheet "
                       "is not readable, let alone editable.",
        'rule': {},
        'model_lines': [
            {'model': 'account.analytic.line', 'no_unlink': True,
             'domain': "[('user_id', '=', user.id)]",
             'domain_on_read': True, 'domain_on_write': True, 'domain_on_unlink': True},
        ],
    },

    # -- Point of Sale ------------------------------------------------------

    'pos_cashier': {
        'name': "POS Cashier - No Config",
        'category': 'pos',
        'apps': "Point of Sale",
        'description': "Runs the till. Cannot change a point-of-sale configuration, "
                       "reopen a closed session or delete an order.",
        'rule': {},
        'model_lines': [
            {'model': 'pos.config', 'readonly_model': True, 'hide_action_button': True},
            {'model': 'pos.session', 'no_create': True, 'no_unlink': True},
            {'model': 'pos.order', 'no_unlink': True, 'hide_duplicate': True},
        ],
    },

    # -- Helpdesk (Enterprise) ----------------------------------------------

    'helpdesk_agent': {
        'name': "Helpdesk Agent - Own Tickets",
        'category': 'helpdesk',
        'apps': "Helpdesk",
        'description': "Works the tickets assigned to them, and cannot delete one or "
                       "export the customer list behind them.",
        'rule': {},
        'model_lines': [
            {'model': 'helpdesk.ticket', 'no_unlink': True, 'hide_export': True,
             'domain': "[('user_id', '=', user.id)]",
             'domain_on_read': True, 'domain_on_write': True, 'domain_on_unlink': True},
        ],
    },
}

#: Keys of ``PRESETS`` entries that carry model-scoped restriction lines, mapped
#: to the ``aam.rule`` one2many they populate.
LINE_FIELDS = {
    'model_lines': 'model_line_ids',
    'field_lines': 'field_line_ids',
    'search_lines': 'search_line_ids',
    'chatter_lines': 'chatter_line_ids',
    'menu_lines': 'menu_line_ids',
}
