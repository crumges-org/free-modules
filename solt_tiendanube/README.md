# Odoo ↔ Tiendanube Connector

## Overview / Overview

> **Based on the Tiendanube app listing:** This official solution connects Tiendanube with Odoo to centralize catalogs, orders, inventories and shipments, eliminating manual tasks and simplifying omnichannel operations.
>
> This connector synchronizes multichannel catalogs (attributes, variants, images, SEO), pulls Tiendanube orders into native sales flows, pushes fulfillment updates (shipments, guides, cancellations) and offers dashboards with alerts for real-time decision making.

The **Soltein Tiendanube Connector** keeps Odoo 18.0 synchronized with Tiendanube: products, extra images, prices, inventory, orders, shipments, and invoices flow automatically between both platforms. Multi-company merchants can orchestrate multiple warehouses, maintain branded catalogs, and automate fulfillment rules without leaving Odoo.

## Key features / Key features

- **Two-way catalog sync** – Push product templates, brands, multi categories, prices, SEO content, and gallery images.
- **Product brand management** – Create and maintain custom brand dictionaries consumed by Tiendanube listings.
- **Multi-category tagging** – Assign additional product categories required by Tiendanube storefronts.
- **Multi-warehouse orders** – Split sales fulfillment by warehouse with per-line delivery dates and routing.
- **Inventory orchestration** – Publish stock figures per warehouse, reserve units, and keep availability aligned with Tiendanube.
- **Order intake** – Import orders, customers, payment references, coupons, and delivery methods into native sales orders.
- **Logistics bridge** – Trigger deliveries, update tracking numbers, and notify Tiendanube via secure webhooks.
- **Workflow automation** – Base automations, cron jobs, and webhooks keep both systems aligned without manual clicks.
- **Localization helpers** – Address formatting, measurement units, and regional settings designed for LATAM stores.

## Dependency Stack / Dependency Architecture

| Module | Purpose |
| --- | --- |
| `solt_api_connector` | Core framework that models REST APIs, handles authentication, webhooks, schedulers, call logs, and provides the reusable sync engine used by every vertical connector. |
| `solt_tiendanube` | Tiendanube-specific configuration (endpoints, payload mappings, cron jobs, UI) built on top of `solt_api_connector`. Includes product brand management, multi-category tagging, and multi-warehouse order routing. |
| `solt_l10n_mx_partner_address` | Mexican address enrichment so Tiendanube shipping data maps cleanly into Odoo. |
| Standard dependencies (`sale`, `sale_stock`, `stock`, `stock_delivery`) | Native Odoo models for orders, inventory, shipments, and carriers that the connector orchestrates. |

## Included Features / Funcionalidades Incluidas

| Feature | Description |
| --- | --- |
| **Core connector** | Sync engines, UI, endpoints, cron jobs for Tiendanube integration |
| **Product Brand** | Custom `solt.product.brand` model with multi-company support |
| **Multi Categories** | `categ_ids` field for auxiliary product categories classification |
| **Multi-Warehouse Orders** | Per-line warehouse assignment and delivery dates in sales orders |
| **API orchestration** | Leverages `solt_api_connector` for imports/exports, hooks, schedulers |

## Requirements

- Odoo 18.0 Community or Enterprise
- Dependencies listed in `__manifest__.py`
- Valid Tiendanube API credentials per company
- Python requirements inherited from base Odoo installation

## Installation

1. Clone this repository inside your custom addons path.
2. Install connector dependencies (`solt_api_connector`, `solt_l10n_mx_partner_address`).
3. Update the Apps list and install **Odoo ↔ Tiendanube Connector**.
4. Assign the new security groups to integration users.

## Configuration

1. Navigate to **Tiendanube Connector ▸ Settings** and enter the API keys / App ID.
2. Configure webhook endpoints and activate the required events.
3. Map warehouses through **Tiendanube Connector ▸ Warehouse Mapping**.
4. Enable multi-warehouse orders in **Sales ▸ Settings** if needed.
5. Enable cron jobs that fit your synchronization cadence.
6. Run an initial product sync followed by stock and order pulls.

## Next Steps Before Publishing

1. Capture 3–5 screenshots (dashboard, order sync, configuration) and add them to `static/description/` as `screenshot_X.png`.
2. Install on a clean DB, run smoke test, and export translations:
   ```bash
   ./odoo-bin -c odoo.conf -d test_tiendanube --stop-after-init -i solt_tiendanube
   ./odoo-bin -c odoo.conf -d test_tiendanube --i18n-export=solt_tiendanube/i18n/es_MX.po --modules=solt_tiendanube
   ```
3. Package the module:
   ```bash
   cd ..
   zip -r solt_tiendanube_18.0.1.0.7.zip solt_tiendanube -x "*/__pycache__/*" "*.pyc"
   ```
4. Submit on Odoo Apps with updated screenshots and manifest category `Sales/Multichannel`.

## Support / Soporte

- Website: <https://www.soltein.mx>
- Email: [soporte@soltein.mx](mailto:soporte@soltein.mx)

## License / Licencia

This suite is released under the **LGPL-3** license. See the root `LICENSE` file or <https://www.gnu.org/licenses/lgpl-3.0.en.html> for the complete terms. / Este conjunto se publica bajo licencia **LGPL-3**.
