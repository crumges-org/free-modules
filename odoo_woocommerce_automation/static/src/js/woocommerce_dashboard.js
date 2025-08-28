/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted, useState } from "@odoo/owl";

class WooCommerceDashboard extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        this.state = useState({
            loading: false,
            dashboardData: null,
            error: null
        });
        
        onMounted(() => {
            this.loadDashboardData();
        });
    }
    
    async loadDashboardData() {
        this.state.loading = true;
        try {
            const result = await this.rpc("/woocommerce/dashboard/data", {});
            if (result.status === 'success') {
                this.state.dashboardData = result.data;
            } else {
                this.state.error = result.message;
            }
        } catch (error) {
            this.state.error = error.message;
        } finally {
            this.state.loading = false;
        }
    }
    
    async testConnection() {
        this.state.loading = true;
        try {
            const result = await this.rpc("/woocommerce/api/status", {});
            if (result.status === 'success') {
                this.notification.add("Connection test successful!", {
                    type: "success",
                    sticky: false,
                });
            } else {
                this.notification.add(result.message, {
                    type: "danger",
                    sticky: false,
                });
            }
        } catch (error) {
            this.notification.add("Connection test failed", {
                type: "danger",
                sticky: false,
            });
        } finally {
            this.state.loading = false;
        }
    }
    
    async syncData(syncType) {
        this.state.loading = true;
        try {
            const result = await this.rpc("/woocommerce/api/sync", { sync_type: syncType });
            if (result.status === 'success') {
                this.notification.add(result.message, {
                    type: "success",
                    sticky: false,
                });
                // Reload dashboard data
                await this.loadDashboardData();
            } else {
                this.notification.add(result.message, {
                    type: "danger",
                    sticky: false,
                });
            }
        } catch (error) {
            this.notification.add("Sync failed", {
                type: "danger",
                sticky: false,
            });
        } finally {
            this.state.loading = false;
        }
    }
    
    getStatusClass(status) {
        switch (status) {
            case 'connected':
                return 'success';
            case 'error':
                return 'danger';
            case 'disconnected':
                return 'warning';
            default:
                return 'info';
        }
    }
    
    getStatusIcon(status) {
        switch (status) {
            case 'connected':
                return 'fa-check-circle';
            case 'error':
                return 'fa-times-circle';
            case 'disconnected':
                return 'fa-exclamation-triangle';
            default:
                return 'fa-question-circle';
        }
    }
}

WooCommerceDashboard.template = 'woocommerce.Dashboard';
WooCommerceDashboard.props = {};

registry.category("actions").add("woocommerce_dashboard", WooCommerceDashboard); 