"""Check every translation against its source term.

A wrong placeholder is the one translation mistake that crashes at runtime rather
than merely reading badly, so it is checked first and hardest.
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
FILES = ['de.po', 'fr.po', 'es.po', 'zh_CN.po', 'ar.po']

NAMED = re.compile(r'%\([a-zA-Z_][a-zA-Z0-9_]*\)[sdrf]')
POSITIONAL = re.compile(r'%[sdrf]')
CURLY = re.compile(r'\{\{.*?\}\}')
TAGS = re.compile(r'</?([a-zA-Z][a-zA-Z0-9-]*)')


def unquote(lines):
    out = []
    for line in lines:
        m = re.match(r'^"(.*)"$', line.strip())
        if m:
            out.append(m.group(1))
    return ''.join(out)


def unescape(text):
    return (text.replace('\\n', '\n').replace('\\"', '"')
                .replace('\\t', '\t').replace('\\\\', '\\'))


def entries(path):
    raw = io.open(path, encoding='utf-8').read()
    for block in raw.split('\n\n'):
        lines = [l for l in block.split('\n') if not l.startswith('#')]
        if not lines or not lines[0].startswith('msgid'):
            continue
        at = next((n for n, l in enumerate(lines) if l.startswith('msgstr')), None)
        if at is None:
            continue
        msgid = unquote([lines[0][len('msgid '):]] + lines[1:at])
        msgstr = unquote([lines[at][len('msgstr '):]] + lines[at + 1:])
        if not msgid:
            continue
        yield unescape(msgid), unescape(msgstr)


def main():
    problems = 0
    for name in FILES:
        path = os.path.join(MODULE, 'i18n', name)
        total = done = 0
        for src, dst in entries(path):
            total += 1
            if not dst:
                continue
            done += 1

            for label, rx in (('named placeholder', NAMED),
                              ('positional placeholder', POSITIONAL),
                              ('curly expression', CURLY)):
                a, b = sorted(rx.findall(src)), sorted(rx.findall(dst))
                if a != b:
                    print('%s: %s mismatch\n  src: %r\n  dst: %r' % (name, label, src[:90], dst[:90]))
                    problems += 1

            a, b = TAGS.findall(src), TAGS.findall(dst)
            if a != b:
                print('%s: html tag mismatch\n  src: %r\n  dst: %r' % (name, src[:90], dst[:90]))
                problems += 1

            # A term made only of placeholders and punctuation has nothing to
            # translate, so an identical copy is correct rather than lazy.
            words = re.sub(r'%\([^)]*\)[sdrf]|%[sdrf]|[^\w]', ' ', src).split()
            if dst.strip() == src.strip() and len(words) > 3:
                print('%s: untranslated copy: %r' % (name, src[:70]))
                problems += 1

        print('%-10s %d/%d translated' % (name, done, total))
    print('problems:', problems)
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
