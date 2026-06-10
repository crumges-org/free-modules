{
    # Per Odoo Vendor Guidelines: name ≤25 chars, no adjectives, no company name.
    'name': 'Connector Common',
    'version': '18.0.1.3.0',
    'category': 'Connectors',
    'summary': 'Free foundation library for Arure paid connectors. Provides the background job processor (cron-driven, exponential-backoff retry, two-commit safety), structured per-call audit log, polymorphic connector-instance registry, and field-mapping framework that paid Arure connectors (WooCommerce, FedEx, MCP, BigQuery, Klaviyo) all extend. No queue_job dependency, no external Python packages, no SaaS middleware.',
    'description': """
Connector Common — foundation for Arure eCommerce connectors
============================================================

Free base module providing the shared infrastructure for Arure
Technologies' connector portfolio (WooCommerce, FedEx, BigQuery,
Klaviyo, etc.). Designed to be installed first, then any of the paid
platform-specific connectors on top.

What's included
---------------

* **Background job processor** — built-in queue with exponential
  backoff retry. No `queue_job` dependency.
* **Connector instance registry** — generic platform/connection model
  that paid connectors link to.
* **Connector log** — structured audit log of every API call,
  background job, and error.
* **Field mapping framework** — base classes platform-specific
  connectors extend with their own mapping rules.
* **Cron scheduler** — registers `Connector: Process Pending Background
  Jobs` cron on install (every 5 minutes).
* **Role-based access** — base groups paid connectors extend.

Why a separate free module
--------------------------

The Arure connector portfolio (WooCommerce, FedEx Shipping, BigQuery
BI, Klaviyo Email Marketing, all on Odoo 19) shares a single queue and
audit infrastructure. Splitting that into a free, installable
foundation lets customers:

* Install one connector at a time without each shipping its own queue
* Audit and customize the queue layer without touching paid connector code
* Avoid version skew when upgrading individual connectors

This module is functional on its own — it provides the registry and
queue UI — but its value is realized when at least one platform-specific
connector is installed.

License
-------

OPL-1 (Odoo Proprietary License v1.0). This is a free module ($0) but
licensed proprietarily, consistent with the rest of the Arure publisher
portfolio. Source delivered with the App Store package; not redistributable.

Refund policy
-------------

This is a free module ($0). Bug reports go to support@arure.tech.
See the bundled SUPPORT.md for SLA detail.
    """,
    'author': 'Arure Technologies',
    'website': 'https://www.arure.tech',
    'license': 'OPL-1',
    'depends': [
        'base',
        'mail',
        'web',
    ],
    'data': [
        'security/connector_security.xml',
        'security/ir.model.access.csv',
        'data/connector_data.xml',
        'views/connector_instance_views.xml',
        'views/connector_log_views.xml',
        'views/connector_queue_views.xml',
        'views/connector_mapping_views.xml',
        'views/connector_config_views.xml',
        'views/connector_platform_views.xml',
        'views/connector_reports.xml',
        'views/menu.xml',
    ],
    'demo': [
        'demo/connector_demo.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'sequence': 1,
    'price': 0.0,
    'currency': 'USD',
    'support': 'support@arure.tech',
    'images': [
        'static/description/banner.png',
    ],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'maintainer': 'Arure Technologies',
    'maintainer_email': 'support@arure.tech',
    # `live_test_url` and `documentation_url` intentionally omitted —
    # no public demo deployment exists yet. Documentation is bundled in
    # the module package (README.md, SUPPORT.md).
}
