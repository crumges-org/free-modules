/** @odoo-module **/

import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import {
    Component,
    onMounted,
    onWillUnmount,
    useState,
} from "@odoo/owl";

const DEFAULT_INTERVAL_MS = 2000;
const HIDDEN_INTERVAL_MULTIPLIER = 4;
const STORAGE_KEY = "server_monitor.odoo_log_prefs";

export class ServerMonitorOdooLog extends Component {
    static template = "server_monitor.OdooLog";

    setup() {
        this.state = useState({
            lastUpdated: "",
            dbName: "",
            error: null,
            isFetching: false,
            logs: {
                available: false,
                path: "",
                lines: [],
                message: "",
            },
            config: {
                intervalMs: DEFAULT_INTERVAL_MS,
            },
            logLines: 200,
            logLinesInput: "200",
            logSearch: "",
        });

        this.applyPreferences();

        this.intervalMs = DEFAULT_INTERVAL_MS;
        this.hiddenIntervalMs = DEFAULT_INTERVAL_MS * HIDDEN_INTERVAL_MULTIPLIER;
        this.timer = null;
        this.searchTimer = null;
        this.handleVisibilityChange = this.handleVisibilityChange.bind(this);

        onMounted(() => {
            this.fetchLogs();
            this.setTimer(this.getEffectiveInterval());
            document.addEventListener("visibilitychange", this.handleVisibilityChange);
        });

        onWillUnmount(() => {
            if (this.timer) {
                clearInterval(this.timer);
            }
            if (this.searchTimer) {
                clearTimeout(this.searchTimer);
            }
            document.removeEventListener("visibilitychange", this.handleVisibilityChange);
        });
    }

    async fetchLogs() {
        if (this.state.isFetching) {
            return;
        }
        this.state.isFetching = true;
        try {
            const data = await rpc("/server_monitor/odoo/logs", {
                log_lines: this.state.logLines,
                log_search: this.state.logSearch,
            });
            if (data && data.error) {
                this.setError(data.error.message || "Unable to fetch logs.");
                return;
            }
            this.clearError();
            this.updateState(data);
        } catch (error) {
            this.setError("Unable to fetch logs. Retrying...");
        } finally {
            this.state.isFetching = false;
        }
    }

    updateState(data) {
        const timestamp = data.timestamp || Date.now() / 1000;
        this.state.lastUpdated = new Date(timestamp * 1000).toLocaleTimeString();
        this.state.dbName = data.db_name || "";
        this.state.logs = data.logs || this.state.logs;
        const nextInterval = this.toNumber(
            data.config?.interval_ms,
            DEFAULT_INTERVAL_MS
        );
        if (nextInterval !== this.intervalMs) {
            this.intervalMs = Math.max(nextInterval, 1000);
            this.hiddenIntervalMs = Math.max(
                this.intervalMs * HIDDEN_INTERVAL_MULTIPLIER,
                4000
            );
            this.setTimer(this.getEffectiveInterval());
        }
    }

    onLogLinesInput(ev) {
        this.state.logLinesInput = ev.target.value;
    }

    onLogLinesChange(ev) {
        const value = this.toNumber(ev.target.value, null);
        if (!Number.isFinite(value)) {
            this.state.logLinesInput = String(this.state.logLines);
            return;
        }
        const clamped = Math.max(Math.min(value, 2000), 20);
        this.state.logLines = clamped;
        this.state.logLinesInput = String(clamped);
        this.fetchLogs();
        this.savePreferences();
    }

    onLogSearchInput(ev) {
        this.state.logSearch = ev.target.value || "";
        this.scheduleSearch();
        this.savePreferences();
    }

    scheduleSearch() {
        if (this.searchTimer) {
            clearTimeout(this.searchTimer);
        }
        this.searchTimer = setTimeout(() => {
            this.fetchLogs();
        }, 300);
    }

    handleVisibilityChange() {
        this.setTimer(this.getEffectiveInterval());
        if (!document.hidden) {
            this.fetchLogs();
        }
    }

    setTimer(intervalMs) {
        if (this.timer) {
            clearInterval(this.timer);
        }
        this.timer = setInterval(() => this.fetchLogs(), intervalMs);
    }

    getEffectiveInterval() {
        return document.hidden ? this.hiddenIntervalMs : this.intervalMs;
    }

    setError(message) {
        this.state.error = { message };
    }

    clearError() {
        this.state.error = null;
    }

    toNumber(value, fallback = null) {
        if (value === null || value === undefined || value === "") {
            return fallback;
        }
        const parsed = Number(value);
        return Number.isFinite(parsed) ? parsed : fallback;
    }

    applyPreferences() {
        const prefs = this.loadPreferences();
        if (prefs.logLines) {
            const clamped = Math.max(Math.min(prefs.logLines, 2000), 20);
            this.state.logLines = clamped;
            this.state.logLinesInput = String(clamped);
        }
        if (typeof prefs.logSearch === "string") {
            this.state.logSearch = prefs.logSearch;
        }
    }

    loadPreferences() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
        } catch (error) {
            return {};
        }
    }

    savePreferences() {
        const payload = {
            logLines: this.state.logLines,
            logSearch: this.state.logSearch,
        };
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
        } catch (error) {
            // ignore storage failures
        }
    }
}

registry.category("actions").add("server_monitor.odoo_log", ServerMonitorOdooLog);
