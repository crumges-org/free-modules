# -*- coding: utf-8 -*-

import json
import logging
from odoo import models, fields, api, Command, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = ['product.template', 'solt.integration.model.mixin', 'connector.sync.mixin']

    product_depth = fields.Float(
        'Depth', compute='_compute_product_depth', digits='Stock Weight',
        inverse='_set_product_depth', store=True)
    product_depth_uom_name = fields.Char(string='Depth UoM label',
                                         compute='_compute_product_depth_uom_name')
    product_height = fields.Float(
        'Height', compute='_compute_product_height', digits='Stock Weight',
        inverse='_set_product_height', store=True)
    product_height_uom_name = fields.Char(string='Height UoM label',
                                          compute='_compute_product_height_uom_name')
    product_width = fields.Float(
        'Width', compute='_compute_product_width', digits='Stock Weight',
        inverse='_set_product_width', store=True)
    product_width_uom_name = fields.Char(string='Width UoM label',
                                         compute='_compute_product_width_uom_name')
    product_image_ids = fields.One2many('solt.product.image', 'product_tmpl_id', string='Extra Images',
        copy=True,
    )
    nube_free_shipping = fields.Boolean("Free shipping")
    nube_requires_shipping = fields.Boolean("Requires shipping", compute="_compute_nube_requires_shipping", store=True,
                                            help="True if the product is physical, False when it is a service")
    website_description = fields.Html(string='Description', sanitize=False, translate=True)
    website_seo_metatitle = fields.Char(string='SEO meta title', translate=True,)
    website_seo_description = fields.Char(string='SEO description', translate=True)
    promotional_price = fields.Float('Promotional price', digits='Product Price', compute='_compute_promotional_price',
                                     inverse='_set_promotional_price', store=True)
    is_published = fields.Boolean('Published', copy=False, default=False, index=True)
    categ_ids_domain = fields.Char(compute='_compute_domain_categ_ids')
    company_id = fields.Many2one(
        'res.company', 'Company', index=True, default=lambda self: self.env.company)
    nube_video_url = fields.Char("YouTube or Vimeo URL", help="Product video URL hosted on YouTube or Vimeo")

    # Product Brand fields
    @api.model
    def _get_brand_domain(self):
        domain = [('company_id', '=', False)]
        if self.env.user.has_group('base.group_multi_company'):
            domain = ['|'] + domain + [('company_id', 'parent_of', self.env.company.id)]
        else:
            domain = ['|'] + domain + [('company_id', '=', self.env.company.id)]
        return domain

    product_brand_id = fields.Many2one(
        "solt.product.brand", string="Brand", help="Select a brand for the product",
        domain=lambda self: self._get_brand_domain()
    )

    # Product Multi Category fields
    categ_ids = fields.Many2many(
        comodel_name="product.category",
        relation="product_categ_rel",
        column1="product_tmpl_id",
        column2="categ_id",
        string="Categories",
        help="Additional categories for product classification. Categories created by store connectors."
    )

    @api.depends('product_variant_ids.product_depth')
    def _compute_product_depth(self):
        self._compute_template_field_from_variant_field('product_depth')

    def _set_product_depth(self):
        self._set_product_variant_field('product_depth')

    @api.depends('product_variant_ids.product_height')
    def _compute_product_height(self):
        self._compute_template_field_from_variant_field('product_height')

    def _set_product_height(self):
        self._set_product_variant_field('product_height')

    @api.depends('product_variant_ids.product_width')
    def _compute_product_width(self):
        self._compute_template_field_from_variant_field('product_width')

    def _set_product_width(self):
        self._set_product_variant_field('product_width')

    @api.depends('type')
    def _compute_product_depth_uom_name(self):
        self.product_depth_uom_name = self._get_measure_uom_name_from_ir_config_parameter()

    @api.depends('type')
    def _compute_product_height_uom_name(self):
        self.product_height_uom_name = self._get_measure_uom_name_from_ir_config_parameter()

    @api.depends('type')
    def _compute_product_width_uom_name(self):
        self.product_width_uom_name = self._get_measure_uom_name_from_ir_config_parameter()

    @api.model
    def _get_measure_uom_name_from_ir_config_parameter(self):
        return self._get_measure_uom_id_from_ir_config_parameter().display_name

    @api.model
    def _get_measure_uom_id_from_ir_config_parameter(self):
        """Return the unit of measure used for depth, width, and height fields.
        Centimeters are used by default, but users can set the ir.config_parameter
        `solt_tiendanube.measure_in_cm` to `1` to force centimeters explicitly.
        """
        product_measure_in_cm_param = self.env['ir.config_parameter'].sudo().get_param('solt_tiendanube.measure_in_cm')
        if product_measure_in_cm_param == '1':
            return self.env.ref('uom.product_uom_cm')
        else:
            return self.env.ref('uom.product_uom_millimeter')

    @api.depends('product_variant_ids.promotional_price')
    def _compute_promotional_price(self):
        self._compute_template_field_from_variant_field('promotional_price')

    def _set_promotional_price(self):
        self._set_product_variant_field('promotional_price')

    def _get_related_fields_variant_template(self):
        fields = super(ProductTemplate, self)._get_related_fields_variant_template()
        return ['product_depth', 'product_height', 'product_width', 'promotional_price'] + fields

    @api.depends('type')
    def _compute_nube_requires_shipping(self):
        for record in self:
            if record.type == 'service':
                record.nube_requires_shipping = False
            else:
                record.nube_requires_shipping = True

    @api.depends_context('company')
    @api.depends('company_id')
    def _compute_domain_categ_ids(self):
        Category = self.env['product.category']
        for record in self:
            record = record.with_company(record.company_id or self.env.company)
            fields_in_model = Category.fields_get().keys()

            record.categ_ids_domain = json.dumps([])
            if 'x_external_id' in fields_in_model and 'x_exclud_from_sync' in fields_in_model:
                record.categ_ids_domain = json.dumps([('x_external_id', 'not in', [False, '']), ('x_exclud_from_sync', '=', False), ('x_store_external_id', '=', self.env.company.external_id)])

    # categories
    def _get_categ_ids(self, data):
        values_list = []

        if isinstance(data, list):
            values_list = data
        elif isinstance(data, dict):
            values_list = [data]
        else:
            return []

        id_map = {cat['id']: cat for cat in values_list}
        created_map = {}
        Category = self.env['product.category'].sudo()

        def _create_or_get_category(cat_dict):
            """Search for a product category in Odoo or create it if needed."""
            external_id = cat_dict['id']
            if external_id in created_map:
                return created_map[external_id]

            existing_cat = Category.search([('x_external_id', '=', external_id)], limit=1)
            if existing_cat:
                created_map[external_id] = existing_cat
                return existing_cat

            # Process parent (if any)
            parent_id = False
            parent_external_id = cat_dict.get('parent')
            if parent_external_id:
                parent_cat = id_map.get(parent_external_id)
                if parent_cat:
                    parent_id = _create_or_get_category(parent_cat).id
                else:
                    # Look in the database when the parent is not part of the payload
                    existing_parent = Category.search([('x_external_id', '=', parent_external_id)], limit=1)
                    parent_id = existing_parent.id if existing_parent else False

            pop_parent = cat_dict.pop('parent', None)
            endpoint = self._get_endpoint_by_code('CATEG_ALL_GET')
            response = endpoint._process_response(cat_dict, target_record=Category)
            values = response.get('values')
            values.update({'parent_id': parent_id})
            new_cat = Category.create(values)
            created_map[external_id] = new_cat
            return new_cat

        # Create or retrieve every category
        categ_ids = Category.browse()
        for cat in values_list:
            cat_rec = _create_or_get_category(cat)
            categ_ids |= cat_rec

        return [Command.set(categ_ids.ids)]

    # variants
    def create_product_variants_from_json(self, json_data, update_from_store=True):
        """Create product variants in Odoo based on Tiendanube JSON payloads."""
        try:
            if isinstance(json_data, str):
                try:
                    json_data = json.loads(json_data)
                except json.JSONDecodeError as e:
                    _logger.error(f"Error decoding JSON: {e}")
                    return False

            if isinstance(json_data, list):
                values_list = json_data
            elif isinstance(json_data, dict):
                values_list = [json_data]
            else:
                return []

            id_map = {str(tmpl['id']): tmpl for tmpl in values_list}
            store_id = self.env.company.external_id
            product_variant_ids = self.env['product.product']
            for product in self:
                product_data = id_map.get(product.x_external_id)

                # Create or find attributes and values
                attributes_data = product_data.get('attributes', [])
                variants_data = product_data.get('variants', [])
                product_external_id = str(product_data.get('id'))

                # Check if product has variants
                has_valid_variants = product._validate_variants(variants_data, attributes_data)

                if has_valid_variants:
                    product._process_attributes_values_product_data(attributes_data, variants_data, product_external_id,
                                                                    store_id, update_from_store)
                else:
                    # Handle simple product without variants
                    product._create_simple_product(product_data, store_id)
                products = self.env['product.product'].search([('product_tmpl_id', '=', product.id), ('x_store_external_id', '=', store_id)])
                product_variant_ids |= products
            return product_variant_ids
        except Exception as e:
            _logger.error(f"Error while creating products: {e}")
            return False

    def _process_attributes_values_product_data(self, attributes_data, variants_data, product_external_id, store_id, update_from_store):
        """Process attribute lines, values, and variants for the given template."""
        self.ensure_one()
        # Dict to store attribute and its values {attribute_id: [value_ids]}
        attributes_values_map = {}

        # Process attributes and values
        for idx, attr_dict in enumerate(attributes_data):
            # Get attribute name
            attr_name = self.convert_translated_field_to_odoo_format(attr_dict)
            if not attr_name:
                continue

            # Find or create attribute
            attribute = self._find_or_create_attribute(attr_name, product_external_id, store_id)

            # Collect all values
            unique_values = set()
            for variant in variants_data:
                values = variant.get('values', [])
                if len(values) > idx:
                    value = self.convert_translated_field_to_odoo_format(values[idx])
                    if value:
                        unique_values.add(value)

            # Create attribute values if not exists
            value_ids = []
            for value in unique_values:
                value_id = self._find_or_create_attribute_value(attribute.id, value, product_external_id, store_id)
                value_ids.append(value_id)

            attributes_values_map[attribute.id] = value_ids

        # Associate attribute and values with product template
        self._associate_attribute_with_product(attributes_values_map)
        # Create product variants
        self._create_product_variants(variants_data, attributes_data, store_id, update_from_store)

        # Handle removal of variants that no longer exist in the external system
        self._handle_removed_variants(variants_data)

    def _find_or_create_attribute(self, attr_name, product_external_id, store_id):
        """Find or create a product attribute."""
        try:
            self.ensure_one()
            ProductAttribute = self.env['product.attribute']

            attribute = ProductAttribute.search([('name', '=', attr_name)], limit=1)
            current_time = fields.Datetime.now()

            if not attribute:
                attribute = ProductAttribute.create({
                    'name': attr_name,
                    'create_variant': 'always',
                    'display_type': 'select',
                    'x_external_id': "",
                    # 'x_store_external_id': store_id,
                    'x_state_sync': 'yes',
                    'x_exclud_from_sync': False,
                    'x_date_last_sync': current_time,
                })
            else:
                # Update sync fields
                attribute.write({
                    'x_state_sync': 'yes',
                    'x_date_last_sync': current_time,
                })

            return attribute
        except Exception as e:
            _logger.error(f"Error while finding or creating the attribute: {e}")
            raise

    def _find_or_create_attribute_value(self, attribute_id, value_name, product_external_id, store_id):
        """Find or create an attribute value."""
        try:
            ProductAttributeValue = self.env['product.attribute.value']

            value = ProductAttributeValue.search([
                ('attribute_id', '=', attribute_id),
                ('name', '=', value_name)
            ], limit=1)
            if not value:
                value = ProductAttributeValue.create({
                    'attribute_id': attribute_id,
                    'name': value_name,
                })
            return value.id
        except Exception as e:
            _logger.error(f"Error while finding or creating an attribute value: {e}")
            raise

    def _associate_attribute_with_product(self, attributes_values_map):
        """Associate attribute/value lines with the current product template."""
        try:
            self.ensure_one()
            # self = self.with_context(ctx)
            ProductTemplateAttributeLine = self.env['product.template.attribute.line']

            for attribute_id, value_ids in attributes_values_map.items():
                # Check if attribute is already associated
                existing_line = ProductTemplateAttributeLine.search([
                    ('product_tmpl_id', '=', self.id),
                    ('attribute_id', '=', attribute_id)
                ], limit=1)

                if existing_line:
                    # Update values
                    existing_line.write({
                        'value_ids': [(6, 0, value_ids)]
                    })
                else:
                    # Create new association
                    ProductTemplateAttributeLine.create({
                        'product_tmpl_id': self.id,
                        'attribute_id': attribute_id,
                        'value_ids': [(6, 0, value_ids)]
                    })
        except Exception as e:
            _logger.error(f"Error while associating attributes with product: {e}")
            raise

    def _create_product_variants(self, variants_data_list, attributes_data, store_id, update_from_store):
        """Create product.product variants based on the processed attribute lines."""
        try:
            self.ensure_one()
            ProductProduct = self.env['product.product']

            # Get template attribute lines
            attribute_lines = self.attribute_line_ids
            current_time = fields.Datetime.now()
            ctx = dict(self.env.context)
            ctx.update({'create_product_product': False})

            for variant_data in variants_data_list:
                # Get values for this variant
                values_data = variant_data.get('values', [])
                variant_external_id = str(variant_data.get('id', ''))

                # Prepare attribute value combinations for this variant
                value_ids = []  # product.template.attribute.value IDs

                for idx, value_dict in enumerate(values_data):
                    value_name = self.convert_translated_field_to_odoo_format(value_dict)
                    if not value_name or idx >= len(attributes_data):
                        continue

                    attr_name = self.convert_translated_field_to_odoo_format(attributes_data[idx])
                    if not attr_name:
                        continue

                    # Find attribute line
                    attr_line = attribute_lines.filtered(lambda l: l.attribute_id.name == attr_name)
                    if not attr_line:
                        continue

                    # Find attribute value
                    attr_value = attr_line.value_ids.filtered(lambda v: v.name == value_name)
                    if not attr_value:
                        continue

                    # Add to value_ids
                    ptav = self.env['product.template.attribute.value'].search([
                        ('product_tmpl_id', '=', self.id),
                        ('attribute_id', '=', attr_line.attribute_id.id),
                        ('product_attribute_value_id', '=', attr_value.id)
                    ], limit=1)

                    if ptav:
                        value_ids.append(ptav.id)

                # Create or update variant
                variant_values_to_write = self._prepare_variant_values_from_json(variant_data)
                sync_values = {
                    'x_external_id': variant_external_id,
                    'x_store_external_id': store_id,
                    'x_state_sync': 'yes',
                    'x_exclud_from_sync': False,
                    'x_date_last_sync': current_time,
                    "company_id": self.env.company.id,
                    'active': True
                }

                # First try to find by external ID
                variant = ProductProduct.with_context(active_test=False).search([
                    ('x_external_id', '=', variant_external_id),
                    ('x_store_external_id', '=', store_id),
                    ('product_tmpl_id', '=', self.id)
                ], limit=1)

                # If not found by external ID, try by attribute combination
                if not variant and value_ids:
                    domain = [
                        ('product_tmpl_id', '=', self.id),
                        ('product_template_attribute_value_ids', '=', False)  # Reset condition
                    ]
                    all_variants = ProductProduct.search([('product_tmpl_id', '=', self.id)])
                    for var in all_variants:
                        if set(var.product_template_attribute_value_ids.ids) == set(value_ids):
                            variant = var
                            break

                    # Add each attribute value to the domain
                    # for value_id in value_ids:
                    #     domain.append(('product_template_attribute_value_ids', 'in', [value_id]))
                    #
                    # variant = ProductProduct.search(domain, limit=1)

                variant_values_to_write = {**variant_values_to_write, **sync_values}
                if variant:
                    if not update_from_store:
                        variant_values_to_write = {**sync_values}
                    # Update variant
                    variant.write(variant_values_to_write)
                else:
                    # Create new variant with specific attribute combination
                    if value_ids:
                        # Create the variant manually with the specific attribute combination
                        variant_values_to_write.update({
                            'product_tmpl_id': self.id,
                            'product_template_attribute_value_ids': [(6, 0, value_ids)]
                        })

                        new_variant = ProductProduct.create(variant_values_to_write)
                        _logger.info(f"Created new variant {new_variant.id} with external_id {variant_external_id}")
                    # variant_values_to_write = {**variant_values_to_write, **sync_values}
                    # The variant will be created automatically by Odoo when setting the template attribute values
                    # We need to find the newly created variant and update it
                    # if value_ids:
                    #     # Force creation of variants
                    #     self._create_variant_ids()
                    #
                    #     # Search again for the variant
                    #     domain = [('product_tmpl_id', '=', self.id)]
                    #
                    #     for value_id in value_ids:
                    #         domain.append(('product_template_attribute_value_ids', 'in', [value_id]))
                    #
                    #     variant = ProductProduct.search(domain, limit=1)
                    #
                    #     if variant:
                    #         variant.write(variant_values_to_write)
        except Exception as e:
            _logger.error(f"Error while creating product variants: {e}")
            raise

    def _handle_removed_variants(self, variants_data, store_id=None):
        """Mark variants as not synchronized if they no longer exist in the external system"""
        self.ensure_one()
        ProductProduct = self.env['product.product']

        # Get all external IDs from the variants data
        external_ids = [str(v.get('id', '')) for v in variants_data if v.get('id')]

        # Find variants of this template that have an external_id but not in the current data
        variants_to_mark = ProductProduct.search([
            ('product_tmpl_id', '=', self.id),
            ('x_store_external_id', '=', store_id),
            ('x_external_id', 'not in', external_ids),
            ('x_external_id', '!=', False)
        ])

        if variants_to_mark:
            variants_to_mark.write({
                'x_state_sync': 'no',
                'x_date_last_sync': fields.Datetime.now(),
                'x_exclud_from_sync': True,
            })

    def _prepare_variant_values_from_json(self, variant_data):
        if not isinstance(variant_data, dict):
            return {}
        standard_price = variant_data.get('cost', 0.0)
        lst_price = variant_data.get('price', 0.0)
        weight = variant_data.get('weight', 0.0)
        product_depth = variant_data.get('depth', 0.0)
        product_height = variant_data.get('height', 0.0)
        product_width = variant_data.get('width', 0.0)
        promotional_price = variant_data.get('promotional_price', 0.0)
        return {
            'default_code': variant_data.get('sku', ''),
            'barcode': variant_data.get('barcode', ''),
            'standard_price': float(standard_price) if standard_price else 0.0,
            'lst_price': float(lst_price) if lst_price else 0.0,
            'weight': float(weight) if weight else 0.0,
            'product_depth': float(product_depth) if product_depth else 0.0,
            'product_height': float(product_height) if product_height else 0.0,
            'product_width': float(product_width) if product_width else 0.0,
            'promotional_price': float(promotional_price) if promotional_price else 0.0,
            'visible': variant_data.get('visible', ''),
        }

    def _validate_variants(self, variants_data, attributes_data):
        """Return True when the product has proper variants; otherwise False."""
        # Check if there are attribute definitions and variants
        if not attributes_data or not variants_data:
            return False

        # Check if variants have values defined
        for variant in variants_data:
            if variant.get('values'):
                return True

        return False

    def _create_simple_product(self, product_data, store_id):
        """Create or update a simple product without variants."""
        try:
            self.ensure_one()
            ProductProduct = self.env['product.product']
            current_time = fields.Datetime.now()

            # Obtain the external ID of the product
            product_external_id = str(product_data.get('id', ''))

            # Ensure there is at least one variant in the payload
            variants_data = product_data.get('variants', [])
            if not variants_data:
                _logger.warning(f"Product {product_external_id} does not contain variants")
                return False

            # For simple products retrieve the first (and only) variant payload
            variant_data = variants_data[0]
            variant_external_id = str(variant_data.get('id', ''))

            # Search for an existing variant by external ID
            variant = ProductProduct.search([
                ('x_external_id', '=', variant_external_id),
                ('x_store_external_id', '=', store_id),
                ('product_tmpl_id', '=', self.id)
            ], limit=1)

            # Fallback to the default variant when external ID lookup fails
            if not variant:
                variant = ProductProduct.search([
                    ('product_tmpl_id', '=', self.id)
                ], limit=1)

            # Add sync bookkeeping fields
            variant_values = {
                'x_external_id': variant_external_id,
                'x_store_external_id': store_id,
                'x_state_sync': 'yes',
                'x_exclud_from_sync': False,
                'x_date_last_sync': current_time,
                "company_id": self.env.company.id
            }

            # Update or create the variant with sync information
            variant.write(variant_values)
        except Exception as e:
            _logger.error(f"Error while creating simple product: {e}")
            raise

    # images
    @api.model_create_multi
    def create(self, vals_list):
        templates = super(ProductTemplate, self).create(vals_list)
        # Skip automatic image creation when the context asks for it
        if self.env.context.get('skip_solt_image_create'):
            return templates
        # Create solt.product.image entries for new templates with images
        for template in templates:
            if template.image_1920:
                template._create_product_image(template.image_1920)
        return templates

    def write(self, vals):
        # Skip automatic image creation when the context asks for it
        if self.env.context.get('skip_solt_image_create'):
            return super(ProductTemplate, self).write(vals)
        # Check if the image is being updated
        if 'image_1920' in vals and vals['image_1920']:
            for template in self:
                # Find if there's already a main image (sequence=1)
                image_ids = self.env['solt.product.image'].search([('product_tmpl_id', '=', template.id)],
                                                                  order='sequence asc', limit=1)

                if image_ids:
                    # Update the sequence
                    main_image = image_ids[0]
                    main_image.write({
                        'sequence': max(image_ids.mapped('sequence'), default=0) + 1
                    })
                template._create_product_image(vals['image_1920'])

        result = super(ProductTemplate, self).write(vals)
        return result

    def _create_product_image(self, image):
        self.ensure_one()
        image_id = self.env['solt.product.image'].create({
            'name': self.name,
            'image_1920': image,
            'product_tmpl_id': self.id,
            'sequence': 1,  # Set as main image
        })

        return image_id

    def _sync_product_images_from_json(self, json_data):
        """Sync product images coming from the Tiendanube JSON payload."""

        def _remove_all_product_images(product_template):
            """Remove every stored image for the provided template."""
            try:
                # Search all product images
                all_images = self.env['solt.product.image'].sudo().search([
                    ('product_tmpl_id', '=', product_template.id)
                ])

                if all_images:
                    all_images.write({'x_exclud_from_sync': True})  # para que no se ejecute la RA
                    _logger.info(
                        f"Removing all images ({len(all_images)}) for product {product_template.name}")
                    all_images.unlink()

                # Clear product main image
                product_template.with_context(skip_solt_image_create=True).write({
                    'image_1920': False
                })

                # Clear variant images
                variants = self.env['product.product'].search([
                    ('product_tmpl_id', '=', product_template.id)
                ])
                for variant in variants:
                    variant.with_context(skip_product_image_create=True).write({
                        'image_variant_1920': False
                    })

            except Exception as e:
                _logger.error(f"Error while removing all product images: {e}")
                raise

        try:
            if isinstance(json_data, str):
                try:
                    json_data = json.loads(json_data)
                except json.JSONDecodeError as e:
                    _logger.error(f"Error decoding JSON: {e}")
                    return False

            if isinstance(json_data, list):
                values_list = json_data
            elif isinstance(json_data, dict):
                values_list = [json_data]
            else:
                return []

            store_id = self.env.company.external_id
            for product_data in values_list:
                external_product_id = str(product_data.get('id'))
                product_template = self.env['product.template'].search([
                    ('x_external_id', '=', external_product_id), ('x_store_external_id', '=', store_id)
                ], limit=1)

                if not product_template:
                    _logger.warning(f"No product found with external ID: {external_product_id}")
                    return
                _logger.info(f"Updating images for product: {product_template.name}")
                images_data = product_data.get('images', [])
                if not images_data:
                    _logger.info(f"Product {product_template.name} does not contain images")
                    _remove_all_product_images(product_template)
                    continue

                # Sort images by position to determine the main image
                images_data.sort(key=lambda x: x.get('position', 999))
                # Process images and keep track of the processed ones
                self._process_image(images_data, product_template, product_data)
        except Exception as e:
            _logger.error(f"Error while syncing product images: {e}")
            raise

    def _process_image(self, images_data, product_template, product_data):
        """Process images coming from Tiendanube payloads."""

        def _remove_obsolete_images(product_template, processed_external_image_ids, product_data):
            """Remove images that no longer exist in Tiendanube."""
            try:
                # Search all product images that were not processed
                obsolete_images = self.env['solt.product.image'].search([
                    ('product_tmpl_id', '=', product_template.id),
                    ('x_external_id', 'not in', processed_external_image_ids),
                    ('x_external_id', '!=', False)  # Only images with an external ID
                ])

                if obsolete_images:
                    obsolete_images.write({'x_exclud_from_sync': True})  # para que no se ejecute la RA
                    _logger.info(
                        f"Removing {len(obsolete_images)} obsolete images for product {product_template.name}")
                    obsolete_images.unlink()

            except Exception as e:
                _logger.error(f"Error while removing obsolete images: {e}")
                raise
        current_time = fields.Datetime.now()
        store_id = self.env.company.external_id
        # Get existing product images to avoid duplicates
        existing_images = self.env['solt.product.image'].search([
            ('product_tmpl_id', '=', product_template.id)
        ])

        # Track external image IDs that we're processing
        processed_external_image_ids = []

        # Determine the main image (the one with the lowest position)
        main_image_position = min(
            [img.get('position', 999) for img in product_data.get('images', [])]) if product_data.get('images') else 999

        for img_data in images_data:
            external_image_id = str(img_data.get('id'))
            image_url = img_data.get('src')
            position = img_data.get('position', 10)

            if not image_url:
                continue

            try:
                # Check if image already exists
                existing_image = existing_images.filtered(
                    lambda i: i.x_external_id == external_image_id
                )

                # Determinar si es la imagen principal
                is_main_image = (position == main_image_position)

                processed_external_image_ids.append(external_image_id)

                # Preparar valores base para la imagen
                image_vals = {
                    'sequence': position,
                    'product_tmpl_id': product_template.id,
                }

                if existing_image:
                    # Only refresh content when dealing with the main image
                    if is_main_image:
                        _logger.info(f'Updating existing main image (ID: {external_image_id})')

                        # Download the image only when it is the main one
                        image_content = self.env['solt.product.image']._get_image_from_url(image_url)

                        # Update the existing image
                        image_vals.update({
                            'x_state_sync': 'yes',
                            'image_1920': image_content,
                            'x_date_last_sync': current_time
                        })
                        existing_image.with_context(not_execute_product_image_base_automation=True).write(image_vals)

                        # Update the product cover
                        product_template.with_context(skip_solt_image_create=True).write({
                            'image_1920': image_content
                        })

                        product_image = existing_image
                    else:
                        # Metadata-only refresh for secondary images
                        _logger.info(
                            f'Secondary image exists, metadata only update (ID: {external_image_id})')

                        metadata_vals = {
                            'sequence': position,
                            'x_state_sync': 'yes',
                            'x_date_last_sync': current_time
                        }
                        existing_image.with_context(not_execute_product_image_base_automation=True).write(metadata_vals)
                        product_image = existing_image

                else:
                    # Create a new image (main or secondary)
                    _logger.info(f'Creating new image (ID: {external_image_id}, Main: {is_main_image})')

                    # Download the original file
                    image_content = self.env['solt.product.image']._get_image_from_url(image_url)

                    image_vals.update({
                        'name': product_template.display_name,
                        'image_1920': image_content,
                        'x_external_id': external_image_id,
                        'x_store_external_id': store_id,
                        'x_state_sync': 'yes',
                        'x_exclud_from_sync': False,
                        'x_date_last_sync': current_time,
                    })
                    product_image = self.env['solt.product.image'].with_context(not_execute_product_image_base_automation=True).create(image_vals)

                    # Update the product cover when this is the main image
                    if is_main_image:
                        _logger.info('Updating product cover image')
                        product_template.with_context(skip_solt_image_create=True).write({
                            'image_1920': image_content
                        })

                # Associate variants that reuse this image
                self._associate_variants_with_image(product_data, external_image_id, product_image, product_template)

            except Exception as e:
                _logger.error(f"Error processing image with external ID {external_image_id} for product {product_template.name}: {e}")
                raise

        if processed_external_image_ids:
            _remove_obsolete_images(product_template, processed_external_image_ids, product_data)

        return processed_external_image_ids

    def _associate_variants_with_image(self, product_data, external_image_id, product_image, product_template):
        """Associate variants with an image according to the JSON payload image_id."""
        if 'variants' not in product_data:
            return

        variants_using_image = []
        for variant_data in product_data.get('variants', []):
            if variant_data.get('image_id', False) and str(variant_data.get('image_id')) == external_image_id:
                external_variant_id = str(variant_data.get('id'))
                variant = self.env['product.product'].search([
                    ('product_tmpl_id', '=', product_template.id),
                    ('x_external_id', '=', external_variant_id)
                ], limit=1)

                if variant:
                    variants_using_image.append(variant.id)

                    # Actualizar la imagen de la variante sin crear una nueva entrada en solt.product.image
                    _logger.info('Updating variant image')
                    variant.with_context(skip_product_image_create=True).write({
                        'image_variant_1920': product_image.image_1920
                    })

        # Update product_variant_ids with the variants that use this image
        if variants_using_image:
            product_image.product_variant_ids = [(6, 0, variants_using_image)]

    # inventory adjustment
    def _create_or_write_stock_quants_from_json(self, json_data):
        """Create or update stock.quant records from the Tiendanube payload."""
        try:
            if isinstance(json_data, str):
                try:
                    json_data = json.loads(json_data)
                except json.JSONDecodeError as e:
                    _logger.error(f"Error decoding JSON: {e}")
                    return False
            if isinstance(json_data, list):
                values_list = json_data
            elif isinstance(json_data, dict):
                values_list = [json_data]
            else:
                return []

            store_id = self.env.company.external_id
            values_to_create = []
            StockQuant = self.env['stock.quant'].sudo()
            quant_ids = self.env['stock.quant'].sudo()
            for product_data in values_list:
                external_product_id = str(product_data.get('id'))
                product_template = self.env['product.template'].search([
                    ('x_external_id', '=', external_product_id), ('x_store_external_id', '=', store_id)
                ], limit=1)

                if not product_template:
                    _logger.warning(f"No product found with external ID: {external_product_id}")
                    return
                variants_data = product_data.get('variants', [])
                if not variants_data:
                    return

                for variant in variants_data:
                    external_id = str(variant.get('id'))
                    product_id = self.env['product.product'].search([
                        ('x_external_id', '=', external_id), ('x_store_external_id', '=', store_id)
                    ], limit=1)
                    if not product_id:
                        _logger.warning(f"No product variant found with external ID: {external_id}")
                        return

                    if product_id.type == 'consu' and product_id.is_storable:
                        inventory_levels_data = variant.get('inventory_levels')
                        for inv_level in inventory_levels_data:
                            external_wh_id = str(inv_level.get('location_id'))
                            warehouse_id = self.env['stock.warehouse'].search([
                                ('x_external_id', '=', external_wh_id), ('x_store_external_id', '=', store_id)
                            ], limit=1)
                            if not warehouse_id:
                                _logger.warning(f"No warehouse found with external ID: {external_wh_id}")
                                continue

                            stock = inv_level.get('stock')
                            vals = {
                                'inventory_quantity': float(stock) if stock else 0,
                                'product_id': product_id.id,
                                'location_id': warehouse_id.lot_stock_id.id,
                            }
                            values_to_create.append(vals)

            if values_to_create:
                quants = StockQuant.with_context(not_execute_quants_base_automation=True).create(values_to_create)
                quant_ids |= quants
            if quant_ids:
                quant_ids.with_context(inventory_name=f"Initial import from store {self.env.company.name}").action_apply_inventory()
        except Exception as e:
            _logger.error(f"Error preparing stock quant data: {e}")
            raise

    def _get_category_hierarchy(self, category):
        """Return the hierarchy for a category including all parents."""
        categories = [category.id]
        if category.parent_id:
            categories.extend(self._get_category_hierarchy(category.parent_id))
        return categories

    @api.onchange('categ_ids')
    def _onchange_categ_ids_alternative(self):
        if not self.categ_ids:
            return

        all_categories = set()

        for category in self.categ_ids:
            hierarchy = self._get_category_hierarchy(category)
            all_categories.update(hierarchy)

        self.categ_ids = [(6, 0, list(all_categories))]

    def _can_update_product_cost(self):
        for product in self:
            if product.x_exclud_from_sync:
                raise UserError(
                    _("The product is excluded from synchronization with external systems"))
            if not product.company_id:
                raise UserError(_("The product does not have a company assigned."))
            product.company_id._check_external_config()

            if product.x_external_id in [False, '']:
                raise UserError(_("The product has not been synchronized yet. Please sync it first."))

            if product.standard_price <= 0:
                raise UserError(_("The cost must be greater than 0."))

    def action_sync_cost(self):
        self._can_update_product_cost()
        if self:
            self[0].company_id.with_context(product_id=self.ids)._sync_variants_cost(0, 50)
        else:
            _logger.info((_("No products were selected to update the cost.")))

    def action_migrate_images(self):
        """Migrate main/variant images to solt.product.image records."""

        if not self.env.user.has_group('solt_tiendanube.group_migrate_image'):
            raise UserError(_("You do not have permission for this operation."
                              "Please ask someone with the 'Migrate images' role."))
        products_with_images = self.env['product.template']
        for product in self:
            product = product.with_company(self.env.company)
            if product.image_1920:
                products_with_images |= product

        if not products_with_images:
            raise UserError(_('The selected products do not contain images.'))

        SoltProductImage = self.env['solt.product.image']
        migrated = 0

        for product in products_with_images:
            existing = SoltProductImage.search([('product_tmpl_id', '=', product.id)], limit=1)
            if existing:
                continue

            # Create the main image
            SoltProductImage.with_context(skip_solt_image_create=True).create({
                'name': product.display_name,
                'sequence': 1,
                'image_1920': product.image_1920,
                'product_tmpl_id': product.id,
            })
            # Migrate variant images
            sequence = 2
            if product.product_variant_count > 1:
                for variant in product.product_variant_ids:
                    if (variant.image_variant_1920 and
                            variant.image_variant_1920 != product.image_1920):
                        SoltProductImage.create({
                            'name': f"{product.display_name} - {variant.display_name}",
                            'sequence': sequence,
                            'image_1920': variant.image_variant_1920,
                            'product_tmpl_id': product.id,
                            'product_variant_ids': [(6, 0, [variant.id])],
                        })
                        sequence += 1
            migrated += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Migration completed'),
                'message': _('{} product images were migrated.').format(migrated),
                'type': 'success',
            }
        }
