/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";

class WooCommerceSync extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        this.state = useState({
            loading: false,
            progress: 0,
            currentOperation: '',
            syncLog: []
        });
    }
    
    async startSync(syncType) {
        this.state.loading = true;
        this.state.progress = 0;
        this.state.currentOperation = `Starting ${syncType} sync...`;
        this.state.syncLog = [];
        
        try {
            // Start sync process
            const result = await this.rpc("/woocommerce/api/sync", { sync_type: syncType });
            
            if (result.status === 'success') {
                this.state.progress = 100;
                this.state.currentOperation = `${syncType} sync completed successfully`;
                this.addLogEntry('success', `${syncType} sync completed successfully`);
                
                this.notification.add(`${syncType} sync completed`, {
                    type: "success",
                    sticky: false,
                });
            } else {
                this.state.currentOperation = `Sync failed: ${result.message}`;
                this.addLogEntry('error', `Sync failed: ${result.message}`);
                
                this.notification.add(result.message, {
                    type: "danger",
                    sticky: false,
                });
            }
        } catch (error) {
            this.state.currentOperation = `Sync failed: ${error.message}`;
            this.addLogEntry('error', `Sync failed: ${error.message}`);
            
            this.notification.add("Sync failed", {
                type: "danger",
                sticky: false,
            });
        } finally {
            this.state.loading = false;
        }
    }
    
    addLogEntry(type, message) {
        this.state.syncLog.push({
            type: type,
            message: message,
            timestamp: new Date().toLocaleTimeString()
        });
    }
    
    updateProgress(progress, operation) {
        this.state.progress = progress;
        this.state.currentOperation = operation;
    }
    
    clearLog() {
        this.state.syncLog = [];
    }
    
    getLogEntryClass(type) {
        switch (type) {
            case 'success':
                return 'woocommerce-log-entry success';
            case 'error':
                return 'woocommerce-log-entry error';
            case 'warning':
                return 'woocommerce-log-entry warning';
            case 'info':
                return 'woocommerce-log-entry info';
            default:
                return 'woocommerce-log-entry';
        }
    }
    
    getLogEntryIcon(type) {
        switch (type) {
            case 'success':
                return 'fa-check';
            case 'error':
                return 'fa-times';
            case 'warning':
                return 'fa-exclamation-triangle';
            case 'info':
                return 'fa-info';
            default:
                return 'fa-circle';
        }
    }
}

WooCommerceSync.template = 'woocommerce.Sync';
WooCommerceSync.props = {};

registry.category("actions").add("woocommerce_sync", WooCommerceSync); 