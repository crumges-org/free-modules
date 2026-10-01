"""Value masking, applied server-side on the way out.

Masking differs from hiding: the field stays present and the record stays
usable, but the value is redacted. That is what you want for a phone number a
support agent must know exists but should not read in full.

Because it happens in ``_read_format`` (see ``inherits/base_records.py``), a
masked value is masked over XML-RPC and the JSON API too - not just in the
browser.
"""

MASK_CHAR_DEFAULT = '*'

#: Mask types added by other modules: ``{type: function(text, keep, char)}``.
MASKERS = {}


def register_mask(mask_type, function):
    """Add a mask type. ``function(text, keep, char)`` returns the redacted text.

    The built-in types are tried first and cannot be replaced.
    """
    MASKERS[mask_type] = function


def _mask_tail(text, keep, char):
    """Redact everything but the last ``keep`` characters."""
    if keep <= 0:
        return char * len(text)
    if len(text) <= keep:
        # Too short to partially redact without giving the whole thing away.
        return char * len(text)
    return char * (len(text) - keep) + text[-keep:]


def _mask_email(text, char):
    """a***@domain.com - keeps the domain, which is rarely the sensitive part."""
    if '@' not in text:
        return _mask_tail(text, 0, char)
    local, _, domain = text.partition('@')
    if not local:
        return text
    return '%s%s@%s' % (local[0], char * max(len(local) - 1, 1), domain)


def _mask_phone(text, keep, char):
    """Redact digits but keep formatting, so the shape stays recognisable."""
    digits = [i for i, c in enumerate(text) if c.isdigit()]
    if not digits:
        return _mask_tail(text, keep, char)
    to_mask = set(digits[:-keep] if keep > 0 else digits)
    return ''.join(char if i in to_mask else c for i, c in enumerate(text))


def apply_mask(value, spec):
    """Return ``value`` redacted according to ``spec``, or unchanged.

    ``spec`` is the dict the policy compiler builds:
    ``{'type', 'char', 'keep', 'pattern'}``. Falsy values are returned as-is -
    masking an empty field would only advertise that something is hidden there.
    """
    if not spec or value in (False, None, ''):
        return value

    mask_type = spec.get('type') or 'none'
    if mask_type == 'none':
        return value

    char = (spec.get('char') or MASK_CHAR_DEFAULT)[:1] or MASK_CHAR_DEFAULT
    keep = spec.get('keep') or 0

    if mask_type == 'custom':
        return spec.get('pattern') or ''

    text = value if isinstance(value, str) else str(value)

    if mask_type == 'full':
        return char * len(text)
    if mask_type == 'partial':
        return _mask_tail(text, keep, char)
    if mask_type == 'email':
        return _mask_email(text, char)
    if mask_type == 'phone':
        return _mask_phone(text, keep, char)
    masker = MASKERS.get(mask_type)
    if masker is not None:
        return masker(text, keep, char)
    return value
