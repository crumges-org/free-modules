# Portal CRM to Quotation Module - Odoo 17

## Overview
This module allows employees to manage CRM Leads/Opportunities and create Sales Quotations directly from the Portal interface, reducing the need for full Odoo users.

## Key Features

### 1. **CRM Lead/Opportunity Management**
   - **Create Lead**: Portal users can create new leads through a popup form
   - **List View**: Display all leads/opportunities with:
     - Activities indicator (Green = Due, Red = Overdue)
     - Create Lead button
     - Pagination and filtering
   - **Edit/Update**: Portal users can edit lead details
   - **Delete**: Ability to delete leads (with proper access rights)

### 2. **Lead/Opportunity Detail View**
   - **Clickable Status Bar**: Dynamic stage progression with clickable stages
   - **Win/Lost Buttons**: Quick actions to mark opportunities as won or lost
   - **Edit Mode**: Toggle between view and edit modes
   - **New Quotation Button**: Create quotation directly from lead/opportunity
   - **Related Quotations**: Smart button showing count and linking to related quotations
   - **Activities Display**: View scheduled activities in the list

### 3. **Activity Management**
   - **Schedule Activity**: Popup form to schedule activities
   - **Log Note**: Internal note logging functionality
   - **Activity View**: Visual indicators for due/overdue activities

### 4. **Quotation Management**
   - **Create Quotation**: Create new quotation from lead/opportunity with pre-filled data
   - **View Quotations**: List and view related quotations
   - **Edit Quotation**: Add, edit, and delete quotation lines
   - **Send by Email**: Send quotation via email using configured templates
   - **Email Logs**: View sent emails in chatter

## Technical Architecture

### Module Structure
```
portal_crm_quotation_mk/
├── __manifest__.py
├── __init__.py
├── controllers/
│   ├── __init__.py
│   └── portal.py          # Portal routes and controllers
├── models/
│   ├── __init__.py
│   ├── crm_lead.py        # CRM Lead model extensions
│   └── sale_order.py     # Sale Order model extensions
├── views/
│   ├── portal_templates.xml    # Portal templates
│   └── crm_lead_views.xml      # CRM views (if needed)
├── security/
│   └── ir.model.access.csv     # Access rights
└── static/
    └── src/
        └── css/          # Custom CSS (if needed)
```

### Dependencies
- `crm` - CRM module
- `sale_management` - Sales module
- `portal` - Portal base module
- `mail` - Mail and activities
- `calendar` - Calendar/activities
- `contacts` - Contacts
- `account` - Invoicing (for quotations)

### Key Routes to Implement

#### CRM Routes
- `/my/leads` - List all leads
- `/my/leads/<int:lead_id>` - View/Edit lead
- `/my/opportunities` - List all opportunities
- `/my/opportunities/<int:opp_id>` - View/Edit opportunity
- `/my/leads/create` - Create new lead (JSON route)
- `/my/leads/<int:lead_id>/update` - Update lead (JSON route)
- `/my/leads/<int:lead_id>/delete` - Delete lead (JSON route)
- `/my/leads/<int:lead_id>/win` - Mark as won (JSON route)
- `/my/leads/<int:lead_id>/lost` - Mark as lost (JSON route)
- `/my/leads/<int:lead_id>/change_stage` - Change stage (JSON route)
- `/my/leads/<int:lead_id>/schedule_activity` - Schedule activity (JSON route)
- `/my/leads/<int:lead_id>/log_note` - Log note (JSON route)

#### Quotation Routes
- `/my/leads/<int:lead_id>/create_quotation` - Create quotation from lead (JSON route)
- `/my/quotations/<int:order_id>` - View/Edit quotation
- `/my/quotations/<int:order_id>/update_line` - Update quotation line (JSON route)
- `/my/quotations/<int:order_id>/add_line` - Add quotation line (JSON route)
- `/my/quotations/<int:order_id>/delete_line` - Delete quotation line (JSON route)
- `/my/quotations/<int:order_id>/send_email` - Send quotation by email (JSON route)

### Model Extensions

#### CRM Lead Extensions
- Add portal access methods
- Add quotation creation method
- Add activity scheduling methods
- Add stage change methods
- Add win/lost methods

#### Sale Order Extensions
- Add portal editing methods
- Add line management methods
- Add email sending methods

### Security Considerations
- Portal users should only see leads/opportunities assigned to them
- Proper access rights for create/update/delete operations
- Use `sudo()` carefully with proper access checks
- Validate all input data
- Check user permissions before allowing operations

### UI/UX Features
- Responsive design matching Odoo portal theme
- Modal popups for create/edit forms
- AJAX operations for seamless updates
- Activity indicators (color-coded)
- Clickable stage bars
- Smart buttons for related records
- Chatter integration for notes and emails

## Implementation Notes

### Based on Existing Odoo Modules
- Reference `website_crm_partner_assign` for CRM portal implementation
- Reference `sale` module for quotation portal views
- Use `portal.CustomerPortal` as base controller class
- Follow Odoo portal template structure

### Key Implementation Points
1. **Access Control**: Ensure portal users can only access their assigned records
2. **Stage Management**: Dynamic stage bar based on team configuration
3. **Activity Integration**: Use `mail.activity.mixin` functionality
4. **Quotation Creation**: Pre-fill quotation with lead/opportunity data
5. **Email Templates**: Use Odoo's email template system
6. **Form Validation**: Client and server-side validation
7. **Error Handling**: Proper error messages and user feedback

## Testing Checklist
- [ ] Create lead from portal
- [ ] Edit lead from portal
- [ ] Delete lead from portal
- [ ] Change stage via clickable bar
- [ ] Mark opportunity as won
- [ ] Mark opportunity as lost
- [ ] Schedule activity
- [ ] Log note
- [ ] Create quotation from lead
- [ ] View related quotations
- [ ] Edit quotation lines
- [ ] Send quotation by email
- [ ] Access rights validation
- [ ] Activity indicators display correctly

## Installation

1. Copy the module to your Odoo custom addons directory
2. Update the apps list: `Settings > Apps > Update Apps List`
3. Search for "Portal CRM to Quotation" and install it
4. Grant portal access to users who need CRM access
5. Access the dashboard at `/my/crm/dashboard`

## Configuration

1. **Portal Users**: Users must have portal access enabled
2. **Access Rights**: Portal users automatically get access to their own leads/opportunities
3. **Sales Team**: Configure sales teams and stages in CRM settings
4. **Email Templates**: Configure email templates for quotation sending

## Usage

### Dashboard
- Navigate to `/my/crm/dashboard` to see the CRM dashboard
- View statistics, recent leads, and quick actions
- Create new leads directly from the dashboard

### Managing Leads
- View all leads at `/my/leads`
- Click on a lead to view/edit details
- Use the "Create Lead" button to add new leads
- Edit mode allows updating lead information

### Managing Opportunities
- View all opportunities at `/my/opportunities`
- Click on an opportunity to view details
- Use the clickable stage bar to change stages
- Mark opportunities as Won or Lost
- Create quotations directly from opportunities

### Activities
- Schedule activities using the "Schedule Activity" button
- Log internal notes using the "Log Note" button
- View activity indicators in list views (green = due, red = overdue)

### Quotations
- Create quotations from leads/opportunities
- View related quotations with smart buttons
- Edit quotation lines (add, update, delete)
- Send quotations by email

## Technical Details

### Routes
- `/my/crm/dashboard` - CRM Dashboard
- `/my/leads` - Leads list
- `/my/leads/<id>` - Lead detail
- `/my/opportunities` - Opportunities list
- `/my/opportunities/<id>` - Opportunity detail

### JSON Routes (AJAX)
- `/my/lead/create` - Create lead
- `/my/lead/<id>/update` - Update lead
- `/my/lead/<id>/delete` - Delete lead
- `/my/lead/<id>/win` - Mark as won
- `/my/lead/<id>/lost` - Mark as lost
- `/my/lead/<id>/change_stage` - Change stage
- `/my/lead/<id>/create_quotation` - Create quotation
- `/my/lead/<id>/schedule_activity` - Schedule activity
- `/my/lead/<id>/log_note` - Log note
- `/my/quotation/<id>/add_line` - Add quotation line
- `/my/quotation/<id>/update_line` - Update quotation line
- `/my/quotation/<id>/delete_line` - Delete quotation line
- `/my/quotation/<id>/send_email` - Send quotation email

## Future Enhancements
- Bulk operations
- Advanced filtering and search
- Export functionality
- Mobile optimization
- Advanced dashboard analytics
- Integration with other modules
- Activity calendar view
- Email template customization from portal
