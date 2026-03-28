# -*- coding: utf-8 -*-
# from odoo import http


# class CrmCampaign(http.Controller):
#     @http.route('/crm_campaign/crm_campaign', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/crm_campaign/crm_campaign/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('crm_campaign.listing', {
#             'root': '/crm_campaign/crm_campaign',
#             'objects': http.request.env['crm_campaign.crm_campaign'].search([]),
#         })

#     @http.route('/crm_campaign/crm_campaign/objects/<model("crm_campaign.crm_campaign"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('crm_campaign.object', {
#             'object': obj
#         })

