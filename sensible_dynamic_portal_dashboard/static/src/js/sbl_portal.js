/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { _t } from "@web/core/l10n/translation";
import { loadBundle } from "@web/core/assets";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.sblPieChart = publicWidget.Widget.extend({
    selector: '#sc_dashboard_charts',

    willStart: async function () {
        await loadBundle("web.chartjs_lib");
    },

    start: async function () {
        this.rpc = rpc;
        await this._super(...arguments);

        // Initial render
        await this.renderChartByType('pie');

        // Listen to chart selector dropdown
        const selector = document.getElementById('sc_chart_selector');
        if (selector) {
            selector.addEventListener('change', async (e) => {
                const selectedType = e.target.value;
                await this.renderChartByType(selectedType);
            });
        }
    },

    async renderChartByType(type) {
        const allChartIds = [
            'sbl_pie_chart_canvas',
            'sbl_bar_chart_canvas',
            'sbl_line_chart_canvas',
            'sbl_radar_chart_canvas',
            'sbl_doughnut_chart_canvas'
        ];

        // Destroy existing charts
        allChartIds.forEach(id => {
            const el = document.getElementById(id);
            if (el && el.chartInstance) {
                el.chartInstance.destroy();
                el.chartInstance = null;
            }
        });

        // Hide all chart containers
        const chartContainers = document.querySelectorAll('#sc_dashboard_charts .col-6');
        chartContainers.forEach(div => div.style.display = 'none');

        const containerMap = {
            pie: 'sbl_portal_dashboard_pie_chart',
            bar: 'sbl_portal_dashboard_bar_chart',
            line: 'sbl_portal_dashboard_line_chart',
            radar: 'sbl_portal_dashboard_radar_chart',
            doughnut: 'sbl_portal_dashboard_doughnut_chart',
        };

        if (type === 'all') {
            for (const [chartType, containerId] of Object.entries(containerMap)) {
                const container = document.getElementById(containerId);
                if (container) container.style.display = 'block';

                const methodName = `create${this.capitalize(chartType)}Chart`;
                if (typeof this[methodName] === 'function') {
                    await this[methodName]();
                } else {
                    console.warn(`Method ${methodName} not found`);
                }
            }
        } else {
            const containerId = containerMap[type];
            const showEl = document.getElementById(containerId);
            if (showEl) {
                showEl.style.display = 'block';
            }

            switch (type) {
                case 'pie': await this.createPieChart(); break;
                case 'bar': await this.createBarChart(); break;
                case 'line': await this.createLineChart(); break;
                case 'radar': await this.createRadarChart(); break;
                case 'doughnut': await this.createDoughnutChart(); break;
            }
        }
    },

    capitalize(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    },

    async fetchChartData(canvasId, containerId) {
        const canvas = document.getElementById(canvasId);
        const container = document.getElementById(containerId);
        if (!canvas || !container) {
            console.warn(`Missing canvas or container for ${canvasId}`);
            return null;
        }
        const recordId = container.dataset.record_id;
        if (!recordId) return null;

        const data = await this.rpc('/get_chart_info', {
            sbl_dynamic_portal_id: recordId,
        });
        return { canvas, data };
    },

    async createPieChart() {
        const result = await this.fetchChartData('sbl_pie_chart_canvas', 'sbl_portal_dashboard_pie_chart');
        if (!result) return;
        const { canvas, data } = result;

        const chart = new Chart(canvas, {
            type: 'pie',
            data: {
                labels: data.map(d => d.label),
                datasets: [{
                    data: data.map(d => d.value),
                    backgroundColor: data.map(d => d.backgroundColor),
                    label: _t('Data')
                }]
            },
            options: {
                responsive: true,
                aspectRatio: 2,
            }
        });
        canvas.chartInstance = chart;
    },

    async createBarChart() {
        const result = await this.fetchChartData('sbl_bar_chart_canvas', 'sbl_portal_dashboard_bar_chart');
        if (!result) return;
        const { canvas, data } = result;

        const chart = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: data.map(d => d.label),
                datasets: [{
                    label: '',
                    data: data.map(d => d.value),
                    backgroundColor: data.map(d => d.backgroundColor)
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    tooltip: {
                        callbacks: {
                            title: items => items[0].label,
                            label: item => _t('Count') + ': ' + item.raw
                        }
                    },
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { precision: 0 }
                    }
                }
            }
        });
        canvas.chartInstance = chart;
    },

    async createLineChart() {
        const result = await this.fetchChartData('sbl_line_chart_canvas', 'sbl_portal_dashboard_line_chart');
        if (!result) return;
        const { canvas, data } = result;

        const colors = data.map(d => d.backgroundColor || '#3e95cd');
        const chart = new Chart(canvas, {
            type: 'line',
            data: {
                labels: data.map(d => d.label),
                datasets: [{
                    label: '',
                    data: data.map(d => d.value),
                    fill: false,
                    borderColor: 'black',
                    tension: 0.1,
                    pointBackgroundColor: colors,
                    pointBorderColor: colors,
                    pointRadius: 6,
                    pointHoverRadius: 8
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    tooltip: {
                        callbacks: {
                            title: items => items[0].label,
                            label: item => _t('Count') + ': ' + item.raw
                        }
                    },
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { precision: 0 }
                    }
                }
            }
        });
        canvas.chartInstance = chart;
    },

    async createRadarChart() {
        const result = await this.fetchChartData('sbl_radar_chart_canvas', 'sbl_portal_dashboard_radar_chart');
        if (!result) return;
        const { canvas, data } = result;

        const colors = data.map(d => d.backgroundColor || '#3e95cd');
        const chart = new Chart(canvas, {
            type: 'radar',
            data: {
                labels: data.map(d => d.label),
                datasets: [{
                    label: _t('KPIs'),
                    data: data.map(d => d.value),
                    fill: true,
                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    pointBackgroundColor: colors,
                    pointBorderColor: colors,
                    pointRadius: 6,
                    pointHoverRadius: 8
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    tooltip: {
                        callbacks: {
                            title: items => items[0].label,
                            label: item => _t('Count') + ': ' + item.raw
                        }
                    },
                    legend: { display: false }
                },
                scales: {
                    r: {
                        beginAtZero: true,
                        ticks: { precision: 0 }
                    }
                }
            }
        });
        canvas.chartInstance = chart;
    },

    async createDoughnutChart() {
        const result = await this.fetchChartData('sbl_doughnut_chart_canvas', 'sbl_portal_dashboard_doughnut_chart');
        if (!result) return;
        const { canvas, data } = result;

        const chart = new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: data.map(d => d.label),
                datasets: [{
                    data: data.map(d => d.value),
                    backgroundColor: data.map(d => d.backgroundColor),
                    label: _t('Data')
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    tooltip: {
                        callbacks: {
                            title: items => items[0].label,
                            label: item => _t('Count') + ': ' + item.raw
                        }
                    },
                    legend: {
                        display: true,
                        position: 'bottom'
                    }
                }
            }
        });
        canvas.chartInstance = chart;
    }
});
