# -*- coding: utf-8 -*-

import base64
import logging
import re

import requests

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import config
from odoo.tools import image
from odoo.tools.mimetypes import guess_mimetype
from odoo.tools.image import is_image_size_above

from odoo.addons.base_import.models.base_import import (
    DEFAULT_IMAGE_CHUNK_SIZE,
    DEFAULT_IMAGE_MAXBYTES,
    DEFAULT_IMAGE_REGEX,
    DEFAULT_IMAGE_TIMEOUT,
)

_logger = logging.getLogger(__name__)


class ProductImage(models.Model):
    _name = 'solt.product.image'
    _inherit = 'image.mixin'
    _description = 'Product Image'
    _order = 'sequence, id'

    name = fields.Char('Name', required=True,)
    sequence = fields.Integer(default=10, index=True,)
    image_1920 = fields.Image(required=True)
    product_tmpl_id = fields.Many2one(
        comodel_name='product.template',
        string='Product Template',
        index=True,
        ondelete='cascade',
    )
    image_url = fields.Char('Image URL', help='Remote image URL.', store=False)
    can_image_1024_be_zoomed = fields.Boolean("Can Image 1024 be zoomed", compute='_compute_can_image_1024_be_zoomed',
                                              store=True)
    product_variant_ids = fields.Many2many(
        comodel_name="product.product",
        string="Visible in these variants",
        domain="[('product_tmpl_id', '=', product_tmpl_id)]",
        help="If left empty, all variants will show this image. "
             "When selecting one or more available variants, you can "
             "restrict the availability of the image to those variants.",
    )
    product_variant_count = fields.Integer(compute="_compute_product_variant_count")
    has_product_tmpl_variant = fields.Boolean(compute="_compute_has_product_tmpl_variant")

    @api.depends("product_variant_ids")
    def _compute_product_variant_count(self):
        for image in self:
            image.product_variant_count = len(image.product_variant_ids)

    @api.depends('image_1920', 'image_1024')
    def _compute_can_image_1024_be_zoomed(self):
        for image in self:
            image.can_image_1024_be_zoomed = image.image_1920 and is_image_size_above(image.image_1920,
                                                                                            image.image_1024)

    @api.depends('product_tmpl_id')
    def _compute_has_product_tmpl_variant(self):
        for image in self:
            image.has_product_tmpl_variant = True if image.product_tmpl_id.product_variant_count > 1 else False

    @api.onchange("image_url")
    def _onchange_image_url(self):
        if not self.image_url:
            return
        if re.match(DEFAULT_IMAGE_REGEX, self.image_url):
            # Retrieve from remote url
            self.image_1920 = self._get_image_from_url(self.image_url)
        self.image_url = False

    @api.model
    def _get_image_from_url(self, url):
        with requests.Session() as session:
            session.stream = True
            # Same code as base_import._import_image_by_url
            maxsize = int(config.get("import_image_maxbytes", DEFAULT_IMAGE_MAXBYTES))
            try:
                response = session.get(
                    url,
                    timeout=int(
                        config.get("import_image_timeout", DEFAULT_IMAGE_TIMEOUT)
                    ),
                )
                response.raise_for_status()

                # Check size from headers
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > maxsize:
                    raise UserError(
                        _("File size exceeds configured maximum (%s bytes)", maxsize)
                    )

                content = bytearray()
                for chunk in response.iter_content(DEFAULT_IMAGE_CHUNK_SIZE):
                    content += chunk
                    if len(content) > maxsize:
                        raise UserError(
                            _(
                                "File size exceeds configured maximum (%s bytes)",
                                maxsize,
                            )
                        )

                # Detect image type
                content_bytes = bytes(content)
                detected_mimetype = guess_mimetype(content_bytes)
                _logger.info(
                    f"Image downloaded: {url}, detected type: {detected_mimetype}, size: {len(content_bytes)} bytes."
                )
                # Support for webp images
                if detected_mimetype == 'image/webp':
                    return self._process_webp_image(content_bytes)
                elif detected_mimetype.startswith('image/'):
                    return self._process_standard_image(content_bytes)
                else:
                    raise UserError(_("URL does not contain a valid image: %s", url))

                # image = PILImage.open(io.BytesIO(content))
                # w, h = image.size
                # if w * h > 42e6:  # Nokia Lumia 1020 photo resolution
                #     raise UserError(
                #         _(
                #             "Image size excessive, "
                #             "imported images must be smaller than 42 million pixel"
                #         )
                #     )

                # return base64.b64encode(content)
            except requests.RequestException as e:
                _logger.error(f"Error downloading image from {url}: {e}")
                raise UserError(_("Could not download image from URL: %(url)s: %(error)s", url=url, error=str(e)))
            except Exception as e:
                _logger.exception(f"Error processing image from {url}")
                raise UserError(_("Could not process image from URL: %(url)s: %(error)s", url=url, error=str(e)))
            # except Exception as e:
            #     _logger.exception(e)
            #     raise UserError(
            #         _("Could not retrieve URL: %(url)s: %(error)s", url=url, error=e)
            #     ) from e

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'sequence' not in vals or vals.get('sequence') == 10:
                template_id = vals.get('product_tmpl_id')
                if template_id:
                    last_seq = self.search([('product_tmpl_id', '=', template_id)
                    ], order='sequence desc', limit=1).sequence or 10
                    vals['sequence'] = last_seq + 1

        images = super(ProductImage, self).create(vals_list)
        for image in images:
            if image.product_variant_ids:
                variants_to_update = image.product_variant_ids.with_context(skip_product_image_create=True)
                for variant in variants_to_update:
                    variant.write({'image_variant_1920': image.image_1920})
        return images

    def write(self, vals):
        # Get original variant ids before the write operation
        original_variant_mapping = {img.id: img.product_variant_ids.ids for img in self}
        result = super(ProductImage, self).write(vals)

        # Handle variant changes if product_variant_ids was modified
        if 'product_variant_ids' in vals:
            for image in self:
                original_variants = set(original_variant_mapping.get(image.id, []))
                current_variants = set(image.product_variant_ids.ids)

                # Find removed variants (were in original but not in current)
                removed_variants = original_variants - current_variants
                # Find added variants (are in current but were not in original)
                added_variants = current_variants - original_variants

                # 1. If variants were removed, clear their images
                if removed_variants:
                    variants_to_clear = self.env['product.product'].browse(list(removed_variants))
                    for variant in variants_to_clear:
                        variant.write({'image_variant_1920': False})

                # 2. If variants were added, assign this image to them
                if added_variants:
                    variants_to_update = self.env['product.product'].browse(list(added_variants))
                    # Flag to temporarily disable automatic image entry creation
                    variants_to_update = variants_to_update.with_context(skip_product_image_create=True)
                    for variant in variants_to_update:
                        variant.write({'image_variant_1920': image.image_1920})

        return result

    @api.constrains('product_variant_ids', 'product_tmpl_id')
    def _check_variant_uniqueness(self):
        # Validate that a variant isn't repeated in multiple images
        for image in self:
            if image.product_variant_ids:
                # Find other images with the same variants
                duplicate_images = self.search([
                    ('id', '!=', image.id),
                    ('product_tmpl_id', '=', image.product_tmpl_id.id),
                ])

                for other_image in duplicate_images:
                    common_variants = image.product_variant_ids & other_image.product_variant_ids
                    if common_variants:
                        variant_names = ", ".join(common_variants.mapped('display_name'))
                        raise ValidationError(_(
                            f"The following variants are already configured in another image: {variant_names}"
                        ))

    @api.model
    def cleanup_deleted_variants(self, variant_ids):
        """Call this method when variants are deleted"""
        images = self.search([('product_variant_ids', 'in', variant_ids)])
        for image in images:
            # Remove deleted variants
            remaining_variants = image.product_variant_ids.filtered(lambda v: v.id not in variant_ids)
            image.product_variant_ids = remaining_variants

    def unlink(self):
        """Override unlink to handle associated variants and main image updates"""
        for image in self:
            template = image.product_tmpl_id
            associated_variants = image.product_variant_ids
            was_main_image = False

            # Check if this is the main image (lowest sequence)
            if template and image.sequence == min(template.product_image_ids.mapped('sequence')):
                was_main_image = True

            result = super(ProductImage, self).unlink()

            # Clean up associated variants
            if associated_variants:
                associated_variants.with_context(skip_product_image_create=True).write({
                    'image_variant_1920': False
                })

            # Update main image if needed
            if was_main_image and template:
                # Find new image with lowest sequence to be the main image
                new_main_image = template.product_image_ids.sorted('sequence')[:1]
                if new_main_image:
                    # Update template image with the new main image
                    template.with_context(skip_solt_image_create=True).write({
                        'image_1920': new_main_image.image_1920
                    })
                else:
                    # No images left, clear the main image
                    template.with_context(skip_solt_image_create=True).write({
                        'image_1920': False
                    })

            return result

    @api.model
    def _get_image_extension(self):
        """Get image extension"""
        ext = ''
        if self.image_1920:
            content = base64.b64decode(self.image_1920)
            mimetype = guess_mimetype(content, '')
            if content and mimetype.startswith('image/'):
                ext = mimetype.split('image/')[-1]
        return ext

    @api.model
    def _get_filename_image(self):
        """Create image filename"""
        filename = ""
        if self.image_1920:
            filename = self.name
            ext = self._get_image_extension()
            filename = f"{filename}.{ext or 'jpg'}"
        return filename

    def _process_webp_image(self, content_bytes):
        """
        Process WebP images.
        Odoo handles WebP in a special way to avoid compatibility issues.
        """
        try:
            # Check that it is really WebP (like in ImageProcess)
            if not (content_bytes[0:4] == b'RIFF' and content_bytes[8:15] == b'WEBPVP8'):
                raise UserError(_("Invalid WebP format"))

            # Get dimensions
            try:
                width, height = image.get_webp_size(content_bytes)
                _logger.info(f"WebP dimensions: {width}x{height}")

                # Check maximum resolution (like in ImageProcess)
                if width * height > image.IMAGE_MAX_RESOLUTION:
                    raise UserError(
                        _("Image size excessive (above %sMpx), reduce the image size.",
                          str(image.IMAGE_MAX_RESOLUTION / 1e6))
                    )

            except Exception as size_error:
                _logger.warning(f"Could not get WebP size: {size_error}")

            # For WebP, Odoo recommends not processing it with PIL
            # Return content directly in base64
            return base64.b64encode(content_bytes)

        except Exception as e:
            _logger.error(f"Error processing WebP: {e}")
            raise UserError(_(f"Error processing WebP: {e}"))

    def _process_standard_image(self, content_bytes):
        """
        Process standard images (JPEG, PNG, GIF, etc.)
        """
        try:
            processed_image = image.image_process(
                content_bytes,
                verify_resolution=True,  # Check maximum resolution
                quality=90,  # JPEG quality
                output_format='JPEG'  # Convert to JPEG for consistency
            )

            if processed_image:
                return base64.b64encode(processed_image)
            else:
                # If image_process returns False, use original content
                return base64.b64encode(content_bytes)

        except Exception as e:
            _logger.error(f"Error processing standard image: {e}")
            raise UserError(_(f"Error processing image: {e}"))

