"""Assemble per-language .po files from the .pot plus the translation dict.

The .pot is walked block by block and copied verbatim; only the `msgstr` line is
replaced. That keeps every reference comment and flag (`#, python-format`) exactly
as Odoo exported it, which matters because the flags drive its own validation.
"""
import io
import os
import re
import sys

SCRATCH = os.path.dirname(os.path.abspath(__file__))
MODULE = os.path.dirname(SCRATCH)   # the module root, i.e. the parent of dev/
# Derived from this file's own location, never hard-coded. The literal path that
# used to be here pointed at the Odoo 19 checkout, so running this script from
# the 18 worktree silently rewrote the *other* branch's shipped .po files while
# reporting success.
POT = os.path.join(MODULE, 'i18n', 'odooapp_access_management.pot')

import json

LANGS = {
    # code -> (po filename, Language header, Plural-Forms)
    'de': ('de.po', 'de', 'nplurals=2; plural=(n != 1);'),
    'fr': ('fr.po', 'fr', 'nplurals=2; plural=(n > 1);'),
    'es': ('es.po', 'es', 'nplurals=2; plural=(n != 1);'),
    'zh': ('zh_CN.po', 'zh_CN', 'nplurals=1; plural=0;'),
    'ar': ('ar.po', 'ar',
           'nplurals=6; plural=(n==0 ? 0 : n==1 ? 1 : n==2 ? 2 : n%100>=3 '
           '&& n%100<=10 ? 3 : n%100>=11 ? 4 : 5);'),
}


def unquote(lines):
    out = []
    for line in lines:
        m = re.match(r'^"(.*)"$', line.strip())
        if m:
            out.append(m.group(1))
    return ''.join(out)


def normalise(text):
    """Turn the escapes used in the batch files into real characters.

    Batch entries wrote `\\n` for a newline and `\\"` for a quote so they would
    line up visually with the source term. Both have to become real characters
    before escaping, or they end up double-escaped in the .po.
    """
    out = []
    i = 0
    while i < len(text):
        c = text[i]
        if c == '\\' and i + 1 < len(text):
            nxt = text[i + 1]
            if nxt == 'n':
                out.append('\n')
                i += 2
                continue
            if nxt == '"':
                out.append('"')
                i += 2
                continue
            raise AssertionError('unexpected escape %r in %r' % (nxt, text[:60]))
        out.append(c)
        i += 1
    return ''.join(out)


def escape(text):
    return text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')


def render_msgstr(text):
    """`msgstr` lines, split after each newline the way gettext tools do."""
    if not text:
        return ['msgstr ""']
    escaped = escape(text)
    if '\\n' not in escaped:
        return ['msgstr "%s"' % escaped]
    parts = escaped.split('\\n')
    chunks = [p + '\\n' for p in parts[:-1]]
    if parts[-1]:
        chunks.append(parts[-1])
    return ['msgstr ""'] + ['"%s"' % c for c in chunks]


def main():
    entries = json.load(io.open(os.path.join(SCRATCH, 'real.json'), encoding='utf-8'))
    table = json.load(io.open(os.path.join(SCRATCH, 'translations.json'), encoding='utf-8'))

    by_msgid = {}
    for i, entry in enumerate(entries):
        row = table.get(str(i))
        if row:
            by_msgid[entry['id']] = row

    pot = io.open(POT, encoding='utf-8').read()
    blocks = pot.split('\n\n')

    for lang, (filename, header_lang, plural) in LANGS.items():
        out_blocks = []
        translated = 0
        for bi, block in enumerate(blocks):
            if not block.strip():
                continue
            lines = block.split('\n')
            body_start = next((n for n, l in enumerate(lines)
                               if l.startswith('msgid')), None)
            if body_start is None:
                out_blocks.append(block)
                continue
            head = lines[:body_start]
            rest = lines[body_start:]
            msgstr_at = next(n for n, l in enumerate(rest) if l.startswith('msgstr'))
            msgid_lines = rest[:msgstr_at]
            msgid = unquote([msgid_lines[0][len('msgid '):]] + msgid_lines[1:])

            if not msgid:  # the header block
                out_blocks.append(header_block(header_lang, plural))
                continue

            row = by_msgid.get(msgid)
            text = normalise(row[lang]) if row else ''
            if text:
                translated += 1
            out_blocks.append('\n'.join(head + msgid_lines + render_msgstr(text)))

        path = os.path.join(MODULE, 'i18n', filename)
        io.open(path, 'w', encoding='utf-8', newline='\n').write(
            '\n\n'.join(out_blocks) + '\n')
        print('%-8s %-10s %4d translated' % (lang, filename, translated))


def pot_header_value(key, default):
    """Read one header field back out of the .pot.

    Odoo regenerates the .pot per serie, so `Project-Id-Version` and
    `POT-Creation-Date` are already right there. Reading them keeps this script
    byte-identical on the 18.0 and 19.0 branches - the value that used to be
    frozen in the list below said "Odoo Server 19.0" and would have stamped the
    wrong serie onto every Odoo 18 translation.
    """
    prefix = '"%s:' % key
    with io.open(POT, encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("#:"):
                break
            if line.startswith(prefix):
                value = line.strip()[len(prefix):].rstrip('"')
                # .po header values end with a literal backslash-n, two
                # characters - not a newline. chr(92) rather than an escape so
                # the intent survives anyone re-quoting this line.
                return value.replace(chr(92) + 'n', '').strip()
    return default


def header_block(header_lang, plural):
    series = pot_header_value('Project-Id-Version', 'Odoo Server')
    created = pot_header_value('POT-Creation-Date', '')
    return '\n'.join([
        '# Translation of Odoo Server.',
        '# This file contains the translation of the following modules:',
        '# \t* odooapp_access_management',
        '#',
        'msgid ""',
        'msgstr ""',
        '"Project-Id-Version: %s\\n"' % series,
        '"Report-Msgid-Bugs-To: \\n"',
        '"POT-Creation-Date: %s\\n"' % created,
        '"PO-Revision-Date: %s\\n"' % created,
        '"Last-Translator: \\n"',
        '"Language-Team: \\n"',
        '"MIME-Version: 1.0\\n"',
        '"Content-Type: text/plain; charset=UTF-8\\n"',
        '"Content-Transfer-Encoding: \\n"',
        '"Language: %s\\n"' % header_lang,
        '"Plural-Forms: %s\\n"' % plural,
    ])


if __name__ == '__main__':
    main()
