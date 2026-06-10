# -*- coding: utf-8 -*-
import json

from odoo import models

# Custom tag developers drop inside any <list> view to render the KPI ribbon.
DASHBOARD_TAG = "listdashboard"


class IrUiViewInherit(models.Model):
    _inherit = "ir.ui.view"

    def _parse_dashboard_card(self, card):
        """Turn a single <card>/<field> element into a card definition dict."""
        return {
            "title": card.get("title") or card.get("string") or "KPI",
            "domain": card.get("domain", "[]"),
            "user_field": card.get("user_field", "user_id"),
            # Any CSS colour (hex / name / rgb). Empty -> auto palette (JS).
            "color": card.get("color") or card.get("colorClass") or "",
            # Optional value aggregation. When "measure" is set the card
            # shows agg(measure) instead of a record count.
            "measure": card.get("measure", ""),
            "aggregate": card.get("aggregate", "sum"),
            # Optional presentation extras.
            "icon": card.get("icon", ""),
            "symbol": card.get("symbol", ""),
        }

    def _extract_dashboard_rows(self, node):
        """Parse the <listdashboard> child of a <list> node into rows of cards.

        Cards may be wrapped in one or more <rowcard> groups - each group is
        rendered as its own horizontal row, stacked vertically. Bare <card>
        elements placed directly under <listdashboard> are grouped into an
        implicit row (backward compatible single-row behaviour).

        Each row is a dict ``{"title": str, "cards": [...]}``. A <rowcard> may
        carry a ``string`` attribute, shown as a heading above that row.

        Returns the list of rows, or None when the tag is absent, and removes
        the custom tag from the tree.
        """
        dashboard_nodes = node.xpath("./%s" % DASHBOARD_TAG)
        if not dashboard_nodes:
            return None

        dashboard_node = dashboard_nodes[0]
        rows = []
        loose = []  # consecutive bare cards not wrapped in a <rowcard>
        # Walk children in document order so rows keep their declared order.
        for child in dashboard_node:
            if child.tag in ("card", "field"):
                loose.append(self._parse_dashboard_card(child))
            elif child.tag == "rowcard":
                if loose:
                    rows.append({"title": "", "cards": loose})
                    loose = []
                rows.append({
                    "title": child.get("string") or child.get("title") or "",
                    "cards": [
                        self._parse_dashboard_card(c)
                        for c in child.xpath("./card | ./field")
                    ],
                })
        if loose:
            rows.append({"title": "", "cards": loose})

        # Drop the custom tag from the tree right now so neither validation
        # nor the rest of post-processing trips over an unknown element.
        node.remove(dashboard_node)
        return rows

    def _postprocess_tag_list(self, node, name_manager, node_info):
        # Runs when the (already combined) arch is served to the client, and
        # the changes made here persist into the arch the browser receives.
        rows = self._extract_dashboard_rows(node)
        if rows is not None:
            node.set("js_class", "ispg_dashboard")
            node.set("ispg_dashboard_data", json.dumps(rows))
        return super()._postprocess_tag_list(node, name_manager, node_info)

    def _validate_tag_list(self, node, name_manager, node_info):
        # Strip the custom tag before the base "allowed list child tags" check
        # so module install/upgrade validation does not reject it.
        for dashboard_node in node.xpath("./%s" % DASHBOARD_TAG):
            node.remove(dashboard_node)
        return super()._validate_tag_list(node, name_manager, node_info)
