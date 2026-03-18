# Portal Navigation Guide

## How CRM Appears in Portal

### 1. **Portal Home Page** (`/my/home`)

When a portal user logs in and visits `/my/home`, they will see:

#### **CRM Section Cards:**
- **CRM Dashboard** - Main dashboard with statistics
  - Icon: Connection icon
  - Text: "Manage your leads, opportunities, and quotations"
  - Link: `/my/crm/dashboard`

- **My Leads** - Leads list
  - Icon: Connection icon  
  - Text: "View and manage your leads"
  - Badge: Shows count of leads
  - Link: `/my/leads`

- **My Opportunities** - Opportunities list
  - Icon: Connection icon
  - Text: "Track your sales opportunities"
  - Badge: Shows count of opportunities
  - Link: `/my/opportunities`

These cards appear in the **"Services"** category section on the portal home page.

### 2. **CRM Dashboard** (`/my/crm/dashboard`)

A comprehensive dashboard showing:

#### **Statistics Cards (Top Row):**
- **Total Leads** - Count with "This Month" indicator
- **Opportunities** - Count with "This Month" indicator
- **Quotations** - Count with "This Month" indicator
- **Expected Revenue** - Total pipeline value

#### **Status Cards (Second Row):**
- **Active** - Active opportunities count
- **Won** - Won opportunities count
- **Lost** - Lost opportunities count

#### **Activity Alert:**
- Shows overdue activities (red badge)
- Shows due today activities (yellow badge)
- Total activities count

#### **Quick Actions Section:**
- Dashboard button
- My Leads button
- My Opportunities button
- Create Lead button (opens modal)

#### **Recent Activity:**
- **Recent Leads/Opportunities** - Last 5 items
- **Recent Quotations** - Last 5 items

### 3. **Leads List** (`/my/leads`)

A table showing all leads with:
- Lead Name (clickable)
- Contact Name
- Company Name
- Email
- Phone
- **Activity Indicators:**
  - Red badge = Overdue activities
  - Yellow badge = Due today activities
- Created Date
- View button

**Top Actions:**
- "Create Lead" button (opens modal popup)

### 4. **Lead Detail** (`/my/lead/<id>`)

Shows full lead information:

#### **Main Section:**
- Lead details form (editable in edit mode)
- Fields: Name, Contact, Company, Email, Phone, Description
- Edit/Save buttons

#### **Activities Section:**
- "Schedule Activity" button (opens modal)
- "Log Note" button (opens modal)
- Activities list

#### **Quick Actions Sidebar:**
- "Create Quotation" button
- "View Quotations" link

### 5. **Opportunities List** (`/my/opportunities`)

Similar to leads list but with additional columns:
- Stage (color-coded badge)
- Expected Revenue
- Probability (progress bar)
- Activity indicators

**Filters:**
- All / Active / Won / Lost
- Today Activities / This Week / Overdue

### 6. **Opportunity Detail** (`/my/opportunity/<id>`)

#### **Stage Bar (Top):**
- Clickable stage progression bar
- Visual dots showing current stage
- Click any stage to change it

#### **Main Section:**
- Opportunity details
- **Win** button (green)
- **Lost** button (red)
- **Edit** button

#### **Quotations Section:**
- "New Quotation" button
- Table of related quotations
- View quotation links

#### **Activities Sidebar:**
- Schedule Activity
- Log Note

### 7. **Navigation Flow:**

```
Portal Home (/my/home)
    ├── CRM Dashboard (/my/crm/dashboard)
    │   ├── My Leads (/my/leads)
    │   │   └── Lead Detail (/my/lead/<id>)
    │   │       ├── Edit Lead
    │   │       ├── Schedule Activity
    │   │       ├── Log Note
    │   │       └── Create Quotation
    │   └── My Opportunities (/my/opportunities)
    │       └── Opportunity Detail (/my/opportunity/<id>)
    │           ├── Change Stage (clickable bar)
    │           ├── Win/Lost buttons
    │           ├── Edit Opportunity
    │           ├── Schedule Activity
    │           ├── Log Note
    │           └── Create/View Quotations
    └── Quotations (from sale module)
        └── Quotation Detail
            ├── Add/Edit/Delete Lines
            └── Send by Email
```

### 8. **Visual Features:**

#### **Color Coding:**
- **Green badges** = Due activities
- **Red badges** = Overdue activities
- **Blue badges** = Active/Info status
- **Stage colors** = Based on stage configuration

#### **Interactive Elements:**
- **Hover effects** on cards and buttons
- **Modal popups** for forms
- **AJAX operations** for seamless updates
- **Progress bars** for probability
- **Clickable stage bar** for quick stage changes

#### **Responsive Design:**
- Works on desktop, tablet, and mobile
- Cards stack on smaller screens
- Touch-friendly buttons

### 9. **Access Points:**

Users can access CRM features from:
1. **Portal Home** - Click on CRM cards
2. **Direct URLs** - Type URLs directly
3. **Breadcrumbs** - Navigate back through breadcrumb links
4. **Quick Actions** - Buttons throughout the interface

### 10. **User Experience:**

- **Clean, modern interface** with card-based design
- **Intuitive navigation** with clear labels
- **Visual feedback** for all actions
- **Loading indicators** during operations
- **Success/Error messages** for user feedback
- **Consistent styling** matching Odoo portal theme
