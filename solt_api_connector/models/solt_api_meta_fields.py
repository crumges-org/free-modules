# -*- coding: utf-8 -*-

from lxml import etree
from lxml.etree import tostring, XML

from odoo import _, api, Command, fields, models
from odoo.exceptions import UserError

group_template = """<group></group>"""

field_template = """<field name="%s"/>"""

invisible_field_template = """<field name="%s" invisible="True"/>"""

readonly_field_template = """<field name="%s" readonly="True"  force_save="True"/>"""

attr_template = """<attribute name="%s">%s</attribute>"""

form_sheet_xpath_inside_template = """<xpath expr="//form/sheet" position="inside"></xpath>"""

page_meta_fields_template = """<page name="meta_fields" string="%s"></page>"""

container_template = """<xpath expr="//form/*" position="before"></xpath>"""

form_xpath_inside_template = """<xpath expr="//form" position="inside"></xpath>"""

label_template = """<label for="%s"/>"""

tree_field_template = """<field name="%(tree_field)s" readonly="True" column_invisible="True"/>"""


def divide_list(lst, n=2):
    length = len(lst)
    return reversed([lst[i * length // n: (i + 1) * length // n] for i in range(n)])


class SoltApiMetaFields(models.Model):
    _name = 'solt.api.meta.fields'
    _description = 'API Meta Fields'

    connector_id = fields.Many2one('solt.api.connector', string='Conector API', required=True, ondelete='cascade')
    name = fields.Char("Nombre")
    model_id = fields.Many2one('ir.model', string='Modelo Odoo')
    model = fields.Char('Model', related="model_id.model")
    active = fields.Boolean(default=True, string="Activar")

    form_view_id = fields.Many2one('ir.ui.view', 'Vista de formulario', help="Vista de formulario del modelo")
    extended_form_view_id = fields.Many2one('ir.ui.view', 'Vista de formulario extendida', readonly=True, help="The form view of the model that want to extend")
    search_view_id = fields.Many2one('ir.ui.view', 'Vista de búsqueda', help="Vista de búsqueda del modelo")
    extended_search_view_id = fields.Many2one('ir.ui.view', 'Vista de búsqueda extendida', readonly=True, help="The search view of the model that want to extend", copy=False)
    ir_meta_field_ids = fields.One2many('ir.model.fields', 'api_meta_field_id', string="Campos meta")
    meta_tab_label = fields.Char(string='Etiqueta de la pestaña Integración', default='Sincronización')
    create_dinamic_view = fields.Boolean("Crear vistas dinámicas", default=False, help="Crea las vistas dinámicas para el modelo Odoo configurado")
    list_view_id = fields.Many2one('ir.ui.view', 'Viste árbol', help="The list view of the model that want to extend Workflow state on it")
    extended_list_view_id = fields.Many2one('ir.ui.view', 'Vista árbol extendida', readonly=True, help="The list view of the model that want to extend", copy=False)

    def get_field_types(self):
        vals = [('boolean', 'Boolean'), ('char', 'Char'), ('date', 'Date'), ('datetime', 'Datetime'), ('float', 'Float'), ('html', 'Html'), ('integer', 'Integer'), ('text', 'Text'), ('selection', 'Selection')]
        return vals

    @api.onchange('model_id')
    def onchange_model_id(self):
        if self.model_id:
            if not self.name:
                self.name = self.model_id.name
            values = {'form_view_id': False, 'search_view_id': False}
            view_obj = self.env['ir.ui.view']
            form_view = view_obj.search([('model', '=', self.model_id.model), ('type', '=', 'form'), ('mode', '=', 'primary'), ('inherit_id', '=', False)], limit=1)
            if form_view:
                values['form_view_id'] = form_view.id
            search_view = view_obj.search([('model', '=', self.model_id.model), ('type', '=', 'search'), ('mode', '=', 'primary')], limit=1)
            if search_view:
                values['search_view_id'] = search_view.id
            self.update(values)

    def action_create_meta_fields(self):
        self.make_fields()
        if self.create_dinamic_view:
            self.make_views()

    @api.model
    def _get_default_meta_field_mapping(self):
        return [{"name": "x_external_id", "ttype": "char", 'state': 'manual', "field_description": "External ID", "help": _("ID of the record in the external system."), "readonly": True},
                {"name": "x_store_external_id", "ttype": "char", 'state': 'manual', "field_description": "Store external ID", "help": _("External store identifier."), "readonly": True},
                {"name":                 "x_state_sync", "ttype": "selection", 'state': 'manual', "field_description": "Sync status", "help": _("Indicates whether the record is synchronized."),
                        'selection_ids': [Command.create({'value': 'yes', 'name': 'Synchronized', 'sequence': 0}), Command.create({'value': 'no', 'name': 'Not synchronized', 'sequence': 1}), Command.create({'value': 'error', 'name': 'Error', 'sequence': 2}), ], "readonly": True},
                {"name": "x_exclud_from_sync", "ttype": "boolean", 'state': 'manual', "field_description": "Exclude from synchronization", "help": _("When enabled, the record will not be exported to external systems.")},
                {"name": "x_date_last_sync", "ttype": "datetime", 'state': 'manual', "field_description": "Last synchronization", "help": _("Indicates the last synchronization timestamp."), "readonly": True}]

    def _get_meta_fields_lines(self):
        self.ensure_one()
        commands = [Command.clear()]
        fields_to_load = self._get_default_meta_field_mapping()
        for fdict in fields_to_load:
            fdict.update({'copied': False, 'model_id': self.model_id.id, 'model': self.model_id.model, 'modules': 'solt_api_connector, ' + self.model_id.modules})
            commands.append(Command.create(fdict))
        return commands

    def _check(self):
        if not self.form_view_id:
            self.onchange_model_id()
        if not self.form_view_id:
            raise UserError(_('Please set the form view'))

    def make_fields(self):
        self.ensure_one()
        ir_meta_field_ids = self._get_default_meta_field_mapping()
        fd_ids = self.create_or_update_field(ir_meta_field_ids)
        if fd_ids and not fd_ids.mapped('api_meta_field_id'):
            self.write({'ir_meta_field_ids': [Command.set(fd_ids.ids)]})
        return True

    def make_form_meta_fields(self, arch):
        fields_attrs = []
        node_group = []
        for mf in self.ir_meta_field_ids:
            if mf.name in fields_attrs:
                raise UserError(_('Field %s already exists, the same field can only be in one.' % mf.name))
            if mf.readonly:
                node = XML(readonly_field_template % mf.name)
            else:
                node = XML(field_template % mf.name)
            node_group.append(node)
            fields_attrs.append(mf.name)
        if node_group:
            if '<notebook' not in self.form_view_id.arch:
                form = XML(form_sheet_xpath_inside_template if '<sheet' in self.form_view_id.arch else form_xpath_inside_template)
                notebook = XML('<notebook></notebook>')
                form.append(notebook)
                arch.append(form)
            else:
                notebook = XML('<notebook position="inside"></notebook>')
                arch.append(notebook)
            page = XML(page_meta_fields_template % self.meta_tab_label)
            notebook.append(page)
            if node_group:
                groups = divide_list(node_group)
                group_main = XML(group_template)
                for g in groups:
                    group = XML(group_template)
                    for n in g:
                        group.append(n)
                    group_main.append(group)
                page.append(group_main)
        return arch

    def make_form_view(self):
        view_obj = self.env['ir.ui.view'].sudo()
        data = XML('<data/>')
        arch = XML(container_template)
        data.append(arch)
        self.make_form_meta_fields(data)
        view_data = {'name': f'solt_api_connector{self.id}.{self.model}.form.view', 'type': 'form', 'model': self.model, 'inherit_id': self.form_view_id.id, 'mode': 'extension', 'arch': tostring(data, pretty_print=True)}
        # update or create view
        view = self.extended_form_view_id.sudo()
        if not view:
            view = view_obj.create(view_data)
            self.env['ir.model.data']._update_xmlids([{'xml_id': f"solt_api_connector.solt_api_connector{self.id}_{self.model.replace('.', '_')}_form_view", 'record': view, 'noupdate': True, }])
            self.write({'extended_form_view_id': view.id})
        else:
            view.write(view_data)

    def make_search_view(self):
        if self.search_view_id:
            state_field = False
            if self.ir_meta_field_ids:
                state_field = self.ir_meta_field_ids.filtered(lambda f: f.name == 'x_state_sync')
            if state_field:
                view_obj = self.env['ir.ui.view'].sudo()
                data = XML('<data/>')
                arch = XML("""<xpath expr="//search" position="inside"></xpath>""")
                data.append(arch)
                arch.append(XML(_("""<filter string="Estado de sincronización" name="%(state)s" domain="[]" context="{'group_by':'%(state)s'}"/>""", state=state_field.name)))

                view_data = {'name': f"{self.model}.{self.search_view_id.id}.api.connector.search.view", 'type': 'search', 'model': self.model, 'inherit_id': self.search_view_id.id, 'mode': 'extension', 'arch': tostring(data, pretty_print=True)}
                # update or create view
                xml_id = f"solt_api_connector.{self.model.replace('.', '_')}_{self.search_view_id.id}_api_connector_search_view"
                view = self.env.ref(xml_id, raise_if_not_found=False)
                if view and self.extended_search_view_id != view:
                    self.extended_search_view_id = view.id
                view = self.extended_search_view_id.sudo()
                if not view:
                    view = view_obj.create(view_data)
                    self.env['ir.model.data']._update_xmlids([{'xml_id': xml_id, 'record': view, 'noupdate': True, }])
                    self.write({'extended_search_view_id': view.id})
                else:
                    view.write(view_data)

    def make_views(self):
        self.ensure_one()
        if self.form_view_id:
            self.make_form_view()
        if self.search_view_id:
            self.make_search_view()
        if self.list_view_id:
            self.make_tree_view()
        return True

    def create_or_update_field(self, ir_meta_field_ids):
        self.ensure_one()
        field_obj = self.env['ir.model.fields'].sudo()
        fd_obj = self.env['ir.model.fields'].sudo()
        for mf_dict in ir_meta_field_ids:
            mf_dict.update({'copied': False, 'model_id': self.model_id.id, 'model': self.model_id.model, 'modules': 'solt_api_connector, ' + self.model_id.modules})
            field_name = mf_dict.get('name')
            fd_id = field_obj.search([('name', '=', field_name), ('model_id', '=', self.model_id.id)])
            if not fd_id:
                fd_id = field_obj.create(mf_dict)

                xml_id = f"base.field_{fd_id.model.replace('.', '_')}__{fd_id.name}"
                if not self.env.ref(xml_id, raise_if_not_found=False):
                    self.env['ir.model.data']._update_xmlids([{'xml_id': xml_id, 'record': fd_id, 'noupdate': False, }])
            else:
                self.env.cr.execute("""
                                        UPDATE ir_model_fields line
                                        SET api_meta_field_id = %s
                                        WHERE id = %s
                                    """, (self.id, fd_id.id))
            fd_obj |= fd_id

        return fd_obj

    def make_tree_view(self):
        if self.list_view_id:
            view_obj = self.env['ir.ui.view'].sudo()
            data = XML('<data/>')
            arch = XML("""<xpath expr="//list" position="inside"></xpath>""")
            data.append(arch)
            arch.append(XML(tree_field_template % {'tree_field': 'x_store_external_id'}))
            arch.append(XML(tree_field_template % {'tree_field': 'x_date_last_sync'}))
            arch.append(XML(tree_field_template % {'tree_field': 'x_state_sync'}))
            arch.append(XML("""<field name="%(tree_field)s" readonly="True" optional="hide"/>""" % {'tree_field': 'x_external_id'}))
            arch.append(XML("""<field name="%(tree_field)s" readonly="False" optional="hide"/>""" % {'tree_field': 'x_exclud_from_sync'}))
            view_data = {'name': f"{self.model}.{self.list_view_id.id}.api.connector.list.view", 'type': 'list', 'model': self.model, 'inherit_id': self.list_view_id.id, 'mode': 'extension', 'arch': tostring(data, pretty_print=True)}
            # update or create view
            xml_id = f"solt_api_connector.{self.model.replace('.', '_')}_{self.list_view_id.id}_api_connector_list_view"
            view = self.env.ref(xml_id, raise_if_not_found=False)
            if view and self.extended_list_view_id != view:
                self.extended_list_view_id = view.id
            view = self.extended_list_view_id.sudo()
            if not view:
                view = view_obj.create(view_data)
                self.env['ir.model.data']._update_xmlids([{'xml_id': xml_id, 'record': view, 'noupdate': True, }])
                self.write({'extended_list_view_id': view.id})
            else:
                view.write(view_data)

    def add_dynamic_fields_to_extended_view(self, model, new_field_names):
        # Buscar la vista extendida
        self.ensure_one()
        meta_fields = self
        view = meta_fields.extended_form_view_id
        if not view:
            return

        arch = view.arch
        doc = etree.fromstring(arch)

        # Buscar la página de sincronización por name
        sync_page = doc.xpath("//page[@name='meta_fields']")
        if not sync_page:
            return

        # Crear un nuevo group y añadir los campos
        node_group = []
        fields_attrs = []
        for mf in new_field_names:
            if mf in fields_attrs:
                continue  # raise UserError(_('Field %s already exists, the same field can only be in one.' % mf))
            node = XML(field_template % mf)
            node_group.append(node)
            fields_attrs.append(mf)

        if node_group:
            groups = divide_list(node_group)
            group_main = XML(group_template)
            for g in groups:
                group = XML(group_template)
                for n in g:
                    group.append(n)
                group_main.append(group)
            sync_page[0].append(group_main)

        # Guardar la vista modificada
        new_arch = etree.tostring(doc, encoding='unicode')
        view.write({'arch': new_arch})
