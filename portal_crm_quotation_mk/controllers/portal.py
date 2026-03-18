# -*- coding: utf-8 -*-

from datetime import datetime, date, timedelta
from collections import OrderedDict
from werkzeug.exceptions import NotFound

from odoo import http, fields, _
from odoo.exceptions import AccessError, ValidationError, UserError
from odoo.http import request
from odoo.addons.portal.controllers import portal
from odoo.addons.portal.controllers.portal import pager as portal_pager

try:
    from odoo.addons.sale.controllers.portal import CustomerPortal as SaleCustomerPortal
except ImportError:
    SaleCustomerPortal = portal.CustomerPortal


class PortalCrmCustomerPortal(SaleCustomerPortal):

    def _prepare_home_portal_values(self, counters):
        """Add CRM counters to portal home"""
        values = super()._prepare_home_portal_values(counters)
        CrmLead = request.env['crm.lead'].sudo()
        user = request.env.user
        
        if 'lead_count' in counters:
            domain = [('user_id', '=', user.id), ('type', '=', 'lead')]
            values['lead_count'] = (
                CrmLead.search_count(domain)
                if CrmLead.check_access_rights('read', raise_exception=False)
                else 0
            )
        
        if 'opportunity_count' in counters:
            domain = [('user_id', '=', user.id), ('type', '=', 'opportunity')]
            values['opportunity_count'] = (
                CrmLead.search_count(domain)
                if CrmLead.check_access_rights('read', raise_exception=False)
                else 0
            )
        
        if 'quotation_count' in counters:
            SaleOrder = request.env['sale.order'].sudo()
            domain = [('user_id', '=', user.id), ('state', 'in', ['draft', 'sent'])]
            values['quotation_count'] = (
                SaleOrder.search_count(domain)
                if SaleOrder.check_access_rights('read', raise_exception=False)
                else 0
            )
        
        return values

    def _get_crm_dashboard_data(self, user):
        """Compute dashboard data for CRM"""
        today = fields.Date.today()
        month_start = today.replace(day=1)
        last_month_start = (month_start - timedelta(days=1)).replace(day=1)
        last_month_end = month_start - timedelta(days=1)
        
        CrmLead = request.env['crm.lead'].sudo()
        SaleOrder = request.env['sale.order'].sudo()
        
        # Domain for user's records
        lead_domain = [('user_id', '=', user.id)]
        opp_domain = [('user_id', '=', user.id), ('type', '=', 'opportunity')]
        quotation_domain = [('user_id', '=', user.id), ('state', 'in', ['draft', 'sent'])]
        
        # Total counts
        total_leads = CrmLead.search_count([('user_id', '=', user.id), ('type', '=', 'lead')])
        total_opportunities = CrmLead.search_count(opp_domain)
        total_quotations = SaleOrder.search_count(quotation_domain)
        
        # Opportunities by stage
        opportunities = CrmLead.search(opp_domain)
        stages_data = {}
        for opp in opportunities:
            stage_name = opp.stage_id.name if opp.stage_id else 'No Stage'
            if stage_name not in stages_data:
                stages_data[stage_name] = 0
            stages_data[stage_name] += 1
        
        # Won/Lost opportunities
        won_opportunities = CrmLead.search_count(opp_domain + [('probability', '=', 100)])
        lost_opportunities = CrmLead.search_count(opp_domain + [('active', '=', False), ('probability', '=', 0)])
        active_opportunities = total_opportunities - won_opportunities - lost_opportunities
        
        # Expected revenue
        total_expected_revenue = sum(opportunities.mapped('expected_revenue'))
        
        # Recent activities (filter out done activities using state != 'done' and date_done is False)
        activities = request.env['mail.activity'].sudo().search([
            ('res_model', '=', 'crm.lead'),
            ('user_id', '=', user.id),
            ('state', '!=', 'done'),
        ], order='date_deadline asc', limit=10)
        # Further filter by date_done to exclude completed activities
        activities = activities.filtered(lambda a: not a.date_done)
        
        due_activities = activities.filtered(lambda a: a.date_deadline == today)
        overdue_activities = activities.filtered(lambda a: a.date_deadline < today)
        
        # Recent leads/opportunities
        recent_leads = CrmLead.search(
            [('user_id', '=', user.id)],
            order='create_date desc',
            limit=5
        )
        
        # Recent quotations
        recent_quotations = SaleOrder.search(
            quotation_domain,
            order='create_date desc',
            limit=5
        )
        
        # Monthly statistics
        this_month_leads = CrmLead.search_count([
            ('user_id', '=', user.id),
            ('type', '=', 'lead'),
            ('create_date', '>=', month_start),
        ])
        this_month_opportunities = CrmLead.search_count([
            ('user_id', '=', user.id),
            ('type', '=', 'opportunity'),
            ('create_date', '>=', month_start),
        ])
        this_month_quotations = SaleOrder.search_count([
            ('user_id', '=', user.id),
            ('state', 'in', ['draft', 'sent']),
            ('create_date', '>=', month_start),
        ])
        
        return {
            'total_leads': total_leads,
            'total_opportunities': total_opportunities,
            'total_quotations': total_quotations,
            'won_opportunities': won_opportunities,
            'lost_opportunities': lost_opportunities,
            'active_opportunities': active_opportunities,
            'total_expected_revenue': total_expected_revenue,
            'stages_data': stages_data,
            'due_activities': len(due_activities),
            'overdue_activities': len(overdue_activities),
            'total_activities': len(activities),
            'recent_leads': recent_leads,
            'recent_quotations': recent_quotations,
            'this_month_leads': this_month_leads,
            'this_month_opportunities': this_month_opportunities,
            'this_month_quotations': this_month_quotations,
        }

    @http.route(['/my/crm/dashboard'], type='http', auth="user", website=True)
    def portal_crm_dashboard(self, **kw):
        """CRM Dashboard"""
        values = self._prepare_portal_layout_values()
        user = request.env.user
        
        dashboard_data = self._get_crm_dashboard_data(user)
        values.update(dashboard_data)
        values.update({
            'page_name': 'crm_dashboard',
        })
        
        return request.render("portal_crm_quotation_mk.portal_crm_dashboard", values)

    @http.route(['/my/leads', '/my/leads/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_leads(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        """List all leads"""
        values = self._prepare_portal_layout_values()
        CrmLead = request.env['crm.lead'].sudo()
        user = request.env.user
        
        domain = [('user_id', '=', user.id), ('type', '=', 'lead')]
        
        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
            'contact_name': {'label': _('Contact Name'), 'order': 'contact_name'},
            'stage': {'label': _('Stage'), 'order': 'stage_id'},
        }
        
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']
        
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]
        
        lead_count = CrmLead.search_count(domain)
        pager = portal_pager(
            url="/my/leads",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=lead_count,
            page=page,
            step=self._items_per_page
        )
        
        leads = CrmLead.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        
        # Get activities info for each lead
        leads_activities = {}
        for lead in leads:
            leads_activities[lead.id] = lead.get_portal_activities_info()
        
        values.update({
            'leads': leads,
            'leads_activities': leads_activities,
            'page_name': 'leads',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        
        return request.render("portal_crm_quotation_mk.portal_my_leads", values)

    @http.route(['/my/opportunities', '/my/opportunities/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_opportunities(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        """List all opportunities"""
        values = self._prepare_portal_layout_values()
        CrmLead = request.env['crm.lead'].sudo()
        user = request.env.user
        
        domain = [('user_id', '=', user.id), ('type', '=', 'opportunity')]
        
        today = fields.Date.today()
        this_week_end_date = fields.Date.to_string(fields.Date.from_string(today) + timedelta(days=7))
        
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'active': {'label': _('Active'), 'domain': [('active', '=', True), ('probability', '<', 100)]},
            'won': {'label': _('Won'), 'domain': [('probability', '=', 100)]},
            'lost': {'label': _('Lost'), 'domain': [('active', '=', False), ('probability', '=', 0)]},
            'today': {'label': _('Today Activities'), 'domain': [('activity_date_deadline', '=', today)]},
            'week': {'label': _('This Week Activities'),
                     'domain': [('activity_date_deadline', '>=', today), ('activity_date_deadline', '<=', this_week_end_date)]},
            'overdue': {'label': _('Overdue Activities'), 'domain': [('activity_date_deadline', '<', today)]},
        }
        
        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
            'contact_name': {'label': _('Contact Name'), 'order': 'contact_name'},
            'revenue': {'label': _('Expected Revenue'), 'order': 'expected_revenue desc'},
            'probability': {'label': _('Probability'), 'order': 'probability desc'},
            'stage': {'label': _('Stage'), 'order': 'stage_id'},
        }
        
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']
        
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']
        
        if filterby == 'lost':
            CrmLead = CrmLead.with_context(active_test=False)
        
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]
        
        opp_count = CrmLead.search_count(domain)
        pager = portal_pager(
            url="/my/opportunities",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby},
            total=opp_count,
            page=page,
            step=self._items_per_page
        )
        
        opportunities = CrmLead.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        
        # Get activities info for each opportunity
        opportunities_activities = {}
        for opp in opportunities:
            opportunities_activities[opp.id] = opp.get_portal_activities_info()
        
        values.update({
            'opportunities': opportunities,
            'opportunities_activities': opportunities_activities,
            'page_name': 'opportunities',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
        })
        
        return request.render("portal_crm_quotation_mk.portal_my_opportunities", values)

    @http.route(['/my/lead/<int:lead_id>'], type='http', auth="user", website=True)
    def portal_my_lead(self, lead_id=None, **kw):
        """View/Edit a lead"""
        lead = request.env['crm.lead'].sudo().browse(lead_id)
        if not lead.exists() or lead.user_id != request.env.user or lead.type != 'lead':
            raise NotFound()
        
        values = self._prepare_portal_layout_values()
        # Get messages (notes and activities) for chatter
        messages = request.env['mail.message'].sudo().search([
            ('model', '=', 'crm.lead'),
            ('res_id', '=', lead.id),
            ('message_type', 'in', ['notification', 'email']),
        ], order='date desc', limit=50)
        
        # Get activities
        activities = request.env['mail.activity'].sudo().search([
            ('res_model', '=', 'crm.lead'),
            ('res_id', '=', lead.id),
            ('user_id', '=', request.env.user.id),
        ], order='date_deadline asc')
        
        values.update({
            'lead': lead,
            'page_name': 'lead_detail',
            'stages': request.env['crm.stage'].sudo().search([
                ('team_id', '=', False),
            ], order='sequence'),
            'activity_types': request.env['mail.activity.type'].sudo().search([
                '|', ('res_model', '=', 'crm.lead'), ('res_model', '=', False)
            ]),
            'countries': request.env['res.country'].sudo().search([]),
            'states': request.env['res.country.state'].sudo().search([]),
            'messages': messages,
            'activities': activities,
        })
        
        return request.render("portal_crm_quotation_mk.portal_my_lead", values)

    @http.route(['/my/opportunity/<int:opp_id>'], type='http', auth="user", website=True)
    def portal_my_opportunity(self, opp_id=None, **kw):
        """View/Edit an opportunity"""
        opp = request.env['crm.lead'].sudo().browse(opp_id)
        if not opp.exists() or opp.user_id != request.env.user or opp.type != 'opportunity':
            raise NotFound()
        
        values = self._prepare_portal_layout_values()
        # Get stages - filter by team and order by sequence
        stage_domain = ['|', ('team_id', '=', False), ('team_id', '=', opp.team_id.id)]
        stages = request.env['crm.stage'].sudo().search(stage_domain, order='sequence')
        
        # Get messages (notes and activities) for chatter
        messages = request.env['mail.message'].sudo().search([
            ('model', '=', 'crm.lead'),
            ('res_id', '=', opp.id),
            ('message_type', 'in', ['notification', 'email']),
        ], order='date desc', limit=50)
        
        # Get activities
        activities = request.env['mail.activity'].sudo().search([
            ('res_model', '=', 'crm.lead'),
            ('res_id', '=', opp.id),
            ('user_id', '=', request.env.user.id),
        ], order='date_deadline asc')
        
        values.update({
            'opportunity': opp,
            'page_name': 'opportunity_detail',
            'stages': stages,
            'activity_types': request.env['mail.activity.type'].sudo().search([
                '|', ('res_model', '=', 'crm.lead'), ('res_model', '=', False)
            ]),
            'countries': request.env['res.country'].sudo().search([]),
            'states': request.env['res.country.state'].sudo().search([]),
            'quotations': request.env['sale.order'].sudo().search([
                ('opportunity_id', '=', opp.id)
            ]),
            'messages': messages,
            'activities': activities,
        })
        
        return request.render("portal_crm_quotation_mk.portal_my_opportunity", values)

    # JSON Routes for AJAX operations
    @http.route(['/my/lead/create'], type='json', auth="user", methods=['POST'], website=True)
    def portal_create_lead(self, **post):
        """Create a new lead from portal"""
        try:
            # Remove csrf_token from post data before creating
            post.pop('csrf_token', None)
            lead = request.env['crm.lead'].sudo().create({
                'name': post.get('name'),
                'type': 'lead',
                'contact_name': post.get('contact_name'),
                'partner_name': post.get('partner_name'),
                'email_from': post.get('email_from'),
                'phone': post.get('phone'),
                'description': post.get('description'),
                'user_id': request.env.user.id,
            })
            return {
                'success': True,
                'id': lead.id,
                'name': lead.name,
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }

    @http.route(['/my/lead/<int:lead_id>/update'], type='json', auth="user", methods=['POST'], website=True)
    def portal_update_lead(self, lead_id=None, **post):
        """Update a lead from portal"""
        lead = request.env['crm.lead'].sudo().browse(lead_id)
        if not lead.exists() or lead.user_id != request.env.user:
            return {'success': False, 'error': 'Access Denied'}
        
        try:
            # Remove csrf_token from post data before updating
            post.pop('csrf_token', None)
            lead.write(post)
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route(['/my/lead/<int:lead_id>/delete'], type='json', auth="user", methods=['POST'], website=True)
    def portal_delete_lead(self, lead_id=None, **post):
        """Delete a lead from portal"""
        lead = request.env['crm.lead'].sudo().browse(lead_id)
        if not lead.exists() or lead.user_id != request.env.user:
            return {'success': False, 'error': 'Access Denied'}
        
        try:
            lead.unlink()
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route(['/my/lead/<int:lead_id>/win'], type='json', auth="user", methods=['POST'], website=True)
    def portal_win_opportunity(self, lead_id=None, **post):
        """Mark opportunity as won"""
        opp = request.env['crm.lead'].sudo().browse(lead_id)
        if not opp.exists() or opp.user_id != request.env.user or opp.type != 'opportunity':
            return {'success': False, 'error': 'Invalid opportunity'}
        
        try:
            # Remove csrf_token from post data
            post.pop('csrf_token', None)
            opp.action_set_won_portal()
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route(['/my/lead/<int:lead_id>/lost'], type='json', auth="user", methods=['POST'], website=True)
    def portal_lost_opportunity(self, lead_id=None, **post):
        """Mark opportunity as lost"""
        opp = request.env['crm.lead'].sudo().browse(lead_id)
        if not opp.exists() or opp.user_id != request.env.user or opp.type != 'opportunity':
            return {'success': False, 'error': 'Invalid opportunity'}
        
        try:
            # Remove csrf_token from post data
            post.pop('csrf_token', None)
            opp.action_set_lost()
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route(['/my/lead/<int:lead_id>/restore'], type='json', auth="user", methods=['POST'], website=True)
    def portal_restore_opportunity(self, lead_id=None, **post):
        """Restore a lost opportunity"""
        opp = request.env['crm.lead'].sudo().browse(lead_id)
        if not opp.exists() or opp.user_id != request.env.user or opp.type != 'opportunity':
            return {'success': False, 'error': 'Invalid opportunity'}
        
        try:
            # Remove csrf_token from post data
            post.pop('csrf_token', None)
            opp.write({'active': True, 'probability': 10})
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route(['/my/lead/<int:lead_id>/change_stage'], type='json', auth="user", methods=['POST'], website=True)
    def portal_change_stage(self, lead_id=None, stage_id=None, **post):
        """Change stage of lead/opportunity"""
        lead = request.env['crm.lead'].sudo().browse(lead_id)
        if not lead.exists() or lead.user_id != request.env.user:
            return {'success': False, 'error': 'Access Denied'}
        
        try:
            # Remove csrf_token from post data
            post.pop('csrf_token', None)
            # Get stage_id from post if not in kwargs
            if not stage_id:
                stage_id = post.get('stage_id')
            result = lead.change_stage_from_portal(stage_id)
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route(['/my/lead/<int:lead_id>/create_quotation'], type='json', auth="user", methods=['POST'], website=True)
    def portal_create_quotation(self, lead_id=None, **post):
        """Create quotation from lead/opportunity"""
        lead = request.env['crm.lead'].sudo().browse(lead_id)
        if not lead.exists() or lead.user_id != request.env.user:
            return {'success': False, 'error': 'Access Denied'}
        
        try:
            # Remove csrf_token from post data
            post.pop('csrf_token', None)
            result = lead.create_quotation_from_portal()
            if not result.get('success'):
                result['success'] = True  # Ensure success flag is set
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route(['/my/lead/<int:lead_id>/schedule_activity'], type='json', auth="user", methods=['POST'], website=True)
    def portal_schedule_activity(self, lead_id=None, **post):
        """Schedule an activity"""
        lead = request.env['crm.lead'].sudo().browse(lead_id)
        if not lead.exists() or lead.user_id != request.env.user:
            return {'success': False, 'error': 'Access Denied'}
        
        try:
            # Remove csrf_token from post data
            post.pop('csrf_token', None)
            
            # Convert activity_type_id to integer
            activity_type_id = post.get('activity_type_id')
            if activity_type_id:
                try:
                    activity_type_id = int(activity_type_id)
                except (ValueError, TypeError):
                    return {'success': False, 'error': 'Invalid activity type ID'}
            else:
                return {'success': False, 'error': 'Activity type is required'}
            
            result = lead.schedule_activity_from_portal(
                activity_type_id=activity_type_id,
                summary=post.get('summary'),
                date_deadline=post.get('date_deadline'),
                note=post.get('note', False),
            )
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route(['/my/lead/<int:lead_id>/log_note'], type='json', auth="user", methods=['POST'], website=True)
    def portal_log_note(self, lead_id=None, note=None, **kw):
        """Log an internal note"""
        lead = request.env['crm.lead'].sudo().browse(lead_id)
        if not lead.exists() or lead.user_id != request.env.user:
            return {'success': False, 'error': 'Access Denied'}
        
        try:
            # For JSON routes, parameters come as function arguments
            # The 'note' should be passed directly from the JSON body
            note_value = note
            
            # Fallback: try from kw dict
            if not note_value:
                note_value = kw.get('note')
            
            # Fallback: try from request.jsonrequest (raw JSON body)
            if not note_value and hasattr(request, 'jsonrequest'):
                json_data = request.jsonrequest
                if isinstance(json_data, dict):
                    # For direct JSON body
                    note_value = json_data.get('note')
                    # For JSON-RPC params
                    if not note_value and 'params' in json_data:
                        note_value = json_data['params'].get('note')
            
            if not note_value or not str(note_value).strip():
                return {'success': False, 'error': 'Note cannot be empty.'}
            
            note_value = str(note_value).strip()
            result = lead.log_note_from_portal(note_value)
            return result
        except Exception as e:
            import traceback
            return {'success': False, 'error': str(e)}

    @http.route(['/my/quotation/<int:order_id>/add_line'], type='json', auth="user", methods=['POST'], website=True)
    def portal_add_quotation_line(self, order_id=None, **post):
        """Add line to quotation"""
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists() or order.user_id != request.env.user:
            return {'success': False, 'error': 'Access Denied'}
        
        try:
            result = order.add_line_from_portal(
                product_id=post.get('product_id'),
                quantity=post.get('quantity', 1),
                price_unit=post.get('price_unit', False),
            )
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route(['/my/quotation/<int:order_id>/update_line'], type='json', auth="user", methods=['POST'], website=True)
    def portal_update_quotation_line(self, order_id=None, **post):
        """Update line in quotation"""
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists() or order.user_id != request.env.user:
            return {'success': False, 'error': 'Access Denied'}
        
        try:
            result = order.update_line_from_portal(
                line_id=post.get('line_id'),
                quantity=post.get('quantity', False),
                price_unit=post.get('price_unit', False),
            )
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route(['/my/quotation/<int:order_id>/delete_line'], type='json', auth="user", methods=['POST'], website=True)
    def portal_delete_quotation_line(self, order_id=None, **post):
        """Delete line from quotation"""
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists() or order.user_id != request.env.user:
            return {'success': False, 'error': 'Access Denied'}
        
        try:
            result = order.delete_line_from_portal(post.get('line_id'))
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route(['/my/quotation/<int:order_id>/send_email'], type='json', auth="user", methods=['POST'], website=True)
    def portal_send_quotation_email(self, order_id=None, template_id=None, recipients=None, subject=None, body=None, **post):
        """Send quotation by email with wizard"""
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists() or order.user_id != request.env.user:
            return {'success': False, 'error': 'Access Denied'}
        
        try:
            # Get parameters from JSON-RPC params
            if not template_id:
                template_id = post.get('template_id')
            if not recipients:
                recipients = post.get('recipients')
            if not subject:
                subject = post.get('subject')
            if not body:
                body = post.get('body')
            
            # Parse recipients (comma-separated)
            recipient_list = []
            if recipients:
                recipient_list = [email.strip() for email in str(recipients).split(',') if email.strip()]
            
            if not recipient_list:
                return {'success': False, 'error': 'At least one recipient email is required.'}
            
            # Use template if provided
            template = False
            if template_id:
                template = request.env['mail.template'].sudo().browse(int(template_id))
                if not template.exists():
                    template = False
            
            # Send email
            email_values = {
                'email_to': ','.join(recipient_list),
            }
            if subject:
                email_values['subject'] = subject
            if body:
                email_values['body_html'] = body
            
            if template:
                # Use custom template
                template.sudo().send_mail(
                    order.id,
                    force_send=True,
                    email_values=email_values,
                    email_layout_xmlid='mail.mail_notification_layout_with_responsible_signature'
                )
            else:
                # Use default template or create message
                default_template = request.env.ref('sale.email_template_edi_sale', raise_if_not_found=False)
                if default_template:
                    default_template.sudo().send_mail(
                        order.id,
                        force_send=True,
                        email_values=email_values,
                        email_layout_xmlid='mail.mail_notification_layout_with_responsible_signature'
                    )
                else:
                    # Fallback: post message
                    order.message_post(
                        body=(body or '') + '<br/><br/>' + _('Quotation sent by email from portal'),
                        subject=subject or _('Quotation: %s') % order.name,
                        email_to=','.join(recipient_list),
                    )
            
            return {
                'success': True,
                'message': _('Quotation has been sent by email to %s.') % ', '.join(recipient_list),
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
