/** @odoo-module **/

import { loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import {
    Component,
    onMounted,
    onWillStart,
    onWillUnmount,
    useRef,
    useState,
} from "@odoo/owl";

const DEFAULT_HISTORY_LENGTH = 60;
const DEFAULT_INTERVAL_MS = 2000;
const HIDDEN_INTERVAL_MULTIPLIER = 4;
const STORAGE_KEY = "server_monitor.postgres_prefs";

export class ServerMonitorPostgres extends Component {
    static template = "server_monitor.PostgresMonitor";

    setup() {
        this.state = useState({
            lastUpdated: "",
            error: null,
            warnings: [],
            errors: [],
            isFetching: false,
            config: {
                slowQuerySeconds: 5,
                alertCacheHitMin: null,
                alertIdleInTx: null,
                alertLocksWaiting: null,
                alertConnPct: null,
            },
            currentDb: "",
            selectedDb: "",
            isCurrentDbSelected: true,
            connections: {
                total: null,
                active: null,
                idle: null,
                idleInTx: null,
                max: null,
                pct: null,
            },
            display: {
                connections: {
                    total: null,
                    active: null,
                    idle: null,
                    idleInTx: null,
                    max: null,
                    pct: null,
                },
                dbSize: null,
                cacheHitRatio: null,
                indexHitRatio: null,
                transactions: { commit: null, rollback: null },
                tuples: { inserted: null, updated: null, deleted: null },
            },
            dbSize: null,
            cacheHitRatio: null,
            indexHitRatio: null,
            locks: null,
            lockBreakdown: [],
            blockedQueries: [],
            dbOverview: [],
            autovacuum: [],
            bgwriter: {},
            wal: {},
            statStatements: [],
            transactions: { commit: null, rollback: null },
            tuples: { inserted: null, updated: null, deleted: null },
            longQueries: [],
            alerts: [],
            alertOverrides: {
                cacheHitMin: null,
                connPctMax: null,
            },
            alertInputs: {
                cacheHitMin: "",
                connPctMax: "",
            },
        });

        this.applyPreferences();

        this.cacheCanvasRef = useRef("cacheCanvas");
        this.transactionsCanvasRef = useRef("transactionsCanvas");
        this.cacheChart = null;
        this.transactionsChart = null;
        this.labels = [];
        this.series = {
            cacheHit: [],
            connPct: [],
            commitRate: [],
            rollbackRate: [],
        };
        this.lastTransactionSample = null;
        this.historyLength = DEFAULT_HISTORY_LENGTH;
        this.intervalMs = DEFAULT_INTERVAL_MS;
        this.hiddenIntervalMs = DEFAULT_INTERVAL_MS * HIDDEN_INTERVAL_MULTIPLIER;
        this.timer = null;
        this.handleVisibilityChange = this.handleVisibilityChange.bind(this);

        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
        });

        onMounted(() => {
            this.initCacheChart();
            this.initTransactionsChart();
            this.fetchMetrics();
            this.setTimer(this.getEffectiveInterval());
            document.addEventListener("visibilitychange", this.handleVisibilityChange);
        });

        onWillUnmount(() => {
            if (this.timer) {
                clearInterval(this.timer);
            }
            document.removeEventListener("visibilitychange", this.handleVisibilityChange);
            if (this.cacheChart) {
                this.cacheChart.destroy();
            }
            if (this.transactionsChart) {
                this.transactionsChart.destroy();
            }
        });
    }

    async fetchMetrics() {
        if (this.state.isFetching) {
            return;
        }
        this.state.isFetching = true;
        try {
            const data = await rpc("/server_monitor/postgres", {});
            if (data && data.error) {
                this.setError(data.error.message || "Unable to fetch metrics.");
                return;
            }
            this.clearError();
            this.updateMetrics(data);
        } catch (error) {
            this.setError("Unable to fetch metrics. Retrying...");
        } finally {
            this.state.isFetching = false;
        }
    }

    updateMetrics(data) {
        const config = data?.config || {};
        this.applyConfig(config);

        const timestamp = data.timestamp || Date.now() / 1000;
        this.appendLabel(this.formatLabel(timestamp));
        this.state.lastUpdated = new Date(timestamp * 1000).toLocaleTimeString();

        const connections = data.connections || {};
        this.state.connections = {
            total: this.toNumber(connections.total),
            active: this.toNumber(connections.active),
            idle: this.toNumber(connections.idle),
            idleInTx: this.toNumber(connections.idle_in_tx),
            max: this.toNumber(connections.max),
            pct: this.toNumber(connections.pct),
        };
        this.state.dbSize = this.toNumber(data.db_size);
        this.state.cacheHitRatio = this.toNumber(data.cache_hit_ratio);
        this.state.indexHitRatio = this.toNumber(data.index_hit_ratio);
        this.state.locks = this.toNumber(data.locks);
        this.state.lockBreakdown = data.lock_breakdown || [];
        this.state.blockedQueries = data.blocked_queries || [];
        this.state.dbOverview = data.db_overview || [];
        this.state.autovacuum = data.autovacuum || [];
        this.state.bgwriter = data.bgwriter || {};
        this.state.wal = data.wal || {};
        this.state.statStatements = data.stat_statements || [];
        this.state.transactions = {
            commit: this.toNumber(data.transactions?.commit),
            rollback: this.toNumber(data.transactions?.rollback),
        };
        this.state.tuples = {
            inserted: this.toNumber(data.tuples?.inserted),
            updated: this.toNumber(data.tuples?.updated),
            deleted: this.toNumber(data.tuples?.deleted),
        };
        this.state.longQueries = data.long_queries || [];
        this.state.warnings = data.warnings || [];
        this.state.errors = data.errors || [];
        this.state.currentDb = data.current_db || "";
        if (!this.state.selectedDb) {
            this.state.selectedDb = this.state.currentDb;
        }
        if (
            this.state.selectedDb &&
            !this.state.dbOverview.some((db) => db.name === this.state.selectedDb)
        ) {
            this.state.selectedDb = this.state.currentDb;
        }

        this.state.config = {
            slowQuerySeconds: this.toNumber(
                data.config?.slow_query_seconds,
                DEFAULT_INTERVAL_MS
            ),
            alertCacheHitMin: this.toNumber(data.config?.alert_cache_hit_min),
            alertIdleInTx: this.toNumber(data.config?.alert_idle_in_tx),
            alertLocksWaiting: this.toNumber(data.config?.alert_locks_waiting),
            alertConnPct: this.toNumber(data.config?.alert_conn_pct),
        };

        this.applySelectedDb(false);
        this.pushAndTrim(this.series.cacheHit, this.state.display.cacheHitRatio);
        this.pushAndTrim(this.series.connPct, this.state.display.connections.pct);
        this.pushTransactionRates(timestamp);
        this.state.alerts = this.computeAlerts();
        this.refreshCacheChart();
        this.refreshTransactionsChart();
    }

    applyConfig(config) {
        const nextInterval = this.toNumber(config.interval_ms, DEFAULT_INTERVAL_MS);
        const nextHistory = this.toNumber(config.history_length, DEFAULT_HISTORY_LENGTH);

        if (nextInterval !== this.intervalMs) {
            this.intervalMs = Math.max(nextInterval, 1000);
            this.hiddenIntervalMs = Math.max(
                this.intervalMs * HIDDEN_INTERVAL_MULTIPLIER,
                5000
            );
            this.setTimer(this.getEffectiveInterval());
        }

        if (nextHistory !== this.historyLength) {
            this.historyLength = Math.max(nextHistory, 10);
            this.trimHistory();
        }
    }

    initCacheChart() {
        if (!this.cacheCanvasRef.el) {
            return;
        }
        const config = {
            type: "line",
            data: {
                labels: this.labels,
                datasets: [],
            },
            options: {
                animation: false,
                maintainAspectRatio: false,
                responsive: true,
                scales: {
                    x: {
                        grid: { color: "#e6e6e6" },
                        ticks: { maxTicksLimit: 8, color: "#6b6b6b" },
                    },
                    y: {
                        beginAtZero: true,
                        max: 100,
                        grid: { color: "#e6e6e6" },
                        ticks: { color: "#6b6b6b", callback: (val) => `${val}%` },
                    },
                },
                plugins: {
                    legend: {
                        position: "top",
                        align: "end",
                        labels: { color: "#1f2d3d" },
                    },
                    tooltip: {
                        intersect: false,
                        mode: "index",
                    },
                },
                elements: {
                    line: { tension: 0.3, borderWidth: 2 },
                    point: { radius: 0, hitRadius: 8, hoverRadius: 4 },
                },
            },
        };
        this.cacheChart = new Chart(this.cacheCanvasRef.el, config);
    }

    initTransactionsChart() {
        if (!this.transactionsCanvasRef.el) {
            return;
        }
        const config = {
            type: "line",
            data: {
                labels: this.labels,
                datasets: [],
            },
            options: {
                animation: false,
                maintainAspectRatio: false,
                responsive: true,
                scales: {
                    x: {
                        grid: { color: "#e6e6e6" },
                        ticks: { maxTicksLimit: 8, color: "#6b6b6b" },
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: "#e6e6e6" },
                        ticks: {
                            color: "#6b6b6b",
                            callback: (val) => `${val} tx/s`,
                        },
                    },
                },
                plugins: {
                    legend: {
                        position: "top",
                        align: "end",
                        labels: { color: "#1f2d3d" },
                    },
                    tooltip: {
                        intersect: false,
                        mode: "index",
                        callbacks: {
                            label: (ctx) => `${ctx.dataset.label}: ${ctx.raw} tx/s`,
                        },
                    },
                },
                elements: {
                    line: { tension: 0.3, borderWidth: 2 },
                    point: { radius: 0, hitRadius: 8, hoverRadius: 4 },
                },
            },
        };
        this.transactionsChart = new Chart(this.transactionsCanvasRef.el, config);
    }

    refreshCacheChart() {
        if (!this.cacheChart || document.hidden) {
            return;
        }
        this.cacheChart.data.labels = this.labels;
        this.cacheChart.data.datasets = [
            {
                label: "Cache hit",
                data: this.series.cacheHit,
                borderColor: "#f39c12",
                backgroundColor: "rgba(243, 156, 18, 0.15)",
                fill: true,
            },
            {
                label: "Conn usage",
                data: this.series.connPct,
                borderColor: "#e74c3c",
                backgroundColor: "rgba(231, 76, 60, 0.1)",
                fill: false,
            },
        ];
        this.cacheChart.update("none");
    }

    refreshTransactionsChart() {
        if (!this.transactionsChart || document.hidden) {
            return;
        }
        this.transactionsChart.data.labels = this.labels;
        this.transactionsChart.data.datasets = [
            {
                label: "Commit",
                data: this.series.commitRate,
                borderColor: "#2ecc71",
                backgroundColor: "rgba(46, 204, 113, 0.1)",
                fill: false,
            },
            {
                label: "Rollback",
                data: this.series.rollbackRate,
                borderColor: "#e74c3c",
                backgroundColor: "rgba(231, 76, 60, 0.1)",
                fill: false,
            },
        ];
        this.transactionsChart.update("none");
    }

    appendLabel(label) {
        this.labels.push(label);
        if (this.labels.length > this.historyLength) {
            this.labels.shift();
        }
    }

    pushAndTrim(series, value) {
        series.push(Number.isFinite(value) ? value : null);
        if (series.length > this.historyLength) {
            series.shift();
        }
    }

    trimHistory() {
        if (this.labels.length > this.historyLength) {
            this.labels.splice(0, this.labels.length - this.historyLength);
        }
        for (const key of Object.keys(this.series)) {
            const series = this.series[key];
            if (series.length > this.historyLength) {
                series.splice(0, series.length - this.historyLength);
            }
        }
    }

    handleVisibilityChange() {
        this.setTimer(this.getEffectiveInterval());
        if (!document.hidden) {
            this.fetchMetrics();
            this.refreshCacheChart();
            this.refreshTransactionsChart();
        }
    }

    setTimer(intervalMs) {
        if (this.timer) {
            clearInterval(this.timer);
        }
        this.timer = setInterval(() => this.fetchMetrics(), intervalMs);
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

    formatLabel(timestamp) {
        const date = new Date(timestamp * 1000);
        const minutes = date.getMinutes().toString().padStart(2, "0");
        const seconds = date.getSeconds().toString().padStart(2, "0");
        return `${minutes}:${seconds}`;
    }

    formatBytes(value) {
        if (!Number.isFinite(value)) {
            return "--";
        }
        const units = ["B", "KB", "MB", "GB", "TB"];
        let size = value;
        let index = 0;
        while (size >= 1024 && index < units.length - 1) {
            size /= 1024;
            index += 1;
        }
        return `${size.toFixed(2)} ${units[index]}`;
    }

    formatPercent(value) {
        if (!Number.isFinite(value)) {
            return "--";
        }
        return `${value.toFixed(1)}%`;
    }

    formatNumber(value) {
        if (!Number.isFinite(value)) {
            return "--";
        }
        return Number(value).toLocaleString();
    }

    formatDuration(seconds) {
        if (!Number.isFinite(seconds)) {
            return "--";
        }
        if (seconds < 60) {
            return `${seconds.toFixed(1)}s`;
        }
        const minutes = Math.floor(seconds / 60);
        const remainder = seconds % 60;
        return `${minutes}m ${remainder.toFixed(0)}s`;
    }

    formatTimestamp(value) {
        if (!value) {
            return "--";
        }
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) {
            return "--";
        }
        return date.toLocaleString();
    }

    formatMs(value) {
        if (!Number.isFinite(value)) {
            return "--";
        }
        return `${value.toFixed(1)} ms`;
    }

    toNumber(value, fallback = null) {
        if (value === null || value === undefined || value === "") {
            return fallback;
        }
        const parsed = Number(value);
        return Number.isFinite(parsed) ? parsed : fallback;
    }

    get selectedDbStats() {
        return this.state.dbOverview.find((db) => db.name === this.state.selectedDb) || null;
    }

    onDbChange(ev) {
        this.state.selectedDb = ev.target.value;
        this.applySelectedDb(true);
        this.state.alerts = this.computeAlerts();
        this.savePreferences();
    }

    computeAlerts() {
        const alerts = [];
        const cfg = this.state.config;
        const cacheMin = Number.isFinite(this.state.alertOverrides.cacheHitMin)
            ? this.state.alertOverrides.cacheHitMin
            : cfg.alertCacheHitMin;
        const connMax = Number.isFinite(this.state.alertOverrides.connPctMax)
            ? this.state.alertOverrides.connPctMax
            : cfg.alertConnPct;
        if (
            Number.isFinite(this.state.display.cacheHitRatio) &&
            Number.isFinite(cacheMin) &&
            this.state.display.cacheHitRatio < cacheMin
        ) {
            alerts.push({
                label: "Low cache hit",
                value: `${this.state.display.cacheHitRatio.toFixed(1)}%`,
            });
        }
        if (
            Number.isFinite(this.state.display.connections.idleInTx) &&
            Number.isFinite(cfg.alertIdleInTx) &&
            this.state.display.connections.idleInTx > cfg.alertIdleInTx
        ) {
            alerts.push({
                label: "Idle in TX",
                value: this.state.display.connections.idleInTx,
            });
        }
        if (
            Number.isFinite(this.state.locks) &&
            Number.isFinite(cfg.alertLocksWaiting) &&
            this.state.locks >= cfg.alertLocksWaiting
        ) {
            alerts.push({ label: "Locks waiting", value: this.state.locks });
        }
        if (
            Number.isFinite(this.state.display.connections.pct) &&
            Number.isFinite(connMax) &&
            this.state.display.connections.pct >= connMax
        ) {
            alerts.push({
                label: "Conn usage",
                value: `${this.state.display.connections.pct.toFixed(1)}%`,
            });
        }
        if (this.state.longQueries.length) {
            alerts.push({
                label: "Slow queries",
                value: this.state.longQueries.length,
            });
        }
        if (this.state.blockedQueries.length) {
            alerts.push({
                label: "Blocked queries",
                value: this.state.blockedQueries.length,
            });
        }
        return alerts;
    }

    applySelectedDb(resetSeries) {
        const selected = this.selectedDbStats;
        const isCurrent =
            !this.state.selectedDb || this.state.selectedDb === this.state.currentDb;
        this.state.isCurrentDbSelected = isCurrent;

        const totalConnections = selected?.connections ?? this.state.connections.total;
        const maxConnections = this.state.connections.max;
        let connPct = this.state.connections.pct;
        if (Number.isFinite(totalConnections) && Number.isFinite(maxConnections)) {
            connPct = (totalConnections / maxConnections) * 100;
        }

        this.state.display = {
            connections: {
                total: totalConnections,
                active: isCurrent ? this.state.connections.active : null,
                idle: isCurrent ? this.state.connections.idle : null,
                idleInTx: isCurrent ? this.state.connections.idleInTx : null,
                max: maxConnections,
                pct: connPct,
            },
            dbSize: selected?.size ?? this.state.dbSize,
            cacheHitRatio: selected?.cache_hit_ratio ?? this.state.cacheHitRatio,
            indexHitRatio: selected?.index_hit_ratio ?? this.state.indexHitRatio,
            transactions: {
                commit: selected?.xact_commit ?? this.state.transactions.commit,
                rollback: selected?.xact_rollback ?? this.state.transactions.rollback,
            },
            tuples: {
                inserted: selected?.tup_inserted ?? this.state.tuples.inserted,
                updated: selected?.tup_updated ?? this.state.tuples.updated,
                deleted: selected?.tup_deleted ?? this.state.tuples.deleted,
            },
        };

        if (resetSeries) {
            this.labels = [];
            this.series.cacheHit = [];
            this.series.connPct = [];
            this.series.commitRate = [];
            this.series.rollbackRate = [];
            this.lastTransactionSample = null;
            this.refreshCacheChart();
            this.refreshTransactionsChart();
        }
    }

    onAlertInputChange(key, ev) {
        this.state.alertInputs = {
            ...this.state.alertInputs,
            [key]: ev.target.value,
        };
    }

    onAlertOverrideChange(key, ev) {
        const raw = ev.target.value;
        if (!raw) {
            this.state.alertOverrides = { ...this.state.alertOverrides, [key]: null };
            this.state.alertInputs = { ...this.state.alertInputs, [key]: "" };
            this.state.alerts = this.computeAlerts();
            this.savePreferences();
            return;
        }
        const value = this.toNumber(raw, null);
        if (!Number.isFinite(value)) {
            this.state.alertInputs = {
                ...this.state.alertInputs,
                [key]: String(this.state.alertOverrides[key] ?? ""),
            };
            return;
        }
        const clamped = Math.max(Math.min(value, 100), 1);
        this.state.alertOverrides = { ...this.state.alertOverrides, [key]: clamped };
        this.state.alertInputs = { ...this.state.alertInputs, [key]: String(clamped) };
        this.state.alerts = this.computeAlerts();
        this.savePreferences();
    }

    applyPreferences() {
        const prefs = this.loadPreferences();
        if (prefs.selectedDb) {
            this.state.selectedDb = prefs.selectedDb;
        }
        if (prefs.alertOverrides) {
            this.state.alertOverrides = {
                ...this.state.alertOverrides,
                ...prefs.alertOverrides,
            };
            this.state.alertInputs = {
                cacheHitMin:
                    this.state.alertOverrides.cacheHitMin !== null
                        ? String(this.state.alertOverrides.cacheHitMin)
                        : "",
                connPctMax:
                    this.state.alertOverrides.connPctMax !== null
                        ? String(this.state.alertOverrides.connPctMax)
                        : "",
            };
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
            selectedDb: this.state.selectedDb,
            alertOverrides: this.state.alertOverrides,
        };
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
        } catch (error) {
            // ignore storage failures
        }
    }

    pushTransactionRates(timestamp) {
        const commit = this.toNumber(this.state.display.transactions.commit);
        const rollback = this.toNumber(this.state.display.transactions.rollback);
        if (!Number.isFinite(commit) || !Number.isFinite(rollback)) {
            this.pushAndTrim(this.series.commitRate, null);
            this.pushAndTrim(this.series.rollbackRate, null);
            this.lastTransactionSample = null;
            return;
        }

        const previous = this.lastTransactionSample;
        if (
            !previous ||
            !Number.isFinite(previous.commit) ||
            !Number.isFinite(previous.rollback) ||
            !Number.isFinite(previous.timestamp)
        ) {
            this.pushAndTrim(this.series.commitRate, null);
            this.pushAndTrim(this.series.rollbackRate, null);
            this.lastTransactionSample = { commit, rollback, timestamp };
            return;
        }

        const deltaTime = Math.max(timestamp - previous.timestamp, 0.001);
        const commitDelta = Math.max(commit - previous.commit, 0);
        const rollbackDelta = Math.max(rollback - previous.rollback, 0);
        const commitRate = commitDelta / deltaTime;
        const rollbackRate = rollbackDelta / deltaTime;

        this.pushAndTrim(this.series.commitRate, commitRate);
        this.pushAndTrim(this.series.rollbackRate, rollbackRate);
        this.lastTransactionSample = { commit, rollback, timestamp };
    }
}

registry.category("actions").add("server_monitor.postgres", ServerMonitorPostgres);
