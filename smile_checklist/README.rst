.. |badge1| image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :alt: License: AGPL-3

.. |badge2| image:: https://img.shields.io/badge/github-Smile--SA%2Fodoo_addons-lightgray.png?logo=github
    :target: https://github.com/Smile-SA/odoo_addons/tree/18.0/smile_checklist
    :alt: Smile-SA/odoo_addons

|badge1| |badge2|

==================
Smile Checklist
==================

This module allows adding checklists to forms to track their filling progress and add actions to be triggered once their checklist is fully completed.

A checklist applies to a single object and is composed of:

- Tasks
  - List of fields to fill or boolean expressions to respect
  - Server Action executed if the task is completed
- Views on which the checklist is visible
- Server Action executed if the checklist is completed
  - all action types: email, sms, object creation/update, etc

.. contents:: Table of contents
   :local:

Usage
=====

In our example, we will create a checklist to check if the contact's address is completed. Once completed, a server action will send an email automatically to the manager.

1. Go to the new menu **Settings > Technical > Checklists** and create a new checklist:

   .. image:: static/description/creation.png
      :alt: create a new checklist
      :width: 850px

2. Select the action that will execute when the checklist is completed:

   .. image:: static/description/action_server.png
      :alt: create an action server
      :width: 850px

3. To create a task, write the field name of the object:

   .. image:: static/description/field_object.png
      :alt: Fill expression
      :width: 850px

4. Write the domain to check when the task is completed:

   .. image:: static/description/complete_if_domain.png
      :alt: Complete if domain
      :width: 850px

5. Choose the views and menus where the checklist appears:

   .. image:: static/description/full_visibility.png
      :alt: Add visibility in menus and views
      :width: 850px

6. See the checklist in the specified form view:

   .. image:: static/description/contact_form.png
      :alt: contact form
      :width: 850px

7. Click on the smart button to see a wizard containing the checklist fields:

   .. image:: static/description/click_smart_button.png
      :alt: Checklist fields
      :width: 850px

8. Once the checklist is completed, the server sends the email:

   .. image:: static/description/email_received.png
      :alt: receiving email
      :width: 850px

9. See the checklist in the list view added in visibility options:

   .. image:: static/description/contacts_list.png
      :alt: contact list
      :width: 850px

Known issues
============

Need to restart the server to display the checklist on model's views after creation.

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/Smile-SA/odoo_addons/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smash it by providing detailed and welcomed feedback
`here <https://github.com/Smile-SA/odoo_addons/issues/new?body=module:%20smile_checklist%0Aversion:%2018.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`_.

Do not contact contributors directly about support or help with technical issues.

Credits
=======

Contributors
-----------

Corentin Pouhet-Brunerie

Maintainer
---------

This module is maintained by Smile SA.

Since 1991 Smile has been a pioneer of technology and also the European expert in open source solutions.