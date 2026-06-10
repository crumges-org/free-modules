# Connector Common — foundation for Arure eCommerce connectors

Free base module ($0). Provides the queue, audit log, and instance
registry that Arure's WooCommerce / FedEx / BigQuery / Klaviyo
connectors all share. Install this first, then any paid connector on
top.

## What's included

- **Background job processor** — built-in queue with exponential
  backoff retry. Cron-driven; runs every 5 minutes.
- **Connector instance registry** (`connector.instance`) — generic
  platform / connection record that paid connectors link to.
- **Connector log** — structured audit log of every API call,
  background job, and error.
- **Field mapping framework** — base classes paid connectors extend
  with their own mapping rules.
- **Role-based access** — base groups paid connectors extend.

No `queue_job` dependency. No external Python packages required.

## Requirements

- Odoo 19.0 (Community or Enterprise) on Odoo.sh or on-premise.
  Third-party apps cannot be installed on Odoo Online (SaaS) per Odoo
  policy.
- PostgreSQL 12+

## Installation

Install via Odoo Apps: search for **Connector Common**. After install,
a new **Connectors** menu appears with Dashboard, Instances, Queue,
Background Jobs, Logs, Configuration, and Reporting sub-menus.

This module is functional on its own (you can register a generic
`connector.instance` and watch the queue), but its value is realized
when a platform-specific connector is installed alongside.

## Recommended companion modules

Each is a separate paid listing on the App Store:

- **WooCommerce Connector** — Two-way sync with WooCommerce stores
- **FedEx Shipping Connector** — Live rates, label generation, tracking (REST API)
- **BI Connector (Power BI + BigQuery)** — Export Odoo data to BI destinations
- **Klaviyo Connector** — Two-way contact and event sync

## Support

- Email: `support@arure.tech` (preferred — bug reports, refund requests, anything that needs an audit trail)
- WhatsApp: `+1 858 463 4405` (quick configuration questions, Mon–Fri 09:00–19:00 IST best-effort)
- Response SLA: 1 business day for acknowledgement; see [SUPPORT.md](SUPPORT.md) for the full severity matrix.

## Refund policy

This is a free module ($0). The Odoo App Store refund policy still applies for any paid follow-on purchase. See `SUPPORT.md` for bug SLAs.

## License & trademarks

Odoo Proprietary License (OPL-1). Each customer receives a per-database
license. Source code is delivered as part of the App Store purchase but is
not redistributable.

WooCommerce is a registered trademark of Automattic Inc. Shopify is a
registered trademark of Shopify Inc. Magento is a registered trademark
of Adobe Inc. PrestaShop is a registered trademark of PrestaShop SA.
BigCommerce is a registered trademark of BigCommerce, Inc. Odoo is a
registered trademark of Odoo S.A. This module is an independent
foundation developed by Arure Technologies and is not affiliated with,
endorsed by, or sponsored by any of the above. References are
descriptive only — the module provides the framework that paid
platform-specific connectors extend.
