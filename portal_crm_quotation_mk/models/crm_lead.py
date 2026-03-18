# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    def action_set_won_portal(self):
        """Mark opportunity as won from portal"""
        self.ensure_one()
        if self.type != 'opportunity':
            raise UserError(_('Only opportunities can be marked as won.'))
        # Set probability to 100 and mark as won
        self.write({
            'probability': 100,
            'active': True,
        })
        # Try to call the standard method if it exists
        if hasattr(self, 'action_set_won_rainbowman'):
            return self.action_set_won_rainbowman()
        return True

    def action_set_lost(self, **kwargs):
        """Mark opportunity as lost"""
        self.ensure_one()
        if self.type != 'opportunity':
            raise UserError(_('Only opportunities can be marked as lost.'))
        return super().action_set_lost(**kwargs)

    def create_quotation_from_portal(self):
        """Create a sale order from this lead/opportunity"""
        self.ensure_one()
        
        # Try to get or create partner if not set
        partner = self.partner_id
        if not partner:
            # Create partner from lead information
            partner_vals = {}
            if self.partner_name:
                partner_vals['name'] = self.partner_name
            if self.contact_name:
                partner_vals['name'] = self.contact_name
            if self.email_from:
                partner_vals['email'] = self.email_from
            if self.phone:
                partner_vals['phone'] = self.phone
            if self.mobile:
                partner_vals['mobile'] = self.mobile
            
            if partner_vals.get('name'):
                partner = self.env['res.partner'].sudo().create(partner_vals)
                self.write({'partner_id': partner.id})
            else:
                raise UserError(_('Please set a customer name or company name on the lead/opportunity before creating a quotation.'))
        
        # Create sale order with sudo to ensure portal user can create
        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': partner.id,
            'opportunity_id': self.id if self.type == 'opportunity' else False,
            'origin': self.name,
            'user_id': self.user_id.id or self.env.user.id,
            'team_id': self.team_id.id or False,
        })
        
        return {
            'success': True,
            'id': sale_order.id,
            'name': sale_order.name,
        }

    def change_stage_from_portal(self, stage_id):
        """Change stage from portal"""
        self.ensure_one()
        stage = self.env['crm.stage'].sudo().browse(stage_id)
        if not stage.exists():
            raise UserError(_('Stage not found.'))
        
        # Check if stage is valid for this team
        if stage.team_id and stage.team_id != self.team_id:
            raise UserError(_('This stage is not available for this opportunity.'))
        
        self.stage_id = stage_id
        return {
            'success': True,
            'stage_name': stage.name,
        }

    def schedule_activity_from_portal(self, activity_type_id, summary, date_deadline, note=False):
        """Schedule an activity from portal"""
        self.ensure_one()
        
        # Ensure activity_type_id is an integer
        if not activity_type_id:
            raise UserError(_('Activity type is required.'))
        
        try:
            activity_type_id = int(activity_type_id)
        except (ValueError, TypeError):
            raise UserError(_('Invalid activity type ID.'))
        
        # Check if activity type exists and is accessible
        activity_type = self.env['mail.activity.type'].sudo().browse(activity_type_id)
        if not activity_type.exists():
            raise UserError(_('Activity type not found.'))
        
        # Create activity with sudo to ensure portal user can create
        activity = self.sudo().activity_schedule(
            activity_type_id=activity_type_id,
            summary=summary or '',
            date_deadline=date_deadline,
            note=note or '',
        )
        
        return {
            'success': True,
            'activity_id': activity.id,
        }

    def log_note_from_portal(self, note):
        """Log an internal note from portal"""
        self.ensure_one()
        if not note or not note.strip():
            raise UserError(_('Note cannot be empty.'))
        
        # Post message with sudo to ensure portal user can post
        self.sudo().message_post(
            body=note,
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        
        return {
            'success': True,
        }

    def get_portal_activities_info(self):
        """Get activities information for portal display"""
        self.ensure_one()
        today = fields.Date.today()
        # Filter activities for current user and that are not done (state != 'done' or date_done is False)
        activities = self.activity_ids.filtered(
            lambda a: a.user_id == self.env.user and a.state != 'done' and not a.date_done
        )
        
        due_activities = activities.filtered(lambda a: a.date_deadline == today)
        overdue_activities = activities.filtered(lambda a: a.date_deadline < today)
        upcoming_activities = activities.filtered(lambda a: a.date_deadline > today)
        
        return {
            'total': len(activities),
            'due': len(due_activities),
            'overdue': len(overdue_activities),
            'upcoming': len(upcoming_activities),
            'activities': [{
                'id': act.id,
                'summary': act.summary or '',
                'date_deadline': act.date_deadline.strftime('%Y-%m-%d') if act.date_deadline else False,
                'activity_type_id': act.activity_type_id.name if act.activity_type_id else '',
                'is_overdue': act.date_deadline < today if act.date_deadline else False,
                'is_due': act.date_deadline == today if act.date_deadline else False,
            } for act in activities[:10]],
        }
