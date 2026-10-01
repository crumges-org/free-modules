import { Component, onWillStart, useEffect, useRef, useState } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";

/**
 * One small chart card: title, canvas, and the numbers behind it.
 *
 * Chart.js comes from Odoo's own lazy bundle (`web.chartjs_lib`, Chart.js
 * 4.4.5), never a CDN - this module has to install on databases with no
 * outbound network. `loadBundle` is memoised, so three cards asking for it at
 * once still produce one request.
 *
 * Colours are read off the DOM with `getComputedStyle` at draw time rather than
 * being hard-coded here. Odoo 19 serves dark mode as a *different compiled
 * stylesheet*, so by the time this runs the `--aam-*` tokens already hold the
 * right values for the current theme. That also means the canvas can never
 * drift from the HTML around it, and a customer who re-points a token in their
 * own theme gets it in the charts for free.
 *
 * Identity is never carried by colour alone: the doughnut ships a real HTML
 * legend with label and value, the bars are labelled by their axis, and the
 * trend is a single series. Every card also carries a table of its own numbers
 * for assistive tech - visible if Chart.js could not load, hidden otherwise.
 */
export class AamChart extends Component {
    static template = "odooapp_access_management.AamChart";
    static props = {
        kind: { type: String },                        // donut | bars | trend
        points: { type: Array },                       // [{label, value}]
        title: { type: String },
        // Font Awesome class for the title glyph. The reference design leads
        // every card title with one; it is also the only bit of the title that
        // survives translation unchanged.
        icon: { type: String, optional: true },
        hint: { type: String, optional: true },
        unit: { type: String, optional: true },
        height: { type: Number, optional: true },
        emptyText: { type: String, optional: true },
        // Which categorical slot tints this card. Decoration, not data:
        // these are single-series magnitude charts, so the hue only tells
        // you which card you are looking at.
        accent: { type: Number, optional: true },
    };
    static defaultProps = {
        height: 200, hint: "", unit: "", emptyText: "", accent: 1, icon: "fa-bar-chart",
    };

    setup() {
        this.canvasRef = useRef("canvas");
        // Plain instance fields, not `useState`: `render()` runs inside an
        // effect, and writing reactive state there would loop patch -> effect
        // -> render -> patch.
        this.chart = null;
        this.libOk = false;
        this.state = useState({ failed: false });

        onWillStart(async () => {
            try {
                await loadBundle("web.chartjs_lib");
                this.libOk = true;
            } catch {
                // No network, or the bundle is unavailable. The table below the
                // canvas becomes the card's visible content.
                this.state.failed = true;
            }
        });

        useEffect(
            () => {
                this.render_();
                // Returning the teardown covers unmount *and* every re-apply,
                // so no separate onWillUnmount is needed.
                return () => {
                    this.chart?.destroy();
                    this.chart = null;
                };
            },
            // A content signature, not object identity: a caller that computes
            // its points in a getter would otherwise hand us a new array on
            // every unrelated patch and the chart would rebuild each time.
            () => [JSON.stringify(this.props.points), this.props.kind]
        );
    }

    get hasData() {
        return (this.props.points || []).some((point) => point.value);
    }

    get total() {
        return (this.props.points || []).reduce((sum, point) => sum + (point.value || 0), 0);
    }

    /** Legend rows for the doughnut - the direct labelling that keeps identity
     *  off colour. */
    get legend() {
        const total = this.total || 1;
        return (this.props.points || []).map((point, index) => ({
            label: point.label,
            value: point.value,
            pct: Math.round((point.value * 100) / total),
            slot: (index % 3) + 1,
        }));
    }

    /** A one-line description of the whole chart, for a screen reader that
     *  skips the table. */
    get ariaLabel() {
        const body = (this.props.points || [])
            .map((point) => `${point.label} ${point.value}`)
            .join(", ");
        return `${this.props.title}: ${body || _t("no data")}`;
    }

    /** The current theme, straight from the tokens the surrounding HTML uses. */
    get theme() {
        const style = getComputedStyle(this.canvasRef.el);
        const token = (name, fallback) =>
            style.getPropertyValue(name).trim() || fallback;
        return {
            cat: [token("--aam-cat-1", "#4F46E5"), token("--aam-cat-2", "#0891B2"),
                  token("--aam-cat-3", "#E54690")],
            fill: token(`--aam-cat-${this.props.accent}`, "#4F46E5"),
            fillSoft: this.softFill(token(`--aam-cat-${this.props.accent}`, "#4F46E5")),
            surface: token("--aam-surface", "#FFFFFF"),
            ink: token("--aam-ink", "#111827"),
            inkMute: token("--aam-ink-mute", "#6B7280"),
            grid: token("--aam-line-soft", "#EEF0F3"),
        };
    }

    /** The card's own accent at low alpha, for an area fill that belongs to its
     *  line. This used to be a fixed `--aam-d2`, which put a pink trend line on
     *  an indigo wash - two hues in a chart that has one series. */
    softFill(hex) {
        const match = /^#?([0-9a-f]{6})$/i.exec(String(hex).trim());
        if (!match) {
            return "rgba(79, 70, 229, .18)";
        }
        const value = parseInt(match[1], 16);
        // eslint-disable-next-line no-bitwise
        return `rgba(${(value >> 16) & 255}, ${(value >> 8) & 255}, ${value & 255}, .18)`;
    }

    render_() {
        this.chart?.destroy();
        this.chart = null;
        if (!this.libOk || !this.canvasRef.el || !this.hasData) {
            return;
        }
        const theme = this.theme;
        const labels = this.props.points.map((point) => point.label);
        const values = this.props.points.map((point) => point.value);

        const base = {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 260 },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: theme.ink,
                    borderWidth: 0,
                    cornerRadius: 6,
                    padding: 10,
                    displayColors: false,
                    callbacks: {
                        label: (item) =>
                            ` ${item.label || item.dataset.label}: ${item.formattedValue}`,
                    },
                },
            },
        };

        const config = this[`config_${this.props.kind}`](theme, labels, values, base);
        this.chart = new Chart(this.canvasRef.el, config);
    }

    config_donut(theme, labels, values, base) {
        return {
            type: "doughnut",
            data: {
                labels,
                datasets: [{
                    data: values,
                    backgroundColor: values.map((_v, i) => theme.cat[i % 3]),
                    // A ring of surface between slices: the 2px gap is what
                    // separates two adjacent hues for a colour-blind reader.
                    borderColor: theme.surface,
                    borderWidth: 2,
                    hoverOffset: 6,
                }],
            },
            options: { ...base, cutout: "64%" },
        };
    }

    config_bars(theme, labels, values, base) {
        return {
            type: "bar",
            data: {
                labels,
                // Six labelled bars need ONE hue, not six. The axis carries
                // identity; a second encoding would only add noise.
                datasets: [{
                    data: values,
                    backgroundColor: theme.fill,
                    borderRadius: 4,
                    borderSkipped: false,
                    barThickness: 14,
                }],
            },
            options: {
                ...base,
                indexAxis: "y",
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: { color: theme.inkMute, font: { size: 10 }, precision: 0 },
                        grid: { color: theme.grid },
                        border: { display: false },
                    },
                    y: {
                        ticks: { color: theme.inkMute, font: { size: 11 } },
                        grid: { display: false },
                        border: { display: false },
                    },
                },
            },
        };
    }

    config_trend(theme, labels, values, base) {
        return {
            type: "line",
            data: {
                labels,
                datasets: [{
                    data: values,
                    borderColor: theme.fill,
                    backgroundColor: theme.fillSoft,
                    fill: true,
                    tension: 0.35,
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 5,
                    pointBackgroundColor: theme.fill,
                    pointHoverBorderColor: theme.surface,
                    pointHoverBorderWidth: 2,
                }],
            },
            options: {
                ...base,
                scales: {
                    x: {
                        ticks: { color: theme.inkMute, font: { size: 10 } },
                        grid: { display: false },
                        border: { display: false },
                    },
                    y: {
                        beginAtZero: true,
                        ticks: { color: theme.inkMute, font: { size: 10 }, precision: 0 },
                        grid: { color: theme.grid },
                        border: { display: false },
                    },
                },
            },
        };
    }
}
