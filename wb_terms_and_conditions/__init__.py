# -- coding: utf-8 --
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) Wan Buffer Services (<https://wanbuffer.com/>).
#
#    For Module Support : support@wanbuffer.com  or Call : +91 9638442270
#
##############################################################################
from . import models


def post_init_hook_sale(env):
    partner = env['res.partner'].create({
        'name': 'Test Partner (Auto)',
    })

    tnc = env['wb.terms.condition'].create({
        'name': 'Auto T&C Sale',
        'term_type': 'sale',
        'tnc_con': '<p>Auto-generated terms and conditions</p>',
        'company_ids': [(6, 0, [env.ref('base.main_company').id])]
    })

    env['sale.order'].create({
        'partner_id': partner.id,
        'terms_and_conditions_id': tnc.id,
    })

