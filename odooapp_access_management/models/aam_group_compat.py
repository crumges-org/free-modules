"""Group membership, expressed once.

Odoo 18 and 19 disagree about *where* the transitive closure of group
membership lives, and the disagreement is invisible at the call site - which is
exactly why it is worth a module of its own rather than twenty inline edits.

**Odoo 18 materialises the closure.** ``GroupsImplied.write`` runs a
``WITH RECURSIVE`` query on every change to ``users`` or ``implied_ids`` and
inserts the transitive result straight into ``res_groups_users_rel``
(``addons/base/models/res_users.py:1494-1514``); ``UsersImplied.write`` does the
mirror image, folding ``trans_implied_ids`` into ``groups_id`` (``:1620-1627``).
That is why core's own ``_get_group_ids`` is the one-liner
``return self.groups_id._ids`` (``:1225``) - the column already *is* the
closure.

**Odoo 19 stopped materialising it** and added computed fields instead:
``res.groups.all_user_ids`` is "users and implied users" while ``user_ids`` is
"users **explicitly** in this group" (``addons/base/models/res_groups.py:17-19``),
and ``res.users.group_ids`` is documented as the explicit set (``res_users.py:257``).

So on 18 ``group.users`` already means what 19 calls ``all_user_ids``. The
mapping is correct, but it is *not* self-evident from reading either line - hence
this file.

One consequence has no workaround and is documented at the call sites: on 18 a
user added directly to a group and a user who merely implies it produce the
identical row, so the direct-vs-implied distinction is **unrecoverable**. Core
hits the same wall in ``_remove_group`` (``res_users.py:1555-1558``) and settles
for a heuristic with a comment admitting the compromise. See
``aam.rule.include_implied_groups``.
"""


def group_members(groups):
    """Every user these groups reach, implied membership included.

    Odoo 19: ``groups.all_user_ids``.
    """
    return groups.users


def group_direct_members(groups):
    """The members of these groups.

    Odoo 19 can answer "direct members only" (``groups.user_ids``); Odoo 18
    cannot, because the closure is materialised into the same relation. This
    returns the same set as :func:`group_members`, and callers that offered the
    distinction must say so rather than quietly return the wrong answer.
    """
    return groups.users


def user_groups(user):
    """Every group this user holds, implied groups included.

    Odoo 19: ``user.all_group_ids``.
    """
    return user.groups_id


def group_with_implied(group):
    """The group plus every group it implies, reflexively.

    Odoo 19's ``all_implied_ids`` is reflexive; Odoo 18's ``trans_implied_ids``
    is not (``res_users.py:1474`` computes it as
    ``implied_ids | implied_ids.trans_implied_ids``), so the union is required.
    """
    return group | group.trans_implied_ids


def group_area(group):
    """The heading the user form files this group under.

    Odoo 19 groups by ``res.groups.privilege``; that model does not exist on 18,
    where the equivalent is the group's ``ir.module.category``.
    """
    return group.category_id
