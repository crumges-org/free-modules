# API Connector

> Configurable API orchestration framework for Odoo 18 (Community & Enterprise)

## Overview / Resumen

| English                                                                                                                                                                 | Español                                                                                                                                                                         |
|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| API Connector lets you model REST APIs visually inside Odoo, orchestrate endpoints, transform payloads, trigger automations, and keep a full audit trail of every call. | API Connector te permite modelar APIs REST dentro de Odoo, orquestar endpoints, transformar cargas, disparar automatizaciones y mantener un historial completo de cada llamada. |

## Key Features

- Multi-connector architecture (one configuration per external API)
- Endpoint catalog with GET/POST/PUT/DELETE support, path/param templating, payload mapping
- Authentication modes: None, Basic, Bearer, API Key (header/query)
- Bidirectional field mapping + transformation hooks
- Scheduler-ready initial import/export actions
- Automation builders (Base Automation, Server Actions, Cron jobs)
- Webhook handler stubs and call log dashboard

## Requirements

- Odoo 18.0 (Community or Enterprise)
- Python `requests` (bundled with Odoo 18 runtime)
- Optional: `social_media` app (already in depends list)

## Installation

```bash
# From your Odoo addons path
git clone git@github.com:soltein/solt-api-conector.git

# Update your odoo.conf
addons_path = /path/to/odoo/addons,/path/to/solt-api-conector

# Install from CLI
./odoo-bin -c odoo.conf -d your_db -i solt_api_connector --stop-after-init
```

## Configuration

1. Go to **Settings > Technical > API Connector > Connectors**.
2. Create a connector (base URL, auth type, credentials, headers, timeout, companies).
3. Define endpoints: HTTP method, path template, parameter mappings, payload templates.
4. Attach Base Automations / Server Actions / Crons for import/export jobs.
5. (Optional) Configure initial import/export server actions for bootstrap jobs.

## Usage

- Use the **Test Connection** button on each connector to validate credentials.
- Trigger an endpoint with `connector.execute_endpoint(code, record, params, data)`.
- Monitor activity in **API Call Logs** (status, payload, response, retry info).
- Link connectors to companies for multi-tenant operations.

## Localization / i18n

Source strings are in English (en_US). To export/update translations:

```bash
./odoo-bin -c odoo.conf -d your_db \
  --i18n-export=solt_api_connector/i18n/es_MX.po \
  --modules=solt_api_connector --log-level=warn
```

More details in `i18n/README.md`.

## Testing

```bash
./odoo-bin -c odoo.conf -d test_api --test-enable \
  -i solt_api_connector --stop-after-init
```

## Packaging for Odoo Apps

```bash
zip -r solt_api_connector_18.0.1.0.1.zip solt_api_connector \
  -x "*/__pycache__/*" "*.pyc" "*.pyo" "*/.git/*"
```

## Support

- Website: https://www.soltein.mx
- Email: soporte@soltein.mx
- Maintainers: `soltein`

---

© 2024 Soltein SA de CV · Licensed under LGPL-3

