# Knowledge Guide

Build navigable user documentation for your Odoo modules and publish it on
the web with secure tokenized links.

Each Odoo module can contribute its own pages through XML data files,
making this the perfect base layer for product documentation, internal
training material, or customer-facing user manuals.

## Features

- **Pages organized by collapsible categories** with FontAwesome icons
- **Books** that group multiple pages and can be published online via a
  secure tokenized URL (no authentication required for end users)
- **Original content + per-page custom override** so admins can adapt
  module-shipped content without losing the original
- **HTML source viewer wizard** to inspect the raw markup of any page
- **Real-time search** with automatic highlight in titles and content
- **User-group filtering** to show or hide pages based on permissions
- **Standalone web template** (clean reading experience without the Odoo
  backend chrome)
- **Click tracking** on published guides via Odoo's native `link.tracker`
- **Email wizard** to send the guide link to multiple recipients with a
  customizable subject and body
- **Modern OWL framework** client action for the backend interface
- **Modular architecture**: any other module can ship its own documentation
  pages via a simple XML data file

## Use cases

- End-user documentation shipped with your custom Odoo modules
- Customer-facing knowledge bases published on a public URL
- Internal team training material with group-based access control
- Quick onboarding guides sent by email to new users

## Installation

1. Place the `knowledge_guide` folder in your Odoo `addons` directory
2. Update your apps list (Apps menu > Update Apps List)
3. Search for "Knowledge Guide" and click Install

## Data model

### `knowledge.guide.page`

| Field                  | Type    | Description                                     |
|------------------------|---------|-------------------------------------------------|
| `name`                 | Char    | Section title (translatable)                    |
| `content_html`         | Html    | Original content shipped by the source module   |
| `custom_content_html`  | Html    | Optional admin override (takes precedence)      |
| `display_content_html` | Html    | Computed: shows custom content if set, else original |
| `sequence`             | Integer | Display order                                   |
| `category`             | Char    | Section / category (translatable)               |
| `module_source`        | Char    | Source module name (used for traceability)      |
| `group_ids`            | Many2many `res.groups` | Allowed groups (empty = visible to everyone) |
| `active`               | Boolean | Archive flag                                    |
| `icon`                 | Char    | FontAwesome class (e.g. `fa-book`)              |
| `book_id`              | Many2one `knowledge.guide.book` | Book this page belongs to (optional) |

### `knowledge.guide.book`

| Field             | Type    | Description                                          |
|-------------------|---------|------------------------------------------------------|
| `name`            | Char    | Book title (translatable)                            |
| `slug`            | Char    | Unique URL identifier                                |
| `description_html`| Html    | Introduction shown above the public guide            |
| `is_published`    | Boolean | Whether the public URL is reachable                  |
| `access_token`    | Char    | UUID token securing the public access                |
| `link_tracker_id` | Many2one `link.tracker` | Optional click tracker             |

## Extending the module

Any other Odoo module can contribute its own pages by depending on
`knowledge_guide` and shipping an XML data file:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo noupdate="1">
    <record id="page_my_module" model="knowledge.guide.page">
        <field name="name">My Feature</field>
        <field name="category">My Module</field>
        <field name="sequence">10</field>
        <field name="icon">fa-cog</field>
        <field name="module_source">my_module</field>
        <field name="content_html"><![CDATA[
            <h1>My Feature</h1>
            <p>Description...</p>
        ]]></field>
    </record>
</odoo>
```

Then declare it in your `__manifest__.py`:

```python
'depends': ['knowledge_guide'],
'data': [
    'data/my_module_guide_data.xml',
],
```

Once the page is created, administrators can write a custom override in the
`custom_content_html` field. The override replaces the original in the
displayed guide while keeping the original available as a fallback.

## Group-based filtering

To restrict a page to specific user groups, populate the `group_ids` field.
The page will only appear for users that belong to at least one of those
groups. Leave the field empty to make the page visible to everyone.

## Public publication

Books can be published on a public URL with the structure:

```
https://your-odoo.example.com/guide/<slug>?token=<uuid>
```

The token is generated automatically when the book is created. You can
regenerate it at any time to invalidate the previous link. Use the built-in
"Generate tracked link" action to create a shortened, click-trackable URL.

## License

LGPL-3.

## Author

[Kameos](https://kameos.be) — Odoo integrator based in Belgium,
specialized in custom development for SMEs and non-profits.
