"""Spot-check that the shipped .po files actually resolve in each language.

Covers the three storage paths a translation can take in v19 - a Selection
label, a field `string`, an `ir.ui.menu` name loaded from XML, and a
`res.groups` name - because each is imported by a different code path.

Writes UTF-8 to a file rather than printing: the Windows console is cp1252 and
raises on the Chinese and Arabic output.
"""
import io

langs = ['de_DE', 'fr_FR', 'es_ES', 'zh_CN', 'ar_001']
out = ['installed: %s' % sorted(env['res.lang'].search([]).mapped('code'))]

for lang in langs:
    e = env(context=dict(env.context, lang=lang))
    sel = dict(e['aam.rule'].fields_get(['enforcement'])['enforcement']['selection'])
    label = e['aam.rule'].fields_get(['priority'])['priority']['string']
    helptext = e['aam.rule'].fields_get(['soft_restrict'])
    menu = e.ref('odooapp_access_management.menu_aam_root')
    group = e.ref('odooapp_access_management.group_aam_manager')
    tmpl = e.ref('odooapp_access_management.mail_template_password_expiry')
    out.append('%-7s | %-14s | %-12s | %-22s | %-16s | %s' % (
        lang, sel.get('enforced'), label, menu.name, group.name, tmpl.subject))

io.open('dev/i18n_check.txt', 'w', encoding='utf-8').write('\n'.join(out) + '\n')
print('wrote dev/i18n_check.txt')
