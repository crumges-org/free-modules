# Access Management for Odoo

Advance Access Management: user access rights and role based access control for
menus, models, fields, records, buttons, search and chatter.

Technical name: `odooapp_access_management` · Odoo **18.0** (Community and Enterprise) · OPL-1

Control what every user can see and do — menus, models, fields, records, buttons,
search and chatter — from one place, per user, per group, or through a reusable
profile.

## The three things this does differently

**It enforces rather than hides.** Field and record restrictions are applied in
`read()` and the ORM access layer, not only in the view. Because `web_read` and
`web_search_read` both route through `read()`, one override covers the browser
and XML-RPC alike. Modules that only rewrite the view arch leave the API wide
open.

**It tells you why.** The Access Explainer names the rule behind every effect and
the path it took to reach that user — *"via profile 'Warehouse Operator', through
group 'Warehouse Crew'"* — alongside Odoo's own ACL rows and record rules. When
someone reports a missing button, you get the cause, not just the state.

**It survives an upgrade.** Rules export by external ID and technical name, never
by database id, with a name fallback for groups a customer created themselves.
Import runs a dry run first and lists every reference that will not resolve
before writing anything.

## You cannot lock yourself out

- Administrators are never restricted unless you explicitly turn that protection off.
- A master switch (`aam.enabled`) makes every rule inert without uninstalling.
- Rules are validated on save; one that would lock every administrator out is refused.

If you do disable administrator protection and lock yourself out, recover with:

```python
# odoo-bin shell -c <conf> -d <db>
env['ir.config_parameter'].set_param('aam.enabled', '0')
env.cr.commit()
```

## Architecture

Rules are never evaluated one at a time at runtime. `aam.policy` compiles every
rule that applies to a user into a single dict cached in the registry per
`(uid, company, lang, debug)`, so each enforcement hook is a dictionary lookup.
The cache is dropped whenever any `aam.*` record changes. Time-windowed rules sit
in a separate live overlay so they cannot poison it. The cached policy is frozen,
so a hook that tries to mutate it fails loudly rather than corrupting every other
user's policy.

**Precedence: deny wins.** Booleans OR together, hidden-id sets union, domains
AND together. `priority` only breaks ties between restrictions of the same kind —
it can never turn a denial back into a permission.

### Where enforcement hooks in

| Restriction | Hook |
|---|---|
| View arch | `get_view` on `base`, after `super()` |
| Toolbar, reports, actions | `ir.actions.actions.get_bindings` |
| Menus | `ir.ui.menu._load_menus_blacklist` |
| Model CRUD | `ir.model.access._get_allowed_models` |
| Record domains | `ir.rule._compute_domain` (+ `_compute_domain_keys`) |
| Field metadata | `_has_field_access` |
| Field values / masking | `read()` |
| Access checks | `_check_access` |
| Login | `res.users._get_login_domain` |
| Developer mode | `ir.http._handle_debug` |

Two Odoo 18 specifics this depends on, both verified against the source:

- `get_view` splits into a **user-agnostic cached** phase (`_get_view_cache`,
  keyed without user or groups) and a **per-user** phase. All per-user arch
  injection happens after `super()` returns, so the template cache stays intact
  and one user's restrictions cannot reach another.
- `ir.ui.menu._visible_menu_ids` is cached on the *group set*, so per-user menu
  hiding must use `_load_menus_blacklist` instead — it is called inside
  `load_menus`, which is uid-keyed.

## Layout

```
models/          rule + line models, the policy compiler, dashboard data
models/inherits/ one file per enforcement hook
wizards/         explainer, JSON import/export, presets, groups→Excel
controllers/     impersonation endpoints
static/src/      policy service, UI patches, dashboard, access map
tests/           tagged by parity-matrix id (A1, C14, L4, …)
```

## Development

Targets Odoo 18 **Community** (`E:\Program Files\Odoo18community\server`), which
has its own Python. Uses an isolated conf rather than touching the server's:

```bash
export MSYS2_ARG_CONV_EXCL='*'
PY="E:/Program Files/Odoo19community/python/python.exe"
BIN="E:/Program Files/Odoo19community/server/odoo-bin"

# install / upgrade
"$PY" "$BIN" -c dev/aam_dev.conf -d aam19_dev -u odooapp_access_management \
  --stop-after-init --logfile dev/run.log

# run the tests
"$PY" "$BIN" -c dev/aam_dev.conf -d aam19_test -i odooapp_access_management \
  --test-enable --test-tags /odooapp_access_management \
  --stop-after-init --logfile dev/test.log
```

The addons path points at `d:\odoo_online\aam_addons`, a directory holding a
junction to this module — an addons-path entry must be a directory whose
*children* are modules.

Note that Odoo **appends** to `--logfile`, so use a fresh filename per run.
