{
    'name': 'ISPG Universal List View KPI Dashboard',
    'version': '18.0.1.1.0',
    'summary': 'Add clickable KPI cards (counts & totals) to ANY list view with a single XML tag - no Python, no JS.',
    'description': """
        Universal List View KPI Dashboard
        =================================
        Drop a single ``<listdashboard>`` tag into any List (Tree) view to get a
        ribbon of clickable KPI cards above the records. No Python, no
        JavaScript, no separate dashboard screen - pure XML configuration.

        Features
        --------
        * **One tag, any model** - Sales, Purchase, Accounting, CRM, Project, or
          your own custom models.
        * **Counts or totals** - each card shows a record count, or an
          aggregated value (sum / avg / max / min) of any numeric field.
        * **Click to filter** - click a card to filter the list to those
          records; click again to clear. Shown as a removable search facet.
        * **Live** - cards recompute automatically to match the records
          currently shown (respects the user's search filters).
        * **Rows with headings** - group cards into rows with ``<rowcard>``, each
          with an optional heading.
        * **Polished UI** - per-card colours (or an automatic 8-colour palette),
          FontAwesome icons OR images (png/svg/jpg, auto-scaled), humanised
          numbers (1.2k / 3.4M) and currency symbols. Theme-aware.

        Configuration example
        ----------------------
        Add this inside any ``<list>`` view (directly or via xpath)::

            <record id="view_quotation_tree_with_onboarding_inherit" model="ir.ui.view">
              <field name="name">sale.order.list</field>
              <field name="model">sale.order</field>
              <field name="inherit_id" ref="sale.view_quotation_tree_with_onboarding"/>
              <field name="arch" type="xml">
                  <xpath expr="//list" position="inside">
                      <listdashboard>
                          <rowcard string="Order Status">
                              <card string="Quotations" domain="[('state','=','draft')]"
                                  color="#0dcaf0" icon="fa-file-text-o"/>
                              <card string="Sold" domain="[('state','=','sale')]"
                                  color="#198754" icon="fa-check-circle-o"/>
                          </rowcard>
                          <rowcard string="Revenue">
                              <card string="Total Revenue" domain="[('state','=','sale')]"
                                  measure="amount_total" aggregate="sum" symbol="$"
                                  icon="fa-line-chart"/>
                          </rowcard>
                      </listdashboard>
                  </xpath>
              </field>
          </record>

        Tags & attributes
        -----------------
        * ``<listdashboard>`` - wraps the whole ribbon. Cards may sit directly
          inside it (single row) or be grouped in ``<rowcard>`` blocks.
        * ``<rowcard string="...">`` - one horizontal row of cards; rows stack
          vertically. ``string`` (optional) shows as a heading above the row.
        * ``<card>`` attributes:
            - ``string`` - card title.
            - ``domain`` - records to count/measure (Odoo domain).
            - ``measure`` - numeric field to aggregate (omit for a record count).
            - ``aggregate`` - sum / avg / max / min (default sum).
            - ``symbol`` - unit/currency prefix, e.g. ``$``.
            - ``icon`` - a FontAwesome class (``fa-line-chart``) OR an image
              URL/path (png/svg/jpg), auto-scaled to a fixed size.
            - ``color`` - any CSS colour; omit for an automatic palette colour.

        100% configuration-driven. No coding required.
    """,
    'category': 'Productivity/Technical',
    'author': 'ISPG Technologies India Pvt. Ltd.',
    'maintainer': 'ISPG Technologies India Pvt. Ltd.',
    'website': 'https://www.ispg.co',
    'depends': ['web'],
    'data': [
    ],

    'assets': {
        'web.assets_backend': [
            'ispg_list_view_dashboard/static/src/js/list_dashboard.js',
            'ispg_list_view_dashboard/static/src/xml/list_dashboard.xml',
            'ispg_list_view_dashboard/static/src/js/list_renderer_patch.js',
            'ispg_list_view_dashboard/static/src/xml/list_renderer_patch.xml',
            'ispg_list_view_dashboard/static/src/scss/list_dashboard.scss',
        ],
    },
     'images': [
        'static/description/banner.png',
        'static/description/icon.png',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}