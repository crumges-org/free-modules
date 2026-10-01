#!/usr/bin/env bash
# Fail if this checkout uses the OTHER Odoo serie's API.
#
# This is the cheapest guard against the worst failure mode in a two-serie repo:
# v19 code reaching the 18 branch (or the reverse) through a merge, producing a
# module that installs cleanly and silently enforces nothing. For an access
# module that is worse than a crash - an administrator marks a field frozen, the
# form shows it frozen, and the write goes through.
#
# Under a second, no server, no database. Run it before every push.
#
# One file, identical on both branches: it reads the serie out of __manifest__.py
# rather than being configured, so it never conflicts on a merge.
set -u
cd "$(dirname "$0")/.."

SERIE=$(grep -oE "'version':[[:space:]]*'[0-9]+" __manifest__.py | grep -oE '[0-9]+$')
[ -n "$SERIE" ] || { echo "check_api: could not read the serie from __manifest__.py"; exit 2; }

if [ "$SERIE" = "18" ]; then
    # Constructs that exist only in Odoo 19.
    BAD='models\.Constraint|from odoo\.fields import Domain|all_user_ids|all_implied_ids|all_group_ids|privilege_id|res\.groups\.privilege|hr\.version|@web_tour/tour_utils|run: *"canvasNotEmpty"|properties\.base\.definition|o_selection_box|CLEAR-CACHES'
else
    # Constructs that exist only in Odoo 18.
    BAD='_sql_constraints|osv\.expression|check_field_access_rights|trans_implied_ids|hr\.contract|@web_tour/tour_service/tour_utils|o_list_selection_box'
fi

# Prose that *names* the other version is the point of this port, not a mistake.
# Three exclusions, in order:
#   - models/aam_group_compat.py exists to document both dialects side by side;
#   - a line that opens as a comment (#, //, *, <!--);
#   - a line where the identifier sits in backticks, which is how every docstring
#     and comment here refers to code it is talking about rather than calling.
#     No real code line in this module carries a backtick.
HITS=$(grep -rnE "$BAD" \
        --include='*.py' --include='*.xml' --include='*.js' \
        models wizards controllers tests views security static 2>/dev/null \
      | grep -v 'aam_group_compat.py' \
      | grep -vE ':[0-9]+: *(#|\*|//|<!--)' \
      | grep -v '`')

if [ -n "$HITS" ]; then
    echo "check_api: this is an Odoo $SERIE checkout, but it contains foreign-serie API:"
    echo "$HITS"
    echo
    echo "If a hit is prose explaining the difference, put the identifier in"
    echo "backticks; if it is real code, it does not belong on this branch."
    exit 1
fi
echo "check_api: clean for Odoo $SERIE"
