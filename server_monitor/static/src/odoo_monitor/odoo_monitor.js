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

export class ServerMonitorOdoo extends Component {
    static template = "server_monitor.OdooMonitor";

    setup() {
        this.state = useState({
            lastUpdated: "",
            dbName: "",
            error: null,
            isFetching: false,
            config: {
                intervalMs: DEFAULT_INTERVAL_MS,
                historyLength: DEFAULT_HISTORY_LENGTH,
                errorWindowMinutes: 60,
            },
            http: {
                labels: [],
                requests: [],
                latencyP95: [],
                latencyP99: [],
                summary: {},
                slow_endpoints: [],
                top_errors: [],
            },
            workers: {
                available: false,
                count: null,
                busy: null,
                memory_rss: null,
                processes: [],
            },
            cron: {
                available: false,
                total: null,
                active: null,
                overdue: null,
                failed: null,
                running_count: null,
                running: [],
                active_jobs: [],
                top_failed: [],
            },
            bus: { available: false, pending: null, online: null },
            mail: {
                available: false,
                outgoing: null,
                failed: null,
                sent_recent: null,
            },
            filestore: {
                available: false,
                attachments: null,
                db_attachments: null,
                size: null,
            },
            errors: { available: false, total: null, top: [] },
            cache: {
                available: false,
                count: null,
                entries: null,
                largest: [],
            },
            orm: { available: false, statements: [] },
            external: {
                mail_servers: null,
                payment_providers: null,
                attachment_location: null,
            },
        });

        this.requestsCanvasRef = useRef("requestsCanvas");
        this.latencyCanvasRef = useRef("latencyCanvas");
        this.requestsChart = null;
        this.latencyChart = null;
        this.intervalMs = DEFAULT_INTERVAL_MS;
        this.hiddenIntervalMs = DEFAULT_INTERVAL_MS * HIDDEN_INTERVAL_MULTIPLIER;
        this.timer = null;
        this.handleVisibilityChange = this.handleVisibilityChange.bind(this);

        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
        });

        onMounted(() => {
            this.initRequestsChart();
            this.initLatencyChart();
            this.fetchMetrics();
            this.setTimer(this.getEffectiveInterval());
            document.addEventListener("visibilitychange", this.handleVisibilityChange);
        });

        onWillUnmount(() => {
            if (this.timer) {
                clearInterval(this.timer);
            }
            document.removeEventListener("visibilitychange", this.handleVisibilityChange);
            if (this.requestsChart) {
                this.requestsChart.destroy();
            }
            if (this.latencyChart) {
                this.latencyChart.destroy();
            }
        });
    }

    async fetchMetrics() {
        if (this.state.isFetching) {
            return;
        }
        this.state.isFetching = true;
        try {
            const data = await rpc("/server_monitor/odoo", {});
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
        this.state.lastUpdated = new Date(timestamp * 1000).toLocaleTimeString();
        this.state.dbName = data.db_name || "";

        const http = data.http || {};
        this.state.http = {
            labels: http.labels || [],
            requests: http.requests_per_s || [],
            latencyP95: http.latency_p95 || [],
            latencyP99: http.latency_p99 || [],
            summary: http.summary || {},
            slow_endpoints: http.slow_endpoints || [],
            top_errors: http.top_errors || [],
        };

        this.state.workers = this.withFallback(data.workers, this.state.workers);
        this.state.cron = this.withFallback(data.cron, this.state.cron);
        this.state.bus = this.withFallback(data.bus, this.state.bus);
        this.state.mail = this.withFallback(data.mail, this.state.mail);
        this.state.filestore = this.withFallback(data.filestore, this.state.filestore);
        this.state.errors = this.withFallback(data.errors, this.state.errors);
        this.state.cache = this.withFallback(data.cache, this.state.cache);
        this.state.orm = this.withFallback(data.orm, this.state.orm);
        this.state.external = this.withFallback(data.external, this.state.external);

        this.refreshCharts();
    }

    applyConfig(config) {
        const nextInterval = this.toNumber(config.interval_ms, DEFAULT_INTERVAL_MS);
        const nextHistory = this.toNumber(config.history_length, DEFAULT_HISTORY_LENGTH);
        const nextErrorWindow = this.toNumber(config.error_window_minutes, 60);
        const nextCronWindow = this.toNumber(config.cron_running_seconds, 300);

        this.state.config = {
            intervalMs: nextInterval,
            historyLength: nextHistory,
            errorWindowMinutes: nextErrorWindow,
            cronRunningSeconds: nextCronWindow,
        };

        if (nextInterval !== this.intervalMs) {
            this.intervalMs = Math.max(nextInterval, 1000);
            this.hiddenIntervalMs = Math.max(
                this.intervalMs * HIDDEN_INTERVAL_MULTIPLIER,
                4000
            );
            this.setTimer(this.getEffectiveInterval());
        }
    }

    initRequestsChart() {
        if (!this.requestsCanvasRef.el) {
            return;
        }
        const config = {
            type: "line",
            data: {
                labels: [],
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
                        ticks: { color: "#6b6b6b" },
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
        this.requestsChart = new Chart(this.requestsCanvasRef.el, config);
    }

    initLatencyChart() {
        if (!this.latencyCanvasRef.el) {
            return;
        }
        const config = {
            type: "line",
            data: {
                labels: [],
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
                            callback: (val) => `${val} ms`,
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
                            label: (ctx) => `${ctx.dataset.label}: ${ctx.raw} ms`,
                        },
                    },
                },
                elements: {
                    line: { tension: 0.3, borderWidth: 2 },
                    point: { radius: 0, hitRadius: 8, hoverRadius: 4 },
                },
            },
        };
        this.latencyChart = new Chart(this.latencyCanvasRef.el, config);
    }

    refreshCharts() {
        if (document.hidden) {
            return;
        }
        const labels = this.state.http.labels || [];
        if (this.requestsChart) {
            this.requestsChart.data.labels = labels;
            this.requestsChart.data.datasets = [
                {
                    label: "Req/s",
                    data: this.state.http.requests || [],
                    borderColor: "#00a39b",
                    backgroundColor: "rgba(0, 163, 155, 0.15)",
                    fill: true,
                },
            ];
            this.requestsChart.update("none");
        }
        if (this.latencyChart) {
            this.latencyChart.data.labels = labels;
            this.latencyChart.data.datasets = [
                {
                    label: "P95",
                    data: this.state.http.latencyP95 || [],
                    borderColor: "#6a62d2",
                    backgroundColor: "rgba(106, 98, 210, 0.1)",
                    fill: false,
                },
                {
                    label: "P99",
                    data: this.state.http.latencyP99 || [],
                    borderColor: "#f39c12",
                    backgroundColor: "rgba(243, 156, 18, 0.1)",
                    fill: false,
                },
            ];
            this.latencyChart.update("none");
        }
    }

    handleVisibilityChange() {
        this.setTimer(this.getEffectiveInterval());
        if (!document.hidden) {
            this.fetchMetrics();
            this.refreshCharts();
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

    withFallback(data, fallback) {
        return data ? { ...fallback, ...data } : fallback;
    }

    toNumber(value, fallback = null) {
        if (value === null || value === undefined || value === "") {
            return fallback;
        }
        const parsed = Number(value);
        return Number.isFinite(parsed) ? parsed : fallback;
    }

    formatNumber(value) {
        if (!Number.isFinite(value)) {
            return "--";
        }
        return Number(value).toLocaleString();
    }

    formatPercent(value) {
        if (!Number.isFinite(value)) {
            return "--";
        }
        return `${value.toFixed(1)}%`;
    }

    formatMs(value) {
        if (!Number.isFinite(value)) {
            return "--";
        }
        return `${value.toFixed(1)} ms`;
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

    formatDuration(value) {
        if (!Number.isFinite(value)) {
            return "--";
        }
        if (value < 60) {
            return `${value.toFixed(0)}s`;
        }
        const minutes = Math.floor(value / 60);
        const seconds = Math.floor(value % 60);
        if (minutes < 60) {
            return `${minutes}m ${seconds}s`;
        }
        const hours = Math.floor(minutes / 60);
        const remMinutes = minutes % 60;
        return `${hours}h ${remMinutes}m`;
    }
}

registry.category("actions").add("server_monitor.odoo", ServerMonitorOdoo);
