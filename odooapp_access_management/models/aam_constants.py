"""Shared constants for Advance Access Management.

Kept in one place so the policy compiler, the rule models and the web client
all agree on the vocabulary. The string keys here are part of the exported
JSON rule format (see the import/export wizard), so treat them as stable.
"""

# ---------------------------------------------------------------------------
# Rule targeting
# ---------------------------------------------------------------------------

TARGET_TYPES = [
    ('user', 'Specific Users'),
    ('group', 'Security Groups'),
    ('profile', 'Access Profile'),
    ('all', 'Everyone'),
]

ENFORCEMENT_MODES = [
    ('enforced', 'Enforced'),
    ('ui_only', 'Hide in UI only'),
]

# ---------------------------------------------------------------------------
# Field restrictions
# ---------------------------------------------------------------------------

MASK_TYPES = [
    ('none', 'No Masking'),
    ('full', 'Full (********)'),
    ('partial', 'Partial (end visible)'),
    ('email', 'Email (a***@domain.com)'),
    ('phone', 'Phone (last digits visible)'),
    ('custom', 'Custom Pattern'),
]

# ---------------------------------------------------------------------------
# Button / tab restrictions
# ---------------------------------------------------------------------------

ELEMENT_TYPES = [
    ('button', 'Button'),
    ('tab', 'Tab / Page'),
    ('kanban_link', 'Kanban Link'),
    ('navbar', 'Navbar Button'),
]

# Where a field line applies. 'all' is the ORM-level restriction; the rest are
# arch-only, and the key must match the view_type that get_view receives.
VIEW_SCOPES = [
    ('all', 'All Views'),
    ('form', 'Form'),
    ('list', 'List'),
    ('kanban', 'Kanban'),
    ('search', 'Search'),
]

# ---------------------------------------------------------------------------
# Policy blob section keys
# ---------------------------------------------------------------------------
# The compiled policy is a plain dict with exactly these top-level keys. Every
# enforcement hook reads one of them; nothing else is allowed in, so the blob
# stays JSON-serialisable and safe to hand to the web client.

POLICY_SECTIONS = (
    'globals',   # user-wide toggles           -> dict
    'menus',     # menu ids to hide            -> list[int]
    'models',    # per-model restrictions      -> {model: {...}}
    'fields',    # per-field restrictions      -> {model: {field: {...}}}
    'buttons',   # per-model element hiding    -> {model: [ {...} ]}
    'search',    # per-model search panel      -> {model: {...}}
    'chatter',   # per-model chatter           -> {model: {...}}
    'reports',   # report action ids to hide   -> list[int]
    'actions',   # window/server action ids    -> list[int]
    'views',     # view ids to hide            -> list[int]
)

# Global toggles. Name -> the field name on aam.rule that carries it.
# Order matters only for display.
GLOBAL_FLAGS = (
    'readonly_user',
    'disable_developer_mode',
    'disable_login',
    'restrict_rpc',
    'restrict_module_manage',
    'hide_import',
    'hide_export',
    'hide_spreadsheet',
    'hide_print',
    'hide_action_button',
    'hide_add_property',
    'hide_chatter',
    'hide_send_message',
    'hide_log_note',
    'hide_activity',
    'hide_followers',
    'hide_attachments',
    'hide_filter',
    'hide_group_by',
    'hide_custom_filter',
    'hide_custom_group_by',
    'hide_delete_filter',
    'hide_search_panel',
    'hide_favourite',
)

# ---------------------------------------------------------------------------
# Safety rails
# ---------------------------------------------------------------------------

#: Master switch. Set to '0' to make every rule inert without uninstalling.
PARAM_ENABLED = 'aam.enabled'

#: Opt-in required before a rule may restrict an administrator.
PARAM_ALLOW_RESTRICT_ADMIN = 'aam.allow_restrict_admin'

#: Users that are never restricted while PARAM_ALLOW_RESTRICT_ADMIN is off.
PROTECTED_UIDS = (1, 2)  # __system__ and the default admin

#: Context value that lets ir.rule skip soft clauses on the direct-access path.
#: An object, not True: the caller controls the context (call_kw applies it),
#: and JSON cannot produce this, so a client cannot lift soft restrictions.
SKIP_SOFT = object()

#: Context value marking the reads the policy compiler makes for itself. Nothing
#: in this module looks at it; a module that redacts values read under sudo()
#: leaves a read marked with it alone. An object for the same reason as
#: SKIP_SOFT: a value the browser could send must not switch redaction off.
RAW_VALUES = object()
