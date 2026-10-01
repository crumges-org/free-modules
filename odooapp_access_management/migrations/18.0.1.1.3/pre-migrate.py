"""Drop the stored user-form extension that still names `aam_session_epoch`.

18.0.1.1.3 removes that field (force logout now revokes sessions through
`res.device` instead of changing every user's session token). On Odoo 18 the
upgrade then fails before this module's views are reloaded: loading
`security/aam_groups.xml` rewrites the generated `res.users.groups` view, and
Odoo validates the whole user form - including the old, still-stored
`view_users_form_aam`, which references the field that no longer exists.

Deleting that view and its external id lets `views/res_users_views.xml`
recreate it from the current file later in the same upgrade. Only this module's
own views that mention the field are touched, and nothing inherits from them.
"""


def migrate(cr, version):
    if not version:
        return
    cr.execute("""
        SELECT v.id
          FROM ir_ui_view v
          JOIN ir_model_data d ON d.model = 'ir.ui.view' AND d.res_id = v.id
         WHERE d.module = 'odooapp_access_management'
           AND v.arch_db::text LIKE '%%aam_session_epoch%%'
    """)
    view_ids = [row[0] for row in cr.fetchall()]
    if not view_ids:
        return
    cr.execute("DELETE FROM ir_ui_view WHERE id = ANY(%s)", [view_ids])
    cr.execute(
        "DELETE FROM ir_model_data WHERE model = 'ir.ui.view' AND res_id = ANY(%s)",
        [view_ids])
