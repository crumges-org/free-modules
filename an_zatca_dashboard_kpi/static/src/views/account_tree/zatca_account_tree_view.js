/** @odoo-module **/

import { registry } from "@web/core/registry";
import { accountMoveUploadListView } from "@account/views/account_move_list/account_move_list_view";
import { ZatcaAccountTreeRenderer } from "./zatca_account_tree_renderer";

export const zatcaAccountTreeView = {
    ...accountMoveUploadListView,
    Renderer: ZatcaAccountTreeRenderer,
};

// Replace the existing account_tree view
registry.category("views").add("account_tree", zatcaAccountTreeView, { force: true });
