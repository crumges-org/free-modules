import { registry } from "@web/core/registry";
import { waitUntil } from "@odoo/hoot-dom";

/**
 * Odoo 18 has no `canvasNotEmpty` tour helper - it arrives in 19
 * (web_tour/static/src/js/tour_automatic/tour_helpers_hoot.js:290), and the whole
 * `js/` subtree is a v19 reorganisation. Same check, inline: read the bitmap back
 * and wait for one non-transparent pixel.
 *
 * NOT dropped and NOT downgraded to a plain trigger assertion. The <canvas> is in
 * the template unconditionally, and aam_chart.js turns a failed `loadBundle` into
 * `state.failed` and renders the fallback table - so anything short of reading the
 * pixels back passes on a chart that was never drawn. This is the only coverage
 * Chart.js has anywhere in the module.
 *
 * `this.anchor` is the element matched by `trigger`: tour_step_automatic.js calls
 * `this.run.call({ anchor: this.element }, actionHelper)` identically on both
 * versions. The 3s timeout replaces hoot's 200ms default, which sits uncomfortably
 * close to the 260ms chart animation on a box also running the Odoo server.
 */
async function canvasNotEmpty() {
    const canvas = this.anchor;
    if (canvas.tagName.toLowerCase() !== "canvas") {
        throw new Error("canvasNotEmpty is only suitable for canvas elements.");
    }
    await waitUntil(
        () => {
            // A card not yet laid out has a 0x0 backing store, and
            // getImageData(0, 0, 0, 0) throws IndexSizeError instead of waiting.
            if (!canvas.width || !canvas.height) {
                return false;
            }
            const imageData = canvas
                .getContext("2d")
                .getImageData(0, 0, canvas.width, canvas.height);
            return new Uint32Array(imageData.data.buffer).some((pixel) => pixel !== 0);
        },
        { timeout: 3000, message: "Chart.js never painted a pixel on this canvas" }
    );
}


/**
 * The dashboard is an OWL client action, and Python tests never render OWL.
 * A broken template, a renamed field on `aam.dashboard`, or an exception in
 * `load()` all pass the whole unit suite and still leave users staring at a
 * blank page - so this tour asserts every region of the screen actually
 * appears, then exercises the two things that re-render it.
 *
 * Fixtures come from `tests/test_tours.py`: a rule on `res.partner` guarantees
 * the restriction matrix has at least one row.
 */
registry.category("web_tour.tours").add("aam_dashboard_tour", {
    url: "/odoo/action-odooapp_access_management.action_aam_dashboard",
    steps: () => [
        {
            content: "The client action mounted",
            trigger: ".o_aam_dashboard .o_aam_statusbar h1:contains(Access Management)",
        },
        {
            // The verdict only renders once `state.data` is set, so this is
            // also the assertion that get_dashboard_data returned.
            content: "get_dashboard_data resolved",
            trigger: ".o_aam_dashboard .o_aam_verdict strong",
        },
        {
            content: "Count tiles render",
            trigger: ".o_aam_counts .o_aam_count .o_aam_count_value",
        },
        {
            content: "The restriction matrix section renders",
            trigger: ".o_aam_matrix_wrap .o_aam_matrix_head h2:contains(Restriction map)",
        },
        {
            content: "get_heatmap_data put the seeded model on the matrix",
            trigger: ".o_aam_matrix tbody .o_aam_rowhead a:contains(res.partner)",
        },
        {
            content: "A heat cell carries its density band",
            trigger: ".o_aam_matrix tbody td.o_aam_cell.o_aam_l1, .o_aam_matrix tbody td.o_aam_cell.o_aam_l2",
        },
        {
            content: "The chart band renders all three cards",
            trigger: ".o_aam_charts .o_aam_chart_card:eq(2)",
        },
        {
            // The only thing that proves Chart.js actually ran: `canvasNotEmpty`
            // reads the bitmap back with getImageData and waits for a lit pixel.
            // Selected by `data-chart`, never by title text - this module ships
            // five translations and a `:contains` would break under any of them.
            content: "Chart.js painted the target doughnut",
            trigger: ".o_aam_chart_card[data-chart='donut'] canvas",
            run: canvasNotEmpty,
        },
        {
            content: "…the family bars",
            trigger: ".o_aam_chart_card[data-chart='bars'] canvas",
            run: canvasNotEmpty,
        },
        {
            content: "…and the creation trend",
            trigger: ".o_aam_chart_card[data-chart='trend'] canvas",
            run: canvasNotEmpty,
        },
        {
            // A canvas full of pixels proves nothing about labels. The legend is
            // real HTML, so it is what proves identity is not carried by colour.
            content: "The doughnut is directly labelled, not colour-coded",
            trigger: ".o_aam_chart_card[data-chart='donut'] .o_aam_chart_legend li b",
        },
        {
            // `visually-hidden` is a 1x1 clip, not display:none, so hoot's
            // visibility check still accepts it.
            content: "Every chart carries its own numbers for assistive tech",
            trigger: ".o_aam_chart_card[data-chart='bars'] table.o_aam_chart_table",
        },
        {
            content: "The insight panel renders its facts",
            trigger: ".o_aam_panel:contains(What needs attention) .o_aam_facts li:contains(Administrators protected)",
        },
        {
            content: "The activity panel renders",
            trigger: ".o_aam_panel:contains(Recent activity)",
        },
        {
            content: "Refresh re-runs both RPCs",
            trigger: ".o_aam_statusbar button:contains(Refresh)",
            run: "click",
        },
        {
            content: "…and the screen comes back",
            trigger: ".o_aam_dashboard .o_aam_verdict strong",
        },
        {
            // The regression guard for the useEffect wiring: a refresh must
            // rebuild the charts, not leave three dead canvases behind.
            content: "Refresh rebuilt the charts",
            trigger: ".o_aam_chart_card[data-chart='trend'] canvas",
            run: canvasNotEmpty,
        },
        {
            content: "A tile drills through to the rules it counts",
            trigger: ".o_aam_counts .o_aam_count:first",
            run: "click",
        },
        {
            content: "The rules list opened",
            trigger: ".o_list_view .o_data_row",
        },
        {
            content: "Back to the dashboard",
            trigger: ".o_breadcrumb .o_back_button",
            run: "click",
        },
        {
            content: "A model name on the matrix opens the rules touching it",
            trigger: ".o_aam_matrix tbody .o_aam_rowhead a:contains(res.partner)",
            run: "click",
        },
        {
            content: "The filtered rules list opened",
            trigger: ".o_list_view .o_data_row",
        },
    ],
});
