# coding: utf-8
import logging
from odoo import tools

_logger = logging.getLogger(__name__)

def post_init_hook(env):
    """Apply custom LATAM address format after installation."""
    try:
        custom_view = env.ref("solt_l10n_mx_partner_address.mx_partner_address_form")
    except ValueError:
        custom_view = False
        _logger.info("View 'solt_l10n_mx_partner_address.mx_partner_address_form' not found")

    address_format = (
        "%(street_name)s %(street_number)s %(street_number2)s\n"
        "%(l10n_mx_colony)s\n"
        "%(zip)s %(city)s, %(state_name)s\n"
        "%(country_name)s"
    )

    countries = ["base.ar", "base.cl", "base.co"]

    for country_xmlid in countries:
        try:
            country = env.ref(country_xmlid)
            vals = {"address_format": address_format}
            if custom_view:
                vals["address_view_id"] = custom_view.id
            country.write(vals)
            _logger.info(f"Custom address format applied to {country.name} ({country.code})")
        except ValueError:
            _logger.warning(f"Country not found with XMLID {country_xmlid}")
