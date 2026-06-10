/** @odoo-module **/

import { Component, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { useService, useBus } from "@web/core/utils/hooks";
import { Domain } from "@web/core/domain";
import { humanNumber } from "@web/core/utils/numbers";

// Fallback palette used when a card declares no `color`. Cards are coloured by
// position so a dashboard with no colours still looks varied and intentional.
const DEFAULT_PALETTE = [
    "#0d6efd", // blue
    "#198754", // green
    "#fd7e14", // orange
    "#d63384", // pink
    "#6f42c1", // purple
    "#0dcaf0", // cyan
    "#ffc107", // amber
    "#20c997", // teal
];

export class ListDashboard extends Component {
    static template = "ispg_list_view_dashboard.ListDashboard";
    static props = {
        config: Object,
        model: Object,
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            rows: [],
            loading: true,
        });
        onWillStart(async () => {
            await this.loadDashboardData();
        });
        onWillUpdateProps(async () => {
            await this.loadDashboardData();
        });
        // Recompute whenever the search changes (filters added/removed) so the
        // cards always reflect the records currently shown in the view.
        if (this.env.searchModel) {
            useBus(this.env.searchModel, "update", () => this.loadDashboardData());
        }
    }

    /**
     * Domain of the records currently shown in the view - i.e. the active
     * search filters - but EXCLUDING this dashboard's own card-click facet, so
     * selecting a card filters the list without collapsing the other cards.
     */
    get baseDomain() {
        const searchModel = this.env.searchModel;
        if (searchModel) {
            try {
                const domains = [searchModel.globalDomain];
                for (const group of searchModel._getGroups()) {
                    const groupDomains = [];
                    for (const activeItem of group.activeItems) {
                        const item = searchModel.searchItems[activeItem.searchItemId];
                        if (item && item.isIspgDashboardFilter) {
                            continue; // skip our own card facets
                        }
                        const domain = searchModel._getSearchItemDomain(activeItem);
                        if (domain) {
                            groupDomains.push(domain);
                        }
                    }
                    if (groupDomains.length) {
                        domains.push(Domain.or(groupDomains));
                    }
                }
                return Domain.and(domains).toList(searchModel.domainEvalContext);
            } catch {
                // Fall back to the list's own domain on any internal API change.
            }
        }
        return this.props.model?.domain || [];
    }

    /**
     * Resolve a single value for a card: either agg(measure) when a measure is
     * configured, or a plain record count otherwise.
     */
    async computeValue(modelName, domain, card) {
        if (card.measure) {
            // Odoo 18 read_group: aggregate spec passed as a `fields` entry,
            // empty groupby aggregates over the whole domain, and the result is
            // keyed by the bare field name (not the "field:agg" spec).
            const spec = `${card.measure}:${card.aggregate || "sum"}`;
            const groups = await this.orm.readGroup(modelName, domain, [spec], []);
            return (groups[0] && groups[0][card.measure]) || 0;
        }
        return this.orm.searchCount(modelName, domain);
    }

    /** Format a value for display: humanized number, optional unit symbol. */
    formatValue(value, card) {
        const symbol = card.symbol || "";
        if (card.measure) {
            // Monetary / float measures: humanize (1.2k, 3.4M) for compactness.
            const formatted = humanNumber(value, { decimals: 1 });
            return symbol ? `${symbol}${formatted}` : formatted;
        }
        // Counts stay exact; only humanize very large ones.
        const formatted = value >= 100000 ? humanNumber(value) : String(value);
        return symbol ? `${symbol}${formatted}` : formatted;
    }

    /**
     * Classify the `icon` value: a FontAwesome class, or an image URL/path
     * (png / svg / jpg / data-uri / http / absolute path).
     */
    classifyIcon(icon) {
        const value = (icon || "").trim();
        if (!value) {
            return { type: "" };
        }
        const looksLikeImage =
            /^(https?:|data:|\/)/.test(value) ||
            /\.(png|svg|jpe?g|gif|webp|ico|bmp)(\?.*)?$/i.test(value);
        if (looksLikeImage) {
            return { type: "image", src: value };
        }
        return { type: "fa", class: value };
    }

    /** Compute the displayable data for one card config. */
    async computeCard(modelName, baseDomain, cardConfig, key, paletteIndex) {
        const cardDomain = [...baseDomain, ...(cardConfig.domain || [])];
        const icon = this.classifyIcon(cardConfig.icon);
        const base = {
            key: key,
            title: cardConfig.title || "KPI",
            // User-provided colour, or a deterministic palette colour.
            color: cardConfig.color || DEFAULT_PALETTE[paletteIndex % DEFAULT_PALETTE.length],
            iconType: icon.type,
            iconClass: icon.class || "",
            iconSrc: icon.src || "",
            domain: cardConfig.domain || [],
        };
        try {
            const value = await this.computeValue(modelName, cardDomain, cardConfig);
            return { ...base, display: this.formatValue(value, cardConfig) };
        } catch (err) {
            console.error(`Failed to compute KPI card "${cardConfig.title}"`, err);
            return { ...base, display: "—" };
        }
    }

    async loadDashboardData() {
        if (!this.props.model || !this.props.config || !this.props.config.rows) {
            return;
        }
        this.state.loading = true;
        const modelName = this.props.model.resModel;
        const baseDomain = this.baseDomain;

        // Palette index runs continuously across rows so colours stay varied.
        let paletteIndex = 0;
        const rows = await Promise.all(
            this.props.config.rows.map(async (row, rowIndex) => ({
                title: row.title || "",
                cards: await Promise.all(
                    row.cards.map((cardConfig, cardIndex) =>
                        this.computeCard(
                            modelName,
                            baseDomain,
                            cardConfig,
                            `${rowIndex}_${cardIndex}`,
                            paletteIndex++
                        )
                    )
                ),
            }))
        );

        this.state.rows = rows;
        this.state.loading = false;
    }

    /** Remove every search facet this dashboard previously added. */
    clearDashboardFilters() {
        const searchModel = this.env.searchModel;
        if (!searchModel) {
            return;
        }
        const groupIds = new Set();
        for (const queryElem of searchModel.query) {
            const item = searchModel.searchItems[queryElem.searchItemId];
            if (item && item.isIspgDashboardFilter) {
                groupIds.add(item.groupId);
            }
        }
        groupIds.forEach((groupId) => searchModel.deactivateGroup(groupId));
    }

    /**
     * Whether this card's filter is currently applied. Derived from the live
     * search query (not local state) so it survives reloads and reflects the
     * facet being removed manually from the search bar.
     */
    isActive(card) {
        const searchModel = this.env.searchModel;
        if (!searchModel) {
            return false;
        }
        return searchModel.query.some((queryElem) => {
            const item = searchModel.searchItems[queryElem.searchItemId];
            return item && item.ispgDashboardKey === card.key;
        });
    }

    /**
     * Filter the list to the records behind a card, as a single removable
     * search facet. Clicking the active card clears it (toggle); clicking
     * another replaces it. Never stacks duplicate facets.
     */
    applyCardFilter(card) {
        const searchModel = this.env.searchModel;
        if (!searchModel) {
            return;
        }
        const wasActive = this.isActive(card);

        // Drop any facet we previously added (robust against repeated clicks).
        this.clearDashboardFilters();

        // Re-clicking the active card just clears it.
        if (wasActive) {
            return;
        }

        searchModel.createNewFilters([
            {
                description: card.title,
                domain: new Domain(card.domain || []).toString(),
                // Keep this out of the "Filters" dropdown (it still shows as a
                // removable facet) - same approach as Odoo's own click filters.
                invisible: "True",
                // Markers so we can recognise and clean up our own facets.
                isIspgDashboardFilter: true,
                ispgDashboardKey: card.key,
            },
        ]);
    }
}
