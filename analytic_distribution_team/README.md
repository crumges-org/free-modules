# Analytic Distribution by Sales Team

[![License: LGPL-3](https://img.shields.io/badge/license-LGPL--3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)
[![Odoo Version](https://img.shields.io/badge/odoo-18.0-875A7B.svg)](https://www.odoo.com)

Adds **Sales Team** as a matching criterion on Analytic Distribution Models,
so analytic accounts can be assigned automatically based on which team a
sale order or customer invoice belongs to.

## What it does

Out of the box, Odoo lets you assign analytic distribution automatically
based on partner, partner category, product, product category, account
prefix and company. This module adds one more criterion: **Sales Team**.

When a sale order is created (or a customer invoice is registered) and
its team matches a distribution rule, the analytic accounts configured
on that rule are applied automatically.

## Use cases

- **Multi-brand companies** — each brand is a sales team with its own
  analytic account. Sales and invoices are tagged automatically.
- **Marketplaces** — Amazon, eBay, etc. configured as separate teams,
  each one mapped to its own analytic dimension for P&L reporting.
- **Geographic divisions** — different sales teams per country or
  region, each routed to the corresponding analytic account.

## Configuration

1. Go to **Accounting → Configuration → Analytic Distribution Models**.
2. Create a new rule (or edit an existing one).
3. Set the **Sales Team** field to the team you want this rule to
   apply to.
4. Set the **Analytic Distribution** as usual.

The rule will be applied automatically the next time a sale order or
customer invoice belonging to that team is created or modified.

## How it works (technical)

- Adds a `team_id` Many2one field (`crm.team`) to
  `account.analytic.distribution.model`.
- Extends `_get_default_search_domain_vals` to include `team_id: False`
  as a default — this guarantees that rules with a team set never match
  documents that do not provide a team (e.g. purchase orders, expenses).
- Overrides
  `account.move.line._get_analytic_distribution_arguments` (the official
  hook exposed by core) to pass `team_id`.
- Overrides `sale.order.line._compute_analytic_distribution` to do the
  same on the sale side — core does not expose a dedicated hook there,
  so the full computation is reimplemented and kept in sync.

## Behaviour summary

| Document type        | Rule has team? | Document has team? | Rule applies? |
| -------------------- | -------------- | ------------------ | ------------- |
| Sale order / invoice | No             | —                  | Yes (as before) |
| Sale order / invoice | Yes            | Same team          | Yes           |
| Sale order / invoice | Yes            | Different / none   | No            |
| Purchase, expense, … | Yes            | —                  | No            |

## Compatibility

- Odoo 18.0 Community and Enterprise.
- Depends on `account` and `sale`.

## Bug Tracker

Bugs are tracked on GitHub Issues. In case of trouble, please check
there if your issue has already been reported.

## Credits

### Authors

- Lune Makers SL

### Maintainers

This module is maintained by [Lune Makers SL](https://lunemakers.com).

For support: [info@lunemakers.com](mailto:info@lunemakers.com)

## License

LGPL-3.0 or later. See [LICENSE](LICENSE) for details.
