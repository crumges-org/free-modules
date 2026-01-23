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
const DEFAULT_INTERVAL_MS = 1000;
const HIDDEN_INTERVAL_MULTIPLIER = 5;
const STORAGE_KEY = "server_monitor.server_prefs";
const DEFAULT_ALERTS = {
    cpuMax: 85,
    ramMax: 85,
    diskMax: 90,
};

const COLORS = {
    cpu: { line: "#00a39b", fill: "rgba(0, 163, 155, 0.15)" },
    memory: { line: "#6a62d2", fill: "rgba(106, 98, 210, 0.15)" },
    disk: { line: "#f39c12", fill: "rgba(243, 156, 18, 0.15)" },
    netIn: { line: "#e74c3c", fill: "rgba(231, 76, 60, 0.15)" },
    netOut: { line: "#ff8c42", fill: "rgba(255, 140, 66, 0.15)" },
};

export class ServerMonitorDashboard extends Component {
    static template = "server_monitor.ServerMonitor";

    setup() {
        this.state = useState({
            selectedKey: "cpu",
            cpuPercent: 0,
            cpuPerCore: [],
            cpuFreq: {},
            cpuStats: {},
            loadAvg: [],
            memory: { used: 0, total: 0, percent: 0 },
            swap: {},
            diskPartitions: [],
            diskIo: [],
            networkAdapters: [],
            gpus: [],
            system: { bootTime: 0, uptime: 0 },
            sensors: { temperatures: [], fans: [], battery: null },
            processes: { top_cpu: [], top_memory: [], total: 0 },
            lastUpdated: "",
            stats: [],
            alerts: [],
            alertConfig: { ...DEFAULT_ALERTS },
            alertInputs: {
                cpuMax: String(DEFAULT_ALERTS.cpuMax),
                ramMax: String(DEFAULT_ALERTS.ramMax),
                diskMax: String(DEFAULT_ALERTS.diskMax),
            },
            error: null,
            isFetching: false,
        });

        this.applyPreferences();

        this.canvasRef = useRef("canvas");
        this.chart = null;
        this.labels = [];
        this.series = {
            cpu: [],
            memory: [],
            disks: {},
            network: {},
            gpus: {},
        };
        this.historyLength = DEFAULT_HISTORY_LENGTH;
        this.intervalMs = DEFAULT_INTERVAL_MS;
        this.hiddenIntervalMs = DEFAULT_INTERVAL_MS * HIDDEN_INTERVAL_MULTIPLIER;
        this.timer = null;
        this.handleVisibilityChange = this.handleVisibilityChange.bind(this);

        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
        });

        onMounted(() => {
            this.initChart();
            this.fetchMetrics();
            this.setTimer(this.getEffectiveInterval());
            document.addEventListener("visibilitychange", this.handleVisibilityChange);
        });

        onWillUnmount(() => {
            if (this.timer) {
                clearInterval(this.timer);
            }
            document.removeEventListener("visibilitychange", this.handleVisibilityChange);
            if (this.chart) {
                this.chart.destroy();
            }
        });
    }

    get metricItems() {
        const items = [
            {
                key: "cpu",
                label: "CPU",
                value: `${Math.round(this.state.cpuPercent)}%`,
                chartTitle: "CPU Usage",
            },
            {
                key: "memory",
                label: "RAM",
                value: `${this.formatGB(this.state.memory.used)} / ${this.formatGB(
                    this.state.memory.total
                )} (${this.state.memory.percent.toFixed(2)}%)`,
                chartTitle: "RAM Usage",
            },
        ];

        for (const disk of this.state.diskPartitions) {
            items.push({
                key: `disk:${disk.key}`,
                label: "Disk",
                subLabel: disk.mountpoint,
                value: `${this.formatGB(disk.used)} / ${this.formatGB(
                    disk.total
                )} (${disk.percent.toFixed(2)}%)\nFree: ${this.formatGB(disk.free)}`,
                chartTitle: `Disk ${disk.mountpoint}`,
            });
        }

        for (const adapter of this.state.networkAdapters) {
            items.push({
                key: `net:${adapter.name}`,
                label: "Network adapter",
                subLabel: adapter.name,
                value: `In: ${this.formatMbits(adapter.inRate)} Out: ${this.formatMbits(
                    adapter.outRate
                )}`,
                chartTitle: `Network ${adapter.name}`,
            });
        }

        for (const gpu of this.state.gpus) {
            items.push({
                key: `gpu:${gpu.id}`,
                label: "GPU",
                subLabel: gpu.name || "GPU",
                value: this.formatGpuSidebarValue(gpu),
                chartTitle: `GPU ${gpu.name || ""}`.trim(),
            });
        }

        return items;
    }

    get selectedTitle() {
        const item = this.metricItems.find((entry) => entry.key === this.state.selectedKey);
        return item ? item.chartTitle : "Server Monitor";
    }

    selectMetric(key) {
        this.state.selectedKey = key;
        this.refreshStats();
        this.refreshChart();
        this.savePreferences();
    }

    async fetchMetrics() {
        if (this.state.isFetching) {
            return;
        }
        this.state.isFetching = true;
        try {
            const data = await rpc("/server_monitor/metrics", {});
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
        this.applyConfig(data?.config || {});

        const timestamp = data.timestamp || Date.now() / 1000;
        this.appendLabel(this.formatLabel(timestamp));
        this.state.lastUpdated = new Date(timestamp * 1000).toLocaleTimeString();

        const cpuPercent = Math.max(0, Math.min(100, data.cpu_percent || 0));
        this.state.cpuPercent = cpuPercent;
        this.state.cpuPerCore = Array.isArray(data.cpu_per_core) ? data.cpu_per_core : [];
        this.state.cpuFreq = data.cpu_freq || {};
        this.state.cpuStats = data.cpu_stats || {};
        this.state.loadAvg = Array.isArray(data.loadavg) ? data.loadavg : [];
        this.pushAndTrim(this.series.cpu, cpuPercent);

        const memory = data.memory || {};
        this.state.memory = {
            used: memory.used || 0,
            total: memory.total || 0,
            percent: memory.percent || 0,
            available: memory.available || 0,
            free: memory.free || 0,
            cached: memory.cached || 0,
            buffers: memory.buffers || 0,
            shared: memory.shared || 0,
        };
        this.pushAndTrim(
            this.series.memory,
            Math.max(0, Math.min(100, memory.percent || 0))
        );

        const swap = data.swap || {};
        this.state.swap = {
            total: swap.total || 0,
            used: swap.used || 0,
            free: swap.free || 0,
            percent: swap.percent || 0,
            sin: swap.sin || 0,
            sout: swap.sout || 0,
        };

        this.updateDiskSeries(data.disks || []);
        this.state.diskIo = (data.disk_io || []).map((disk) => ({
            name: disk.name || "disk",
            readMbs: disk.read_mbs || 0,
            writeMbs: disk.write_mbs || 0,
            readBytes: disk.read_bytes || 0,
            writeBytes: disk.write_bytes || 0,
            readCount: disk.read_count || 0,
            writeCount: disk.write_count || 0,
        }));
        this.updateNetworkSeries(data.network || []);
        this.updateGpuSeries(data.gpus || []);
        this.state.system = {
            bootTime: data.system?.boot_time || 0,
            uptime: data.system?.uptime || 0,
        };
        this.state.sensors = data.sensors || {
            temperatures: [],
            fans: [],
            battery: null,
        };
        this.state.processes = data.processes || {
            top_cpu: [],
            top_memory: [],
            total: 0,
        };
        this.state.alerts = this.computeAlerts();
        this.refreshStats();
        this.refreshChart();
    }

    applyConfig(config) {
        const nextInterval = this.parseNumber(config.interval_ms, DEFAULT_INTERVAL_MS);
        const nextHistory = this.parseNumber(config.history_length, DEFAULT_HISTORY_LENGTH);

        if (nextInterval !== this.intervalMs) {
            this.intervalMs = Math.max(nextInterval, 250);
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

    updateDiskSeries(disks) {
        const seen = new Set();
        const partitions = disks.map((disk) => {
            const key = this.diskKey(disk);
            seen.add(key);
            if (!this.series.disks[key]) {
                this.series.disks[key] = new Array(this.labels.length - 1).fill(0);
            }
            this.pushAndTrim(
                this.series.disks[key],
                Math.max(0, Math.min(100, disk.percent || 0))
            );
            return {
                key,
                mountpoint: disk.mountpoint || disk.device || "Disk",
                total: disk.total || 0,
                used: disk.used || 0,
                free: disk.free || 0,
                percent: disk.percent || 0,
            };
        });

        for (const key of Object.keys(this.series.disks)) {
            if (!seen.has(key)) {
                this.pushAndTrim(this.series.disks[key], 0);
            }
        }

        this.state.diskPartitions = partitions;
        if (
            this.state.selectedKey.startsWith("disk:") &&
            !seen.has(this.state.selectedKey.slice(5))
        ) {
            this.state.selectedKey = "cpu";
        }
    }

    updateNetworkSeries(networkAdapters) {
        const seen = new Set();
        const adapterSummaries = [];

        for (const adapter of networkAdapters) {
            const name = adapter.name;
            seen.add(name);

            if (!this.series.network[name]) {
                this.series.network[name] = {
                    in: new Array(this.labels.length - 1).fill(0),
                    out: new Array(this.labels.length - 1).fill(0),
                };
            }

            const inRate = adapter.in_mbits || 0;
            const outRate = adapter.out_mbits || 0;
            this.pushAndTrim(this.series.network[name].in, inRate);
            this.pushAndTrim(this.series.network[name].out, outRate);

            adapterSummaries.push({
                name,
                inRate,
                outRate,
                speed: adapter.speed_mbps || 0,
                mtu: adapter.mtu || 0,
                duplex: adapter.duplex || "unknown",
                ips: adapter.ips || [],
            });
        }

        for (const name of Object.keys(this.series.network)) {
            if (!seen.has(name)) {
                this.pushAndTrim(this.series.network[name].in, 0);
                this.pushAndTrim(this.series.network[name].out, 0);
            }
        }

        this.state.networkAdapters = adapterSummaries;
        if (
            this.state.selectedKey.startsWith("net:") &&
            !seen.has(this.state.selectedKey.slice(4))
        ) {
            this.state.selectedKey = "cpu";
        }
    }

    updateGpuSeries(gpus) {
        const seen = new Set();
        const summaries = gpus.map((gpu, index) => {
            const id = gpu.id || `${index}`;
            seen.add(id);
            if (!this.series.gpus[id]) {
                this.series.gpus[id] = new Array(this.labels.length - 1).fill(null);
            }
            const utilization = this.parseNumber(gpu.utilization, null);
            this.pushAndTrim(
                this.series.gpus[id],
                Number.isFinite(utilization) ? utilization : null
            );
            return {
                id,
                name: gpu.name || `GPU ${index}`,
                vendor: gpu.vendor || "gpu",
                utilization,
                memoryTotal: Number.isFinite(gpu.memory_total) ? gpu.memory_total : null,
                memoryUsed: Number.isFinite(gpu.memory_used) ? gpu.memory_used : null,
                memoryFree: Number.isFinite(gpu.memory_free) ? gpu.memory_free : null,
                memoryPercent: Number.isFinite(gpu.memory_percent)
                    ? gpu.memory_percent
                    : null,
                temperature: gpu.temperature,
                fanSpeed: gpu.fan_speed,
                powerDraw: gpu.power_draw,
                clockSm: gpu.clock_sm,
                clockMem: gpu.clock_mem,
            };
        });

        for (const key of Object.keys(this.series.gpus)) {
            if (!seen.has(key)) {
                this.pushAndTrim(this.series.gpus[key], null);
            }
        }

        this.state.gpus = summaries;
        if (
            this.state.selectedKey.startsWith("gpu:") &&
            !seen.has(this.state.selectedKey.slice(4))
        ) {
            this.state.selectedKey = "cpu";
        }
    }

    initChart() {
        if (!this.canvasRef.el) {
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
                            callback: (value) => this.formatTick(value),
                        },
                    },
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        intersect: false,
                        mode: "index",
                    },
                },
                elements: {
                    line: { tension: 0.35, borderWidth: 2 },
                    point: { radius: 0, hitRadius: 8, hoverRadius: 4 },
                },
            },
        };
        this.chart = new Chart(this.canvasRef.el, config);
    }

    refreshChart() {
        if (!this.chart || document.hidden) {
            return;
        }
        const { datasets, suggestedMax } = this.getChartData();
        this.chart.data.labels = this.labels;
        this.chart.data.datasets = datasets;
        this.chart.options.scales.y.suggestedMax = suggestedMax;
        this.chart.update("none");
    }

    refreshStats() {
        this.state.stats = this.getStats();
    }

    getChartData() {
        if (this.state.selectedKey.startsWith("net:")) {
            const adapterName = this.state.selectedKey.slice(4);
            const series = this.series.network[adapterName] || { in: [], out: [] };
            const maxValue = Math.max(1, ...series.in, ...series.out);
            return {
                suggestedMax: Math.ceil(maxValue * 1.2),
                datasets: [
                    {
                        label: "In",
                        data: series.in,
                        borderColor: COLORS.netIn.line,
                        backgroundColor: COLORS.netIn.fill,
                        fill: true,
                    },
                    {
                        label: "Out",
                        data: series.out,
                        borderColor: COLORS.netOut.line,
                        backgroundColor: COLORS.netOut.fill,
                        fill: true,
                    },
                ],
            };
        }

        if (this.state.selectedKey.startsWith("disk:")) {
            const key = this.state.selectedKey.slice(5);
            const data = this.series.disks[key] || [];
            return {
                suggestedMax: 100,
                datasets: [
                    {
                        label: "Disk",
                        data,
                        borderColor: COLORS.disk.line,
                        backgroundColor: COLORS.disk.fill,
                        fill: true,
                    },
                ],
            };
        }

        if (this.state.selectedKey.startsWith("gpu:")) {
            const key = this.state.selectedKey.slice(4);
            const data = this.series.gpus[key] || [];
            return {
                suggestedMax: 100,
                datasets: [
                    {
                        label: "GPU",
                        data,
                        borderColor: "#1f78b4",
                        backgroundColor: "rgba(31, 120, 180, 0.15)",
                        fill: true,
                    },
                ],
            };
        }

        const seriesKey = this.state.selectedKey;
        const line = COLORS[seriesKey]?.line || COLORS.cpu.line;
        const fill = COLORS[seriesKey]?.fill || COLORS.cpu.fill;
        const data = this.series[seriesKey] || [];
        return {
            suggestedMax: 100,
            datasets: [
                {
                    label: seriesKey,
                    data,
                    borderColor: line,
                    backgroundColor: fill,
                    fill: true,
                },
            ],
        };
    }

    getStats() {
        if (this.state.selectedKey.startsWith("net:")) {
            const adapterName = this.state.selectedKey.slice(4);
            const series = this.series.network[adapterName] || { in: [], out: [] };
            const inStats = this.computeStats(series.in);
            const outStats = this.computeStats(series.out);
            return [
                ...this.formatStats("In", inStats, (value) => this.formatMbits(value)),
                ...this.formatStats("Out", outStats, (value) => this.formatMbits(value)),
            ];
        }

        if (this.state.selectedKey.startsWith("disk:")) {
            const key = this.state.selectedKey.slice(5);
            const diskStats = this.computeStats(this.series.disks[key] || []);
            return this.formatStats("", diskStats, (value) => this.formatPercent(value));
        }

        if (this.state.selectedKey.startsWith("gpu:")) {
            const key = this.state.selectedKey.slice(4);
            const gpuStats = this.computeStats(this.series.gpus[key] || []);
            return this.formatStats("", gpuStats, (value) => this.formatPercent(value));
        }

        const stats = this.computeStats(this.series[this.state.selectedKey] || []);
        return this.formatStats("", stats, (value) => this.formatPercent(value));
    }

    computeStats(values) {
        const samples = values.filter((value) => Number.isFinite(value));
        if (!samples.length) {
            return { min: null, max: null, avg: null, hasData: false };
        }
        const min = Math.min(...samples);
        const max = Math.max(...samples);
        const avg = samples.reduce((sum, val) => sum + val, 0) / samples.length;
        return { min, max, avg, hasData: true };
    }

    formatStats(prefix, stats, formatter) {
        const labelPrefix = prefix ? `${prefix} ` : "";
        if (!stats.hasData) {
            return [
                { label: `${labelPrefix}Min`, value: "--" },
                { label: `${labelPrefix}Max`, value: "--" },
                { label: `${labelPrefix}Avg`, value: "--" },
            ];
        }
        return [
            { label: `${labelPrefix}Min`, value: formatter(stats.min) },
            { label: `${labelPrefix}Max`, value: formatter(stats.max) },
            { label: `${labelPrefix}Avg`, value: formatter(stats.avg) },
        ];
    }

    formatTick(value) {
        if (this.state.selectedKey.startsWith("net:")) {
            return `${Number(value).toFixed(1)} Mbit/s`;
        }
        return `${Math.round(value)}%`;
    }

    appendLabel(label) {
        this.labels.push(label);
        if (this.labels.length > this.historyLength) {
            this.labels.shift();
        }
    }

    pushAndTrim(series, value) {
        series.push(value);
        if (series.length > this.historyLength) {
            series.shift();
        }
    }

    trimHistory() {
        if (this.labels.length > this.historyLength) {
            this.labels.splice(0, this.labels.length - this.historyLength);
        }
        for (const seriesKey of ["cpu", "memory"]) {
            const series = this.series[seriesKey];
            if (series.length > this.historyLength) {
                series.splice(0, series.length - this.historyLength);
            }
        }
        for (const key of Object.keys(this.series.disks)) {
            const series = this.series.disks[key];
            if (series.length > this.historyLength) {
                series.splice(0, series.length - this.historyLength);
            }
        }
        for (const key of Object.keys(this.series.network)) {
            const incoming = this.series.network[key].in;
            const outgoing = this.series.network[key].out;
            if (incoming.length > this.historyLength) {
                incoming.splice(0, incoming.length - this.historyLength);
            }
            if (outgoing.length > this.historyLength) {
                outgoing.splice(0, outgoing.length - this.historyLength);
            }
        }
        for (const key of Object.keys(this.series.gpus)) {
            const series = this.series.gpus[key];
            if (series.length > this.historyLength) {
                series.splice(0, series.length - this.historyLength);
            }
        }
    }

    handleVisibilityChange() {
        this.setTimer(this.getEffectiveInterval());
        if (!document.hidden) {
            this.fetchMetrics();
            this.refreshChart();
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

    diskKey(disk) {
        return disk.mountpoint || disk.device || "disk";
    }

    parseNumber(value, fallback) {
        if (value === null || value === undefined || value === "") {
            return fallback;
        }
        const parsed = Number(value);
        return Number.isFinite(parsed) ? parsed : fallback;
    }

    formatLabel(timestamp) {
        const date = new Date(timestamp * 1000);
        const minutes = date.getMinutes().toString().padStart(2, "0");
        const seconds = date.getSeconds().toString().padStart(2, "0");
        return `${minutes}:${seconds}`;
    }

    formatGB(bytes) {
        if (!bytes) {
            return "0.00 GB";
        }
        return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
    }

    formatMaybeGB(bytes) {
        if (!Number.isFinite(bytes)) {
            return "--";
        }
        return this.formatGB(bytes);
    }

    formatMB(bytes) {
        if (!bytes) {
            return "0.00 MB";
        }
        return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    }

    formatGpuSidebarValue(gpu) {
        const utilization = this.formatPercent(gpu.utilization);
        const memTotal = Number.isFinite(gpu.memoryTotal)
            ? this.formatGB(gpu.memoryTotal)
            : "--";
        const memUsed = Number.isFinite(gpu.memoryUsed) ? this.formatGB(gpu.memoryUsed) : "--";
        const temp = this.formatTemperature(gpu.temperature);
        let value = `${utilization}\nMem: ${memUsed} / ${memTotal}`;
        if (temp !== "--") {
            value += `\nTemp: ${temp}`;
        }
        return value;
    }

    formatMbits(value) {
        if (value === null || value === undefined) {
            return "--";
        }
        return `${Number(value).toFixed(1)} Mbits/s`;
    }

    formatUptime(seconds) {
        if (!seconds) {
            return "--";
        }
        const total = Math.floor(seconds);
        const days = Math.floor(total / 86400);
        const hours = Math.floor((total % 86400) / 3600);
        const minutes = Math.floor((total % 3600) / 60);
        const parts = [];
        if (days) {
            parts.push(`${days}d`);
        }
        if (hours || days) {
            parts.push(`${hours}h`);
        }
        parts.push(`${minutes}m`);
        return parts.join(" ");
    }

    formatTimestamp(seconds) {
        if (!seconds) {
            return "--";
        }
        return new Date(seconds * 1000).toLocaleString();
    }

    formatCpuFreq(freq) {
        if (!freq || !freq.current) {
            return "--";
        }
        const current = (freq.current / 1000).toFixed(2);
        const min = freq.min ? (freq.min / 1000).toFixed(2) : "--";
        const max = freq.max ? (freq.max / 1000).toFixed(2) : "--";
        return `${current} GHz (min ${min} / max ${max})`;
    }

    formatLoadAvg(values) {
        if (!values || !values.length) {
            return "--";
        }
        return values.map((value) => Number(value).toFixed(2)).join(", ");
    }

    formatNumber(value) {
        if (value === null || value === undefined) {
            return "--";
        }
        return Number(value).toLocaleString();
    }

    formatPercent(value) {
        if (value === null || value === undefined) {
            return "--";
        }
        return `${Number(value).toFixed(1)}%`;
    }

    formatTemperature(value) {
        if (value === null || value === undefined) {
            return "--";
        }
        return `${Number(value).toFixed(1)} C`;
    }

    formatWatts(value) {
        if (value === null || value === undefined) {
            return "--";
        }
        return `${Number(value).toFixed(1)} W`;
    }

    formatMHz(value) {
        if (value === null || value === undefined) {
            return "--";
        }
        return `${Math.round(value)} MHz`;
    }

    formatRpm(value) {
        if (value === null || value === undefined) {
            return "--";
        }
        return `${Math.round(value)} RPM`;
    }

    formatBattery(battery) {
        if (!battery) {
            return "--";
        }
        const status = battery.power_plugged ? "plugged" : "on battery";
        return `${battery.percent.toFixed(1)}% (${status})`;
    }

    onAlertInputChange(key, ev) {
        this.state.alertInputs = {
            ...this.state.alertInputs,
            [key]: ev.target.value,
        };
    }

    onAlertThresholdChange(key, ev) {
        const value = this.parseNumber(ev.target.value, null);
        if (!Number.isFinite(value)) {
            this.state.alertInputs = {
                ...this.state.alertInputs,
                [key]: String(this.state.alertConfig[key]),
            };
            return;
        }
        const clamped = Math.max(Math.min(value, 100), 1);
        this.state.alertConfig = {
            ...this.state.alertConfig,
            [key]: clamped,
        };
        this.state.alertInputs = {
            ...this.state.alertInputs,
            [key]: String(clamped),
        };
        this.state.alerts = this.computeAlerts();
        this.savePreferences();
    }

    computeAlerts() {
        const alerts = [];
        const { cpuMax, ramMax, diskMax } = this.state.alertConfig;
        if (Number.isFinite(this.state.cpuPercent) && this.state.cpuPercent >= cpuMax) {
            alerts.push({
                label: "CPU",
                value: `${this.state.cpuPercent.toFixed(1)}%`,
                threshold: `${cpuMax}%`,
            });
        }
        if (
            Number.isFinite(this.state.memory.percent) &&
            this.state.memory.percent >= ramMax
        ) {
            alerts.push({
                label: "RAM",
                value: `${this.state.memory.percent.toFixed(1)}%`,
                threshold: `${ramMax}%`,
            });
        }
        for (const disk of this.state.diskPartitions) {
            if (Number.isFinite(disk.percent) && disk.percent >= diskMax) {
                alerts.push({
                    label: `Disk ${disk.mountpoint}`,
                    value: `${disk.percent.toFixed(1)}%`,
                    threshold: `${diskMax}%`,
                });
            }
        }
        return alerts;
    }

    applyPreferences() {
        const prefs = this.loadPreferences();
        if (prefs.selectedKey) {
            this.state.selectedKey = prefs.selectedKey;
        }
        if (prefs.alertConfig) {
            this.state.alertConfig = { ...DEFAULT_ALERTS, ...prefs.alertConfig };
            this.state.alertInputs = {
                cpuMax: String(this.state.alertConfig.cpuMax),
                ramMax: String(this.state.alertConfig.ramMax),
                diskMax: String(this.state.alertConfig.diskMax),
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
            selectedKey: this.state.selectedKey,
            alertConfig: this.state.alertConfig,
        };
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
        } catch (error) {
            // ignore storage failures
        }
    }
}

registry.category("actions").add("server_monitor.dashboard", ServerMonitorDashboard);
