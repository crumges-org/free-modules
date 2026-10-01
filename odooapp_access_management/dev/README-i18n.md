# Regenerating the translations

The module ships `de`, `fr`, `es`, `zh_CN` and `ar`. The 595 timezone entries in
the `.pot` come from the `tz` selection on `aam.time.window`; they are IANA
identifiers and are deliberately left untranslated, as Odoo core does.

## When a string changes

1. Upgrade the module so the database has the new terms, then re-export:

       odoo-bin -c dev/aam_dev.conf -d aam19_dev -u odooapp_access_management --stop-after-init
       odoo-bin i18n export -c dev/aam_dev.conf -d aam19_dev odooapp_access_management

2. `dev/translations.json` is keyed by the index of `dev/real.json`, which is the
   `.pot` minus the timezones. Re-derive both after an export, translate whatever
   comes back missing, and merge it:

       python dev/merge.py <batch.json>

   A batch is `{"<index>": {"de": ..., "fr": ..., "es": ..., "zh": ..., "ar": ...}}`.
   Inside a batch, write `\n` for a newline and `\"` for a quote — `build_po.py`
   converts both to real characters before escaping, so nothing ends up
   double-escaped in the `.po`.

3. Rebuild and check:

       python dev/build_po.py
       python dev/check_po.py

`check_po.py` compares every translation with its source term for matching
`%s` / `%(name)s` placeholders, `{{ ... }}` expressions and HTML tags. A wrong
placeholder is the one translation mistake that raises at runtime rather than
merely reading badly, so this must be clean before shipping.

## Verifying in the database

    odoo-bin i18n loadlang -c dev/aam_dev.conf -d aam19_dev -l de fr es zh_CN ar
    odoo-bin shell -c dev/aam_dev.conf -d aam19_dev < dev/check_i18n.py

`check_i18n.py` writes UTF-8 to `dev/i18n_check.txt` rather than printing: the
Windows console is cp1252 and raises on the Chinese and Arabic output.
