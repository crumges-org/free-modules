{
    'name': "Access Rights Audit",
    'summary': "Read-only audit of Odoo access rights: explain why a user can reach a model, and list the grants that expose data without anyone noticing.",
    'description': """
Odoo decides whether someone may touch a record in two layers, and neither is legible from the user form. An access line grants create, read, write or delete on a model to a group. A record rule then decides which records of that model the user actually sees, and the rules do not combine the way most people assume: a rule with no group is a restriction everyone obeys and is combined with AND, while rules attached to groups are permissions combined with OR, so adding one more group can widen what a user sees rather than narrow it. On top of that, group membership is transitive - a user given one group silently receives every group it implies, and those never appear on their user form.

The result is that "why can this person see this?" is a question almost nobody can answer about their own database. This module answers it. Pick a user, a model and an operation, and it reports whether the answer is yes, which access line granted it, which group that line came from and whether the user holds that group directly or through implication, which record rules apply and which belong to groups they do not hold, and how many records of that model they can actually reach. The reachable count is obtained by asking Odoo itself as that user rather than by re-implementing the rule engine, so it cannot drift from what the ORM enforces.

The second half is a scan. It reports access lines with no group, which grant the operation to every logged-in user rather than acting as a placeholder; delete rights on business models that no record rule narrows; multi-company databases where a model with a company field has no rule mentioning the company; ordinary-looking groups that reach Settings access through the implied-groups chain; who really holds Settings access once implication is counted; and record rules that have been switched off, which is easy to miss because an inactive rule does not appear in the default list. Every finding links to the exact access line, rule or group that produced it.

This module only reads. It creates no groups, changes no rules and grants nothing, so it is safe to install on a production database to find out what is actually configured.

Key features:
  * Explain access for any user, model and operation, in plain sentences
  * Groups shown split into those on the user form and those received through implication
  * The granting access lines and the applicable record rules, listed with the rules that belong to groups the user does not hold
  * Reachable record count obtained from Odoo as that user, not from a second rule engine that could disagree
  * Scan for access lines with no group that grant write, create or delete to everyone
  * Scan for delete rights on business models with no record rule to narrow them
  * Scan for missing company rules in a multi-company database
  * Scan for groups that imply Settings access, and for who holds it once implication is counted
  * Scan for inactive record rules - restrictions that no longer restrict
  * Every finding links back to the access line, rule or group behind it
  * Strictly read-only: nothing in this module writes to a security record
""",
    'version': '18.0.1.0.0',
    'category': 'Extra Tools',
    'author': 'Techsnas',
    'maintainer': 'Techsnas',
    'website': 'https://www.techsnas.com',
    'support': 'info@techsnas.com',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/access_finding_views.xml',
        'wizard/access_explain_views.xml',
        'views/access_audit_menus.xml',
    ],
    'installable': True,
    'application': True,
    'images': ['static/description/banner.png'],
}
