/** @odoo-module **/

import { Component, useState, useRef, onMounted, onWillStart, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

// ========================================================================
//  Unique ID helper
// ========================================================================
let _uid = 0;
function uid() {
    return "blk_" + Date.now().toString(36) + "_" + (++_uid);
}

// ========================================================================
//  BLOCK_META – labels, icons, categories
// ========================================================================
const BLOCK_META = {
    company_header:  { label: _t("Company Header"),       icon: "fa-building-o",       cat: "header" },
    sender_line:     { label: _t("Sender Line"),           icon: "fa-ellipsis-h",       cat: "header" },
    company_details: { label: _t("Company Details"),       icon: "fa-id-card-o",        cat: "header" },
    document_title:  { label: _t("Document Title"),        icon: "fa-header",           cat: "header" },
    partner_address: { label: _t("Recipient Address"),     icon: "fa-address-card-o",   cat: "header" },
    intro_text:      { label: _t("Introduction Text"),     icon: "fa-comment-o",        cat: "content" },
    info_table:      { label: _t("Info Table"),            icon: "fa-info-circle",      cat: "content" },
    line_items:      { label: _t("Line Items"),            icon: "fa-table",            cat: "content" },
    subtotals:       { label: _t("Totals / Taxes"),        icon: "fa-calculator",       cat: "content" },
    notes:           { label: _t("Payment & Shipping Info"), icon: "fa-sticky-note-o",  cat: "content" },
    free_text:       { label: _t("Free Text"),             icon: "fa-font",             cat: "content" },
    footer:          { label: _t("Footer"),                icon: "fa-window-minimize",  cat: "footer" },
    two_columns:     { label: _t("Two Columns"),           icon: "fa-columns",          cat: "layout" },
    separator:       { label: _t("Separator"),             icon: "fa-minus",            cat: "layout" },
    spacer:          { label: _t("Spacer"),                icon: "fa-arrows-v",         cat: "layout" },
    page_break:      { label: _t("Page Break"),            icon: "fa-file-o",           cat: "layout" },
};

const CATEGORIES = [
    { key: "header",  label: _t("Header") },
    { key: "content", label: _t("Content") },
    { key: "footer",  label: _t("Footer") },
    { key: "layout",  label: _t("Layout") },
];

const COLUMN_FORBIDDEN_TYPES = new Set(["two_columns", "page_break"]);

const LINE_ITEM_COLUMNS = [
    { id: "position",    label: _t("Position No."),  defaultLabel: _t("Pos.") },
    { id: "sku",          label: _t("SKU"),           defaultLabel: _t("SKU") },
    { id: "product",     label: _t("Product"),       defaultLabel: _t("Product") },
    { id: "description", label: _t("Description"),   defaultLabel: _t("Description") },
    { id: "quantity",    label: _t("Quantity"),       defaultLabel: _t("Quantity") },
    { id: "uom",         label: _t("Unit"),           defaultLabel: _t("Unit") },
    { id: "price_unit",  label: _t("Unit Price"),     defaultLabel: _t("Unit Price") },
    { id: "discount",    label: _t("Discount"),       defaultLabel: _t("Discount %") },
    { id: "taxes",       label: _t("Taxes"),          defaultLabel: _t("Taxes") },
    { id: "subtotal",    label: _t("Subtotal"),       defaultLabel: _t("Subtotal") },
];

const DEFAULT_COLUMN_ORDER = LINE_ITEM_COLUMNS.map((c) => c.id);

// ========================================================================
//  PROPERTY DEFINITIONS per block type
// ========================================================================
const _LH_OPTIONS = [
    { value: "1.0", label: _t("1.0 – Tight") }, { value: "1.2", label: _t("1.2 – Compact") },
    { value: "1.4", label: _t("1.4 – Normal") }, { value: "1.6", label: _t("1.6 – Wide") },
    { value: "1.8", label: _t("1.8 – Very wide") }, { value: "2.0", label: _t("2.0 – Double") },
];
const _ALIGN_OPTIONS = [
    { value: "left", label: _t("Align left") }, { value: "center", label: _t("Align center") }, { value: "right", label: _t("Align right") },
];

const BLOCK_PROPERTIES = {
    company_header: [
        { key: "show_logo",            label: _t("Show logo"),          type: "boolean" },
        { key: "show_company_name",    label: _t("Show company name"), type: "boolean" },
        { key: "show_company_address", label: _t("Show address"),      type: "boolean" },
        { key: "logo_position",        label: _t("Logo position"),     type: "select", options: [
            { value: "left", label: _t("Logo left") }, { value: "right", label: _t("Logo right") }, { value: "top", label: _t("Logo top") }] },
        { key: "line_height", label: _t("Line height"), type: "select", options: _LH_OPTIONS },
    ],
    document_title: [
        { key: "display_mode", label: _t("Display"), type: "select", options: [
            { value: "type_and_number", label: _t("Document type + number") },
            { value: "type_only", label: _t("Type only") },
            { value: "number_only", label: _t("Number only") },
            { value: "custom", label: _t("Custom text") }] },
        { key: "custom_label", label: _t("Custom title / document type"), type: "text" },
        { key: "font_size",  label: _t("Font size (px)"), type: "text" },
        { key: "bold",       label: _t("Bold"),            type: "boolean" },
        { key: "alignment",  label: _t("Alignment"),       type: "select", options: _ALIGN_OPTIONS },
        { key: "line_height", label: _t("Line height"), type: "select", options: _LH_OPTIONS },
    ],
    sender_line: [
        { key: "separator",  label: _t("Separator"),       type: "text" },
        { key: "font_size",  label: _t("Font size (px)"),  type: "text" },
        { key: "show_name",  label: _t("Company name"),    type: "boolean" },
        { key: "show_street", label: _t("Street"),          type: "boolean" },
        { key: "show_city",  label: _t("ZIP / City"),       type: "boolean" },
        { key: "show_phone", label: _t("Phone"),            type: "boolean" },
        { key: "show_email", label: _t("Email"),            type: "boolean" },
    ],
    company_details: [
        { key: "font_size",     label: _t("Font size (px)"),  type: "text" },
        { key: "line_height", label: _t("Line height"), type: "select", options: _LH_OPTIONS },
        { key: "show_name",     label: _t("Company name"),    type: "boolean" },
        { key: "show_address",  label: _t("Address"),         type: "boolean" },
        { key: "show_phone",    label: _t("Phone"),           type: "boolean" },
        { key: "show_fax",      label: _t("Fax"),             type: "boolean" },
        { key: "show_email",    label: _t("Email"),           type: "boolean" },
        { key: "show_website",  label: _t("Website"),         type: "boolean" },
        { key: "show_vat",      label: _t("VAT ID"),          type: "boolean" },
        { key: "show_company_registry", label: _t("Company registry"), type: "boolean" },
        { key: "show_bank",     label: _t("Bank details"),    type: "boolean" },
    ],
    partner_address: [
        { key: "use_shipping", label: _t("Use shipping address"), type: "boolean" },
        { key: "show_vat",     label: _t("Show VAT ID"),         type: "boolean" },
        { key: "font_size",    label: _t("Font size (px)"),      type: "text" },
        { key: "line_height",  label: _t("Line height"), type: "select", options: _LH_OPTIONS },
    ],
    intro_text: [
        { key: "salutation", label: _t("Salutation"), type: "textarea" },
        { key: "body",       label: _t("Introduction text"), type: "textarea" },
        { key: "font_size",  label: _t("Font size (px)"), type: "text" },
        { key: "line_height", label: _t("Line height"), type: "select", options: _LH_OPTIONS },
    ],
    info_table: [
        { key: "font_size",            label: _t("Font size (px)"),   type: "text" },
        { key: "line_height", label: _t("Line height"), type: "select", options: _LH_OPTIONS },
        { key: "columns",              label: _t("Columns (1-4)"),    type: "text" },
        { key: "show_number",          label: _t("Number"),           type: "boolean" },
        { key: "label_number",         label: _t("↳ Label"),          type: "text" },
        { key: "show_date",            label: _t("Date"),             type: "boolean" },
        { key: "label_date",           label: _t("↳ Label"),          type: "text" },
        { key: "show_reference",       label: _t("Reference"),        type: "boolean" },
        { key: "label_reference",      label: _t("↳ Label"),          type: "text" },
        { key: "show_payment_term",    label: _t("Payment terms"),    type: "boolean" },
        { key: "label_payment_term",   label: _t("↳ Label"),          type: "text" },
        { key: "show_salesperson",     label: _t("Salesperson"),      type: "boolean" },
        { key: "label_salesperson",    label: _t("↳ Label"),          type: "text" },
        { key: "show_salesperson_email", label: _t("Salesperson email"), type: "boolean" },
        { key: "label_salesperson_email", label: _t("↳ Label"),       type: "text" },
        { key: "show_customer_number", label: _t("Customer number"),  type: "boolean" },
        { key: "label_customer_number", label: _t("↳ Label"),         type: "text" },
    ],
    line_items: [
        { key: "table_style", label: _t("Table design"), type: "select", options: [
            { value: "minimal", label: _t("Minimal (header/separator lines only)") },
            { value: "bordered", label: _t("Bordered") },
            { value: "striped", label: _t("Striped rows") },
            { value: "striped_bordered", label: _t("Striped rows + borders") },
            { value: "clean", label: _t("No lines") }] },
        { key: "header_bg", label: _t("Header background"), type: "color" },
        { key: "header_fg", label: _t("Header text color"), type: "color" },
        { key: "stripe_color", label: _t("Stripe color"), type: "color" },
        { key: "font_size", label: _t("Font size (px)"), type: "text" },
        { key: "line_height", label: _t("Line height"), type: "select", options: _LH_OPTIONS },
    ],
    subtotals: [
        { key: "show_tax_details", label: _t("Tax details"), type: "boolean" },
        { key: "show_residual",    label: _t("Show amount due"), type: "boolean" },
        { key: "full_width",       label: _t("Full width"), type: "boolean" },
        { key: "alignment",        label: _t("Alignment"),  type: "select", options: [
            { value: "left", label: _t("Align left") }, { value: "right", label: _t("Align right") }] },
        { key: "table_style", label: _t("Table design"), type: "select", options: [
            { value: "minimal",  label: _t("Minimal (total line only)") },
            { value: "bordered", label: _t("Bordered") },
            { value: "clean",    label: _t("No lines") },
            { value: "striped",  label: _t("Alternating rows") }] },
        { key: "total_line_style", label: _t("Total separator"), type: "select", options: [
            { value: "double", label: _t("Double") },
            { value: "bold",   label: _t("Bold") },
            { value: "thin",   label: _t("Thin") },
            { value: "none",   label: _t("None") }] },
        { key: "font_size",  label: _t("Font size (px)"), type: "text" },
        { key: "line_height", label: _t("Line height"), type: "select", options: _LH_OPTIONS },
        { key: "header_bg",  label: _t("Total background color"), type: "color" },
        { key: "header_fg",  label: _t("Total text color"), type: "color" },
        { key: "stripe_color", label: _t("Alternating row color"), type: "color" },
        { key: "label_subtotal",  label: _t("Label: Subtotal"), type: "text" },
        { key: "label_tax",       label: _t("Label: Taxes"), type: "text" },
        { key: "label_total",     label: _t("Label: Total"), type: "text" },
        { key: "label_residual",  label: _t("Label: Amount Due"), type: "text" },
    ],
    notes: [
        { key: "show_payment_terms",  label: _t("Show payment terms"), type: "boolean" },
        { key: "label_payment_terms", label: _t("Label: Payment terms"), type: "text" },
        { key: "show_payment_method", label: _t("Show payment method"), type: "boolean" },
        { key: "label_payment_method", label: _t("Label: Payment method"), type: "text" },
        { key: "show_payment_ref",    label: _t("Show payment reference"), type: "boolean" },
        { key: "label_payment_ref",   label: _t("Label: Payment reference"), type: "text" },
        { key: "show_notes",          label: _t("Notes (from document)"), type: "boolean" },
        { key: "shipping_text",       label: _t("Shipping notice"), type: "textarea" },
        { key: "payment_text",        label: _t("Payment notice"), type: "textarea" },
        { key: "custom_text",         label: _t("Additional text"), type: "textarea" },
        { key: "font_size",           label: _t("Font size (px)"), type: "text" },
        { key: "line_height", label: _t("Line height"), type: "select", options: _LH_OPTIONS },
    ],
    free_text: [
        { key: "content",   label: _t("Content (HTML)"),    type: "textarea" },
        { key: "alignment", label: _t("Alignment"),         type: "select", options: _ALIGN_OPTIONS },
        { key: "font_size", label: _t("Font size (px)"),    type: "text" },
        { key: "line_height", label: _t("Line height"), type: "select", options: _LH_OPTIONS },
    ],
    footer: [
        { key: "layout",  label: _t("Layout"), type: "select", options: [
            { value: "columns",  label: _t("Columns (side by side)") },
            { value: "centered", label: _t("Centered") },
            { value: "single",   label: _t("Single line") }] },
        { key: "alignment", label: _t("Alignment"), type: "select", options: _ALIGN_OPTIONS },
        { key: "separator_style", label: _t("Top separator"), type: "select", options: [
            { value: "solid", label: _t("Solid") },
            { value: "dashed", label: _t("Dashed") },
            { value: "none", label: _t("None") }] },
        { key: "separator_color", label: _t("Line color"), type: "color" },
        { key: "show_company_name",  label: _t("Company name"), type: "boolean" },
        { key: "show_address",       label: _t("Address"), type: "boolean" },
        { key: "show_phone",         label: _t("Phone"), type: "boolean" },
        { key: "show_email",         label: _t("Email"), type: "boolean" },
        { key: "show_website",       label: _t("Website"), type: "boolean" },
        { key: "show_vat",           label: _t("VAT ID"), type: "boolean" },
        { key: "show_company_registry", label: _t("Company registry"), type: "boolean" },
        { key: "show_bank",          label: _t("Bank details"), type: "boolean" },
        { key: "show_ceo",           label: _t("CEO"), type: "boolean" },
        { key: "ceo_label",          label: _t("Label: CEO"), type: "text" },
        { key: "ceo_name",           label: _t("CEO name"), type: "text" },
        { key: "custom_left",        label: _t("Custom text (left)"), type: "textarea" },
        { key: "custom_center",      label: _t("Custom text (center)"), type: "textarea" },
        { key: "custom_right",       label: _t("Custom text (right)"), type: "textarea" },
        { key: "show_page_numbers",  label: _t("Page numbers"), type: "boolean" },
        { key: "font_size",          label: _t("Font size (px)"), type: "text" },
        { key: "line_height", label: _t("Line height"), type: "select", options: [
            { value: "1.0", label: _t("1.0 – Tight") }, { value: "1.2", label: _t("1.2 – Compact") },
            { value: "1.4", label: _t("1.4 – Normal") }, { value: "1.6", label: _t("1.6 – Wide") }] },
        { key: "text_color",         label: _t("Text color"), type: "color" },
    ],
    two_columns: [
        { key: "left_ratio", label: _t("Left column (%)"), type: "text" },
    ],
    separator: [
        { key: "style", label: _t("Line style"), type: "select", options: [
            { value: "solid", label: _t("Solid") }, { value: "dashed", label: _t("Dashed") }, { value: "dotted", label: _t("Dotted") }] },
        { key: "color",  label: _t("Color"),        type: "color" },
        { key: "margin", label: _t("Margin (px)"),  type: "text" },
    ],
    spacer: [
        { key: "height", label: _t("Height (px)"), type: "text" },
    ],
    page_break: [],
};

// ========================================================================
//  DEFAULT SETTINGS per block type
// ========================================================================
const DEFAULT_SETTINGS = {
    company_header:  { show_logo: true, show_company_name: true, show_company_address: true, logo_position: "left", line_height: "1.4" },
    sender_line:     { separator: " · ", font_size: "8", show_name: true, show_street: true, show_city: true, show_phone: false, show_email: false },
    company_details: { font_size: "9", line_height: "1.4", show_name: true, show_address: true, show_phone: true, show_fax: false, show_email: true, show_website: true, show_vat: true, show_company_registry: false, show_bank: true },
    document_title:  { display_mode: "type_and_number", custom_label: "", font_size: "20", bold: true, alignment: "left", line_height: "1.2" },
    partner_address: { use_shipping: false, show_vat: true, font_size: "10", line_height: "1.4" },
    intro_text:      { salutation: _t("Dear Sir or Madam,"), body: _t("please find the requested quotation attached:"), font_size: "10", line_height: "1.4" },
    info_table:      { font_size: "10", line_height: "1.2", show_date: true, show_number: true, show_reference: true, show_payment_term: true, show_salesperson: false, show_salesperson_email: false, show_customer_number: false, columns: 2, label_number: _t("Number"), label_date: _t("Date"), label_reference: _t("Reference"), label_payment_term: _t("Payment Terms"), label_salesperson: _t("Salesperson"), label_salesperson_email: _t("Email"), label_customer_number: _t("Customer No.") },
    line_items:      { table_style: "minimal", header_bg: "#000000", header_fg: "#ffffff", stripe_color: "#f8f9fa", font_size: "10", line_height: "1.2", column_order: [...DEFAULT_COLUMN_ORDER], show_position: true, show_sku: false, show_product: true, show_description: true, show_quantity: true, show_uom: true, show_price_unit: true, show_discount: true, show_taxes: false, show_subtotal: true, label_position: _t("Pos."), label_sku: _t("SKU"), label_product: _t("Product"), label_description: _t("Description"), label_quantity: _t("Quantity"), label_uom: _t("Unit"), label_price_unit: _t("Unit Price"), label_discount: _t("Discount %"), label_taxes: _t("Taxes"), label_subtotal: _t("Subtotal") },
    subtotals:       { show_tax_details: true, show_residual: true, full_width: false, alignment: "right", table_style: "minimal", total_line_style: "double", font_size: "10", line_height: "1.2", header_bg: "", header_fg: "", stripe_color: "#f8f9fa", label_subtotal: _t("Subtotal"), label_tax: _t("Taxes"), label_total: _t("Total"), label_residual: _t("Amount Due") },
    notes:           { show_payment_terms: true, label_payment_terms: _t("Payment Terms"), show_payment_method: true, label_payment_method: _t("Payment Method"), show_payment_ref: false, label_payment_ref: _t("Payment Reference"), show_notes: true, shipping_text: "", payment_text: "", custom_text: "", font_size: "10", line_height: "1.4" },
    free_text:       { content: "", alignment: "left", font_size: "12", line_height: "1.4" },
    two_columns:     { left_ratio: 50, left_blocks: [], right_blocks: [] },
    separator:       { style: "solid", color: "#000000", margin: "10" },
    footer:          { layout: "columns", alignment: "left", separator_style: "solid", separator_color: "#cccccc", show_company_name: true, show_address: true, show_phone: true, show_email: true, show_website: false, show_vat: true, show_company_registry: false, show_bank: true, show_ceo: false, ceo_label: _t("CEO"), ceo_name: "", custom_left: "", custom_center: "", custom_right: "", show_page_numbers: true, font_size: "8", line_height: "1.2", text_color: "#666666" },
    spacer:          { height: "20" },
    page_break:      {},
};

// ========================================================================
//  AxolineLayoutEditor – Main OWL Client Action
// ========================================================================
class AxolineLayoutEditor extends Component {
    static template = "axoline_layout_editor.LayoutEditor";
    static props = ["*"];

    setup() {
        this.actionService = useService("action");
        this.notification = useService("notification");

        this.canvasRef = useRef("canvas");

        this.state = useState({
            loading: true,
            saving: false,
            reportName: "",
            modelName: "",
            layoutId: null,
            blocks: [],
            selectedBlockId: null,
            previewUrl: "",
            showPreview: false,
            active: true,
            sampleRecords: [],
            selectedRecordId: null,
            dragState: null,  // { type: 'palette'|'reorder'|'column_reorder', ... }
            dropTargetIndex: null,
            columnDropTarget: null,  // { blockId, side, index }
            // Template system
            showTemplateDialog: false,
            showSaveTemplateDialog: false,
            templates: [],
            templatesLoading: false,
            saveTemplateName: "",
            saveTemplateDescription: "",
            // Template editing mode
            isTemplateMode: false,
            templateName: "",
            // Freemium
            isPro: false,
            proStoreUrl: "",
            // Page margins (mm)
            margins: { top: 10, bottom: 20, left: 7, right: 7 },
        });

        onWillStart(async () => {
            const params = this.props.action?.params || {};
            this.layoutCustomId = params.layout_custom_id;
            this.templateId = params.template_id;
            if (this.templateId) {
                await this.loadTemplate();
            } else if (this.layoutCustomId) {
                await this.loadLayout();
            }
        });

        this._boundOnKeyDown = this._onKeyDown.bind(this);
        onMounted(() => {
            document.addEventListener("keydown", this._boundOnKeyDown);
        });
        onWillUnmount(() => {
            document.removeEventListener("keydown", this._boundOnKeyDown);
        });
    }

    // ------------------------------------------------------------------
    //  Data loading
    // ------------------------------------------------------------------

    async loadLayout() {
        try {
            const data = await rpc("/axoline_layout_editor/load", {
                layout_custom_id: this.layoutCustomId,
            });
            if (data.error) {
                this.notification.add(data.error, { type: "danger" });
                return;
            }
            this.state.reportName = data.report_name || "";
            this.state.modelName = data.model_name || "";
            this.reportTechnicalName = data.report_technical_name || "";
            this.state.layoutId = data.id;
            this.state.blocks = data.layout_json?.blocks || [];
            const m = data.layout_json?.margins;
            if (m) {
                this.state.margins = { top: m.top ?? 10, bottom: m.bottom ?? 20, left: m.left ?? 7, right: m.right ?? 7 };
            }
            this.state.active = data.active;
            this.state.isPro = !!data.is_pro;
            this.state.proStoreUrl = data.pro_store_url || "";
            this.state.loading = false;

            if (!this.state.blocks.length) {
                this.openTemplateDialog();
            }

            // load sample records
            const samples = await rpc("/axoline_layout_editor/get_sample_records", {
                model_name: data.model_name,
                limit: 30,
            });
            this.state.sampleRecords = samples || [];
            if (samples.length) {
                this.state.selectedRecordId = samples[0].id;
            }
        } catch (e) {
            this.state.loading = false;
            this.notification.add(_t("Error loading: ") + String(e), { type: "danger" });
        }
    }

    // ------------------------------------------------------------------
    //  Load template (template editing mode)
    // ------------------------------------------------------------------

    async loadTemplate() {
        try {
            const data = await rpc("/axoline_layout_editor/load_template", {
                template_id: this.templateId,
            });
            if (data.error) {
                this.notification.add(data.error, { type: "danger" });
                return;
            }
            this.state.isTemplateMode = true;
            this.state.templateName = data.template_name || "";
            this.state.reportName = _t("Template: %s", data.template_name || "");
            this.state.modelName = "";
            this.state.layoutId = data.id;
            this.state.blocks = data.layout_json?.blocks || [];
            const m = data.layout_json?.margins;
            if (m) {
                this.state.margins = { top: m.top ?? 10, bottom: m.bottom ?? 20, left: m.left ?? 7, right: m.right ?? 7 };
            }
            this.state.active = true;
            this.state.loading = false;
        } catch (e) {
            this.state.loading = false;
            this.notification.add(_t("Error loading: ") + String(e), { type: "danger" });
        }
    }

    // ------------------------------------------------------------------
    //  Save
    // ------------------------------------------------------------------

    async save() {
        this.state.saving = true;
        try {
            const payload = { version: 1, blocks: this.state.blocks, margins: this.state.margins };
            if (this.state.isTemplateMode) {
                await rpc("/axoline_layout_editor/save_template", {
                    template_id: this.templateId,
                    layout_json: payload,
                });
            } else {
                await rpc("/axoline_layout_editor/save", {
                    layout_custom_id: this.layoutCustomId,
                    layout_json: payload,
                    active: this.state.active,
                });
            }
            this.notification.add(_t("Layout saved!"), { type: "success" });
        } catch (e) {
            this.notification.add(_t("Error saving: ") + String(e), { type: "danger" });
        }
        this.state.saving = false;
    }

    // ------------------------------------------------------------------
    //  Preview
    // ------------------------------------------------------------------

    togglePreview() {
        if (this.state.showPreview) {
            this.state.showPreview = false;
            return;
        }
        this._updatePreviewUrl();
        this.state.showPreview = true;
    }

    _updatePreviewUrl() {
        let url = `/axoline_layout_editor/preview?layout_custom_id=${this.layoutCustomId}`;
        if (this.state.selectedRecordId) {
            url += `&record_id=${this.state.selectedRecordId}`;
        }
        this.state.previewUrl = url + "&_t=" + Date.now();
    }

    onSampleChange(ev) {
        this.state.selectedRecordId = parseInt(ev.target.value) || null;
        if (this.state.showPreview) {
            this._updatePreviewUrl();
        }
    }

    async refreshPreview() {
        await this.save();
        this._updatePreviewUrl();
    }

    async testPrint() {
        const recordId = this.state.selectedRecordId;
        if (!recordId) {
            this.notification.add(_t("Please select a sample record first."), { type: "warning" });
            return;
        }
        await this.save();
        this.actionService.doAction({
            type: "ir.actions.report",
            report_type: "qweb-pdf",
            report_name: this.reportTechnicalName,
            report_file: this.reportTechnicalName,
            context: { active_ids: [recordId] },
        });
    }

    // ------------------------------------------------------------------
    //  Navigation
    // ------------------------------------------------------------------

    goBack() {
        if (this.state.isTemplateMode) {
            this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: "axoline.layout.template",
                view_mode: "list,form",
                views: [[false, "list"], [false, "form"]],
                name: _t("Layout Templates"),
            });
        } else {
            this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: "ir.actions.report",
                view_mode: "list,form",
                views: [[false, "list"], [false, "form"]],
                domain: [["report_type", "=", "qweb-pdf"]],
                name: _t("PDF Reports"),
            });
        }
    }

    // ------------------------------------------------------------------
    //  Block management
    // ------------------------------------------------------------------

    addBlock(blockType) {
        const settings = JSON.parse(JSON.stringify(DEFAULT_SETTINGS[blockType] || {}));
        const block = { id: uid(), type: blockType, settings };
        this.state.blocks.push(block);
        this.state.selectedBlockId = block.id;
    }

    removeBlock(blockId) {
        const idx = this.state.blocks.findIndex((b) => b.id === blockId);
        if (idx >= 0) {
            this.state.blocks.splice(idx, 1);
            if (this.state.selectedBlockId === blockId) {
                this.state.selectedBlockId = null;
            }
            return;
        }
        for (const b of this.state.blocks) {
            if (b.type === "two_columns") {
                for (const key of ["left_blocks", "right_blocks"]) {
                    const arr = b.settings[key] || [];
                    const subIdx = arr.findIndex((sb) => sb.id === blockId);
                    if (subIdx >= 0) {
                        arr.splice(subIdx, 1);
                        if (this.state.selectedBlockId === blockId) {
                            this.state.selectedBlockId = null;
                        }
                        return;
                    }
                }
            }
        }
    }

    duplicateBlock(blockId) {
        const idx = this.state.blocks.findIndex((b) => b.id === blockId);
        if (idx >= 0) {
            const copy = JSON.parse(JSON.stringify(this.state.blocks[idx]));
            copy.id = uid();
            if (copy.type === "two_columns") {
                (copy.settings.left_blocks || []).forEach((b) => (b.id = uid()));
                (copy.settings.right_blocks || []).forEach((b) => (b.id = uid()));
            }
            this.state.blocks.splice(idx + 1, 0, copy);
            this.state.selectedBlockId = copy.id;
            return;
        }
        for (const b of this.state.blocks) {
            if (b.type === "two_columns") {
                for (const key of ["left_blocks", "right_blocks"]) {
                    const arr = b.settings[key] || [];
                    const subIdx = arr.findIndex((sb) => sb.id === blockId);
                    if (subIdx >= 0) {
                        const copy = JSON.parse(JSON.stringify(arr[subIdx]));
                        copy.id = uid();
                        arr.splice(subIdx + 1, 0, copy);
                        this.state.selectedBlockId = copy.id;
                        return;
                    }
                }
            }
        }
    }

    moveBlock(blockId, direction) {
        const idx = this.state.blocks.findIndex((b) => b.id === blockId);
        const newIdx = idx + direction;
        if (newIdx < 0 || newIdx >= this.state.blocks.length) return;
        const [item] = this.state.blocks.splice(idx, 1);
        this.state.blocks.splice(newIdx, 0, item);
    }

    moveColumnBlock(twoColBlockId, side, subBlockId, direction) {
        const block = this.state.blocks.find((b) => b.id === twoColBlockId);
        if (!block) return;
        const key = side === "left" ? "left_blocks" : "right_blocks";
        const arr = block.settings[key] || [];
        const idx = arr.findIndex((b) => b.id === subBlockId);
        const newIdx = idx + direction;
        if (idx < 0 || newIdx < 0 || newIdx >= arr.length) return;
        const [item] = arr.splice(idx, 1);
        arr.splice(newIdx, 0, item);
    }

    selectBlock(blockId) {
        this.state.selectedBlockId = blockId;
    }

    // ------------------------------------------------------------------
    //  Property editing
    // ------------------------------------------------------------------

    get selectedBlock() {
        if (!this.state.selectedBlockId) return null;
        for (const b of this.state.blocks) {
            if (b.id === this.state.selectedBlockId) return b;
            if (b.type === "two_columns") {
                for (const key of ["left_blocks", "right_blocks"]) {
                    const sub = (b.settings[key] || []).find(
                        (sb) => sb.id === this.state.selectedBlockId,
                    );
                    if (sub) return sub;
                }
            }
        }
        return null;
    }

    get selectedBlockProps() {
        const block = this.selectedBlock;
        if (!block) return [];
        return BLOCK_PROPERTIES[block.type] || [];
    }

    onPropChange(propKey, ev) {
        const block = this.selectedBlock;
        if (!block) return;
        const propDef = this.selectedBlockProps.find((p) => p.key === propKey);
        let value;
        if (propDef && propDef.type === "boolean") {
            value = ev.target.checked;
        } else {
            value = ev.target.value;
        }
        block.settings[propKey] = value;
    }

    // ------------------------------------------------------------------
    //  Active toggle
    // ------------------------------------------------------------------

    toggleActive() {
        this.state.active = !this.state.active;
    }

    // ------------------------------------------------------------------
    //  Margins
    // ------------------------------------------------------------------

    onMarginChange(side, ev) {
        const val = parseFloat(ev.target.value);
        if (!isNaN(val) && val >= 0) {
            this.state.margins[side] = val;
        }
    }

    // ------------------------------------------------------------------
    //  Line items column ordering
    // ------------------------------------------------------------------

    get orderedLineItemColumns() {
        const block = this.selectedBlock;
        if (!block || block.type !== "line_items") return [];
        const s = block.settings;
        if (!s.column_order || !s.column_order.length) {
            s.column_order = [...DEFAULT_COLUMN_ORDER];
        }
        const allIds = LINE_ITEM_COLUMNS.map((c) => c.id);
        for (const id of allIds) {
            if (!s.column_order.includes(id)) {
                s.column_order.push(id);
            }
        }
        return s.column_order.map((colId) => {
            const def = LINE_ITEM_COLUMNS.find((c) => c.id === colId);
            if (!def) return null;
            return {
                id: colId,
                label: def.label,
                enabled: s["show_" + colId] !== false,
                displayLabel: s["label_" + colId] || def.defaultLabel,
            };
        }).filter(Boolean);
    }

    toggleLineItemColumn(colId) {
        const block = this.selectedBlock;
        if (!block) return;
        const key = "show_" + colId;
        block.settings[key] = !block.settings[key];
    }

    onColumnLabelChange(colId, ev) {
        const block = this.selectedBlock;
        if (!block) return;
        block.settings["label_" + colId] = ev.target.value;
    }

    moveColumnUp(colId) {
        const block = this.selectedBlock;
        if (!block) return;
        const order = block.settings.column_order;
        const idx = order.indexOf(colId);
        if (idx > 0) {
            [order[idx - 1], order[idx]] = [order[idx], order[idx - 1]];
        }
    }

    moveColumnDown(colId) {
        const block = this.selectedBlock;
        if (!block) return;
        const order = block.settings.column_order;
        const idx = order.indexOf(colId);
        if (idx >= 0 && idx < order.length - 1) {
            [order[idx], order[idx + 1]] = [order[idx + 1], order[idx]];
        }
    }

    getVisibleColumns(block) {
        if (!block || block.type !== "line_items") return [];
        const s = block.settings;
        const order = s.column_order || DEFAULT_COLUMN_ORDER;
        const defaultHidden = ["taxes", "sku"];
        const result = [];
        for (const colId of order) {
            const def = LINE_ITEM_COLUMNS.find((c) => c.id === colId);
            if (!def) continue;
            const showKey = "show_" + colId;
            const isDefaultHidden = defaultHidden.includes(colId);
            const visible = isDefaultHidden ? (s[showKey] === true) : (s[showKey] !== false);
            if (!visible) continue;
            result.push({
                id: colId,
                label: s["label_" + colId] || def.defaultLabel,
            });
        }
        return result;
    }

    getSampleData(colId, rowIdx) {
        const data = {
            position: ["1", "2"],
            sku: ["ART-001", "ART-002"],
            product: [_t("Product A"), _t("Product B")],
            description: [_t("Description…"), _t("Another item")],
            quantity: ["5", "2"],
            uom: [_t("pcs"), _t("pcs")],
            price_unit: ["100.00 €", "250.00 €"],
            discount: ["10%", ""],
            taxes: ["19%", "19%"],
            subtotal: ["500.00 €", "500.00 €"],
        };
        return (data[colId] || ["", ""])[rowIdx] || "";
    }

    // ------------------------------------------------------------------
    //  Keyboard
    // ------------------------------------------------------------------

    _onKeyDown(ev) {
        if ((ev.ctrlKey || ev.metaKey) && ev.key === "s") {
            ev.preventDefault();
            this.save();
        }
        if (ev.key === "Delete" && this.state.selectedBlockId) {
            const tag = ev.target.tagName;
            if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
            this.removeBlock(this.state.selectedBlockId);
        }
    }

    // ------------------------------------------------------------------
    //  Drag & Drop from palette
    // ------------------------------------------------------------------

    onPaletteDragStart(ev, blockType) {
        ev.dataTransfer.effectAllowed = "copy";
        ev.dataTransfer.setData("text/plain", blockType);
        this.state.dragState = { type: "palette", blockType };
    }

    // ------------------------------------------------------------------
    //  Drag & Drop reorder on canvas
    // ------------------------------------------------------------------

    onBlockDragStart(ev, blockId) {
        const idx = this.state.blocks.findIndex((b) => b.id === blockId);
        ev.dataTransfer.effectAllowed = "move";
        ev.dataTransfer.setData("text/plain", blockId);
        this.state.dragState = { type: "reorder", blockId, fromIndex: idx };
    }

    onCanvasDragOver(ev) {
        ev.preventDefault();
        ev.dataTransfer.dropEffect = this.state.dragState?.type === "palette" ? "copy" : "move";
        const idx = this._getDropIndex(ev);
        this.state.dropTargetIndex = idx;
    }

    onCanvasDragLeave(ev) {
        if (!this.canvasRef.el?.contains(ev.relatedTarget)) {
            this.state.dropTargetIndex = null;
        }
    }

    onCanvasDrop(ev) {
        ev.preventDefault();
        const targetIdx = this.state.dropTargetIndex ?? this.state.blocks.length;
        const ds = this.state.dragState;

        if (ds?.type === "palette") {
            const settings = JSON.parse(JSON.stringify(DEFAULT_SETTINGS[ds.blockType] || {}));
            const block = { id: uid(), type: ds.blockType, settings };
            this.state.blocks.splice(targetIdx, 0, block);
            this.state.selectedBlockId = block.id;
        } else if (ds?.type === "reorder") {
            const fromIdx = this.state.blocks.findIndex((b) => b.id === ds.blockId);
            if (fromIdx >= 0) {
                const [item] = this.state.blocks.splice(fromIdx, 1);
                const insertIdx = targetIdx > fromIdx ? targetIdx - 1 : targetIdx;
                this.state.blocks.splice(insertIdx, 0, item);
            }
        } else if (ds?.type === "column_reorder") {
            const srcBlock = this.state.blocks.find((b) => b.id === ds.twoColBlockId);
            if (srcBlock) {
                const srcKey = ds.side === "left" ? "left_blocks" : "right_blocks";
                const srcArr = srcBlock.settings[srcKey] || [];
                const srcIdx = srcArr.findIndex((b) => b.id === ds.subBlockId);
                if (srcIdx >= 0) {
                    const [item] = srcArr.splice(srcIdx, 1);
                    this.state.blocks.splice(targetIdx, 0, item);
                    this.state.selectedBlockId = item.id;
                }
            }
        }

        this.state.dragState = null;
        this.state.dropTargetIndex = null;
        this.state.columnDropTarget = null;
    }

    _getDropIndex(ev) {
        if (!this.canvasRef.el) return this.state.blocks.length;
        const items = this.canvasRef.el.querySelectorAll(".axo-canvas-block");
        for (let i = 0; i < items.length; i++) {
            const rect = items[i].getBoundingClientRect();
            if (ev.clientY < rect.top + rect.height / 2) {
                return i;
            }
        }
        return this.state.blocks.length;
    }

    // ------------------------------------------------------------------
    //  Column Drag & Drop
    // ------------------------------------------------------------------

    onColumnDragOver(ev, twoColBlockId, side) {
        ev.preventDefault();
        ev.stopPropagation();
        const ds = this.state.dragState;
        if (!ds) return;
        if (ds.type === "palette" && COLUMN_FORBIDDEN_TYPES.has(ds.blockType)) return;
        if (ds.type === "reorder") {
            const b = this.state.blocks.find((x) => x.id === ds.blockId);
            if (b && COLUMN_FORBIDDEN_TYPES.has(b.type)) return;
        }
        ev.dataTransfer.dropEffect = ds.type === "palette" ? "copy" : "move";
        const idx = this._getColumnDropIndex(ev, twoColBlockId, side);
        this.state.columnDropTarget = { blockId: twoColBlockId, side, index: idx };
        this.state.dropTargetIndex = null;
    }

    onColumnDragLeave(ev) {
        if (!ev.currentTarget.contains(ev.relatedTarget)) {
            this.state.columnDropTarget = null;
        }
    }

    onColumnDrop(ev, twoColBlockId, side) {
        ev.preventDefault();
        ev.stopPropagation();
        const ds = this.state.dragState;
        if (!ds) return;

        const block = this.state.blocks.find((b) => b.id === twoColBlockId);
        if (!block) return;
        const key = side === "left" ? "left_blocks" : "right_blocks";
        if (!block.settings[key]) block.settings[key] = [];
        const arr = block.settings[key];
        const targetIdx = this.state.columnDropTarget?.index ?? arr.length;

        if (ds.type === "palette") {
            if (COLUMN_FORBIDDEN_TYPES.has(ds.blockType)) return;
            const settings = JSON.parse(JSON.stringify(DEFAULT_SETTINGS[ds.blockType] || {}));
            const newBlock = { id: uid(), type: ds.blockType, settings };
            arr.splice(targetIdx, 0, newBlock);
            this.state.selectedBlockId = newBlock.id;
        } else if (ds.type === "reorder") {
            const fromIdx = this.state.blocks.findIndex((b) => b.id === ds.blockId);
            if (fromIdx >= 0) {
                const movedBlock = this.state.blocks[fromIdx];
                if (COLUMN_FORBIDDEN_TYPES.has(movedBlock.type)) return;
                this.state.blocks.splice(fromIdx, 1);
                arr.splice(targetIdx, 0, movedBlock);
                this.state.selectedBlockId = movedBlock.id;
            }
        } else if (ds.type === "column_reorder") {
            const srcBlock = this.state.blocks.find((b) => b.id === ds.twoColBlockId);
            if (!srcBlock) return;
            const srcKey = ds.side === "left" ? "left_blocks" : "right_blocks";
            const srcArr = srcBlock.settings[srcKey] || [];
            const srcIdx = srcArr.findIndex((b) => b.id === ds.subBlockId);
            if (srcIdx >= 0) {
                const [movedBlock] = srcArr.splice(srcIdx, 1);
                let insertIdx = targetIdx;
                if (ds.twoColBlockId === twoColBlockId && ds.side === side && srcIdx < targetIdx) {
                    insertIdx--;
                }
                arr.splice(Math.max(0, insertIdx), 0, movedBlock);
                this.state.selectedBlockId = movedBlock.id;
            }
        }

        this.state.dragState = null;
        this.state.columnDropTarget = null;
        this.state.dropTargetIndex = null;
    }

    onColumnBlockDragStart(ev, twoColBlockId, side, subBlockId) {
        ev.stopPropagation();
        ev.dataTransfer.effectAllowed = "move";
        ev.dataTransfer.setData("text/plain", subBlockId);
        this.state.dragState = { type: "column_reorder", twoColBlockId, side, subBlockId };
    }

    _getColumnDropIndex(ev, twoColBlockId, side) {
        const selector = `.axo-twocol-col[data-col-block="${twoColBlockId}"][data-col-side="${side}"] .axo-column-subblock`;
        const items = document.querySelectorAll(selector);
        for (let i = 0; i < items.length; i++) {
            const rect = items[i].getBoundingClientRect();
            if (ev.clientY < rect.top + rect.height / 2) {
                return i;
            }
        }
        const block = this.state.blocks.find((b) => b.id === twoColBlockId);
        return (block?.settings[side === "left" ? "left_blocks" : "right_blocks"] || []).length;
    }

    isColumnDropTarget(blockId, side) {
        const ct = this.state.columnDropTarget;
        return ct && ct.blockId === blockId && ct.side === side;
    }

    // ------------------------------------------------------------------
    //  Layout Template system
    // ------------------------------------------------------------------

    async openTemplateDialog() {
        this.state.showTemplateDialog = true;
        this.state.templatesLoading = true;
        try {
            const templates = await rpc("/axoline_layout_editor/templates", {});
            this.state.templates = templates || [];
        } catch (e) {
            this.notification.add(_t("Error loading templates: ") + String(e), { type: "danger" });
        }
        this.state.templatesLoading = false;
    }

    closeTemplateDialog() {
        this.state.showTemplateDialog = false;
    }

    // ------------------------------------------------------------------
    //  Freemium upsell
    // ------------------------------------------------------------------

    showUpsell(message) {
        const url = this.state.proStoreUrl || "https://apps.odoo.com/apps/modules/18.0/axoline_layout_editor_pro";
        this.notification.add(
            message || _t("This is a PRO feature. Get the PRO add-on to unlock all templates and document types."),
            {
                type: "warning",
                sticky: true,
                buttons: [{
                    name: _t("Get the PRO add-on"),
                    primary: true,
                    onClick: () => window.open(url, "_blank"),
                }],
            },
        );
    }

    onTemplateClick(tpl) {
        if (tpl.locked) {
            this.showUpsell(_t("The \u201c%s\u201d template is available in the PRO add-on.", tpl.name));
            return;
        }
        this.applyTemplate(tpl.id);
    }

    async applyTemplate(templateId) {
        if (this.state.blocks.length) {
            if (!confirm(_t("The current layout will be replaced by the template. Continue?"))) {
                return;
            }
        }
        try {
            const result = await rpc("/axoline_layout_editor/apply_template", {
                layout_custom_id: this.layoutCustomId,
                template_id: templateId,
            });
            if (result.error === "pro_required") {
                this.state.proStoreUrl = result.pro_store_url || this.state.proStoreUrl;
                this.showUpsell();
                return;
            }
            if (result.error) {
                this.notification.add(result.error, { type: "danger" });
                return;
            }
            this.state.blocks = result.layout_json?.blocks || [];
            this.state.selectedBlockId = null;
            this.state.showTemplateDialog = false;
            this.notification.add(_t("Template applied!"), { type: "success" });
        } catch (e) {
            this.notification.add(_t("Error: ") + String(e), { type: "danger" });
        }
    }

    openSaveTemplateDialog() {
        this.state.saveTemplateName = "";
        this.state.saveTemplateDescription = "";
        this.state.showSaveTemplateDialog = true;
    }

    closeSaveTemplateDialog() {
        this.state.showSaveTemplateDialog = false;
    }

    onTemplateNameInput(ev) {
        this.state.saveTemplateName = ev.target.value;
    }

    onTemplateDescriptionInput(ev) {
        this.state.saveTemplateDescription = ev.target.value;
    }

    async confirmSaveTemplate() {
        const name = this.state.saveTemplateName.trim();
        if (!name) {
            this.notification.add(_t("Please enter a name."), { type: "warning" });
            return;
        }
        try {
            await this.save();
            const result = await rpc("/axoline_layout_editor/save_as_template", {
                layout_custom_id: this.layoutCustomId,
                name: name,
                description: this.state.saveTemplateDescription.trim(),
            });
            if (result.error) {
                this.notification.add(result.error, { type: "danger" });
                return;
            }
            this.state.showSaveTemplateDialog = false;
            this.notification.add(_t("Template '%s' saved!", name), { type: "success" });
        } catch (e) {
            this.notification.add(_t("Error: ") + String(e), { type: "danger" });
        }
    }

    getCategoryLabel(category) {
        const map = { classic: _t("Classic"), modern: _t("Modern"), compact: _t("Compact"), custom: _t("Custom") };
        return map[category] || category;
    }

    // ------------------------------------------------------------------
    //  Template helpers (block meta)
    // ------------------------------------------------------------------

    getBlockMeta(blockType) {
        return BLOCK_META[blockType] || { label: blockType, icon: "fa-cube", cat: "other" };
    }

    get paletteCategories() {
        return CATEGORIES.map((cat) => ({
            ...cat,
            blocks: Object.entries(BLOCK_META)
                .filter(([_, m]) => m.cat === cat.key)
                .map(([type, m]) => ({ type, ...m })),
        }));
    }

    isDropTarget(index) {
        return this.state.dropTargetIndex === index;
    }

    blockPreviewText(block) {
        const meta = BLOCK_META[block.type] || {};
        const label = meta.label || block.type;
        const s = block.settings || {};
        switch (block.type) {
            case "free_text":
                return label + (s.content ? ": " + s.content.substring(0, 50) : "");
            case "spacer":
                return label + " (" + (s.height || 20) + "px)";
            case "separator":
                return label + " (" + (s.style || "solid") + ")";
            case "two_columns":
                return label + " (" + (s.left_ratio || 50) + "% / " + (100 - (s.left_ratio || 50)) + "%)";
            default:
                return label;
        }
    }
}

registry.category("actions").add("axoline_layout_editor", AxolineLayoutEditor);
