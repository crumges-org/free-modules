/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Git Update Widget
 *
 * Provides AJAX functionality for git workspace updates with real-time status
 */
class GitUpdateWidget extends Component {
  setup() {
    this.rpc = useService("rpc");
    this.notification = useService("notification");
    this.state = useState({
      updating: false,
      status: null,
    });
  }

  async updateNow(workspaceId) {
    if (this.state.updating) {
      return;
    }

    this.state.updating = true;

    try {
      const result = await this.rpc("/git/update_now", {
        workspace_id: workspaceId,
      });

      if (result.success) {
        this.notification.add(
          result.message || "Update initiated successfully",
          { type: "success" }
        );
        this.state.status = result.status;
      } else {
        this.notification.add(result.message || "Update failed", {
          type: "danger",
        });
      }
    } catch (error) {
      this.notification.add("Error initiating update: " + error.message, {
        type: "danger",
      });
    } finally {
      this.state.updating = false;
    }
  }

  async refreshStatus(workspaceId) {
    try {
      const result = await this.rpc(`/git/status/${workspaceId}`, {});

      if (result.success) {
        this.state.status = result.status;
        this.notification.add("Status refreshed", { type: "info" });
      }
    } catch (error) {
      console.error("Error refreshing status:", error);
    }
  }
}

GitUpdateWidget.template = "odoo_git_source_manager.GitUpdateWidget";

registry.category("view_widgets").add("git_update_widget", {
  component: GitUpdateWidget,
});

export default GitUpdateWidget;
