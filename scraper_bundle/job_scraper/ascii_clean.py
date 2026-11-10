"""ASCII-only cleanup for job descriptions.

Pipeline (in order):
  1. repair_mojibake          - undo cp437/cp1252 misreads of valid UTF-8,
                                restoring the correct Unicode character first
  2. transliterate_to_ascii   - map every remaining non-ASCII character to its
                                ASCII equivalent (umlauts -> letter+e, soft
                                quotes/dashes, currency -> ISO codes), drop
                                anything unmappable
  3. fix_mid_word_caps        - lowercase mid-word capitals, leaving acronyms
                                (IBM, CEO, B2B) and TitleCase/proper nouns alone
  4. ensure_terminal_punctuation - strip trailing consent/boilerplate fragments,
                                collapse trailing '...', '!!', '??' to '.',
                                drop hanging - ; , : and append a final period
"""

import re
import unicodedata

_CURRENCY_MAP = {
    "\u20ac": "EUR",  # €
    "\u00a3": "GBP",  # £
    "\u20b9": "INR",  # ₹
    "\u00a5": "JPY",  # ¥
    "\u00a4": "USD",  # ¤ generic currency
    "\u00a2": "cents",  # ¢
    "\u20a9": "KRW",  # ₩
    "\u20bd": "RUB",  # ₽
    "\u20ba": "TRY",  # ₺
    "\u20b1": "PHP",  # ₱
    "\u20b4": "UAH",  # ₴
    "\u20aa": "ILS",  # ₪
    "\u20a6": "NGN",  # ₦
}

_CURRENCY_MAP.update({
    "\u20a1": "CRC",  # ₡
    "\u20ab": "VND",  # ₫
    "\u20b2": "PYG",  # ₲
    "\u20ae": "MNT",  # ₮
    "\u20b8": "KZT",  # ₸
    "\u20be": "GEL",  # ₾
    "\u0e3f": "THB",  # ฿
    "\ufdfc": "SAR",  # ﷼
})

_SPECIAL_MAP = {
    "ä": "ae", "ö": "oe", "ü": "ue",
    "Ä": "AE", "Ö": "OE", "Ü": "UE",
    "ß": "ss", "ẞ": "SS",
    "\u201c": '"', "\u201d": '"', "\u201e": '"', "\u201f": '"',  # “ ” „ ‟
    "\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201b": "'",  # ‘ ’ ‚ ‛
    "\u00ab": '"', "\u00bb": '"', "\u2039": "'", "\u203a": "'",  # « » ‹ ›
    "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-",
    "\u2014": "-", "\u2015": "-", "\u2212": "-", "\u2012\u2013": "-",
    "\u2026": "...",  # …
    "\u00b7": "."  # ·
    # \u00df handled above; œ/æ decompose via NFKD ("oe"/"ae")
}

_SPACE_MAP = {
    "\u00a0": " ",  # NBSP
    "\u2007": " ", "\u2009": " ", "\u200a": " ", "\u202f": " ",
}
_SPECIAL_MAP.update(_SPACE_MAP)

_EXTRA_MAP = {
    "\u00d7": "x",  # ×
    "\u00f7": "/",  # ÷
    "\u00bc": "1/4", "\u00bd": "1/2", "\u00be": "3/4",
    "\u2044": "/",  # fraction slash
    "\u00b0": " deg",  # °
    "\u2205": "",  # hollow bullet (empty, dropped)
}

_MOJI_ENC_CANDIDATES = ("cp437", "cp1252", "latin-1")
_NON_ASCII_RUN = re.compile(r"[^\x00-\x7f]+")

_WORD_RE = re.compile(r"[A-Za-z]+")

_BOILER_TAIL = re.compile(
    r"[\s.,;!?\-/:\u2026]+"
    r"(?:ok(?:ay)?|got\s*its?|accept(?:ed|s|ing)?|accept\s+all|close|dismiss|cancel"
    r"|agree(?:d|ing)?|i\s*(?:agree|understand)|no\s*thanks?|thanks?|thank\s*you"
    r"|skip|done|understand|allow|continue|settings|privacy|consent(?:.*))"
    r"\s*$",
    re.IGNORECASE | re.DOTALL,
)
_PUNCT_RUN_RE = re.compile(r"[.!?]{2,}\s*$")
_HANGING_RE = re.compile(r"[\s\-;,:]+$")


def _repair_run(run):
    """Try to repair one non-ASCII run (encoded cp437/cp1252 -> UTF-8)."""
    for enc in _MOJI_ENC_CANDIDATES:
        try:
            raw = run.encode(enc, errors="strict")
        except (UnicodeEncodeError, UnicodeError):
            continue
        try:
            decoded = raw.decode("utf-8", errors="strict")
        except (UnicodeDecodeError, UnicodeError):
            continue
        if decoded != run:
            return decoded
    return run


def repair_mojibake(text):
    """Undo cp437/cp1252 byte-misreads of valid UTF-8, run by run.

    Mojibake bytes and genuine UTF-8 often sit in the same string (e.g.
    'Gr├╝├ƒe aus der schönen Stadt'); repairing the whole string would fail on
    the genuine 'ö'.  Repair each non-ASCII run independently and repeat so
    double-encoded text (cin├â┬⌐ma -> Ã© -> é) resolves too.
    """
    if not text:
        return text
    current = text
    for _ in range(4):
        done = True
        parts = []
        pos = 0
        for m in _NON_ASCII_RUN.finditer(current):
            parts.append(current[pos:m.start()])
            run = m.group(0)
            run = _repair_run(run)
            if run != m.group(0):
                done = False
            parts.append(run)
            pos = m.end()
        parts.append(current[pos:])
        next_text = "".join(parts)
        if next_text == current:
            break
        current = next_text
        if done:
            break
    return current


def _transliterate_char(ch):
    if ord(ch) < 128:
        return ch
    special = _SPECIAL_MAP.get(ch)
    if special is not None:
        return special
    currency = _CURRENCY_MAP.get(ch)
    if currency is not None:
        return currency
    extra = _EXTRA_MAP.get(ch)
    if extra is not None:
        return extra
    decomposed = unicodedata.normalize("NFKD", ch)
    ascii_letters = "".join(c for c in decomposed
                            if not unicodedata.combining(c) and ord(c) < 128)
    if ascii_letters:
        return ascii_letters
    return ""


def transliterate_to_ascii(text):
    """Replace every non-ASCII character with its ASCII equivalent, or drop it."""
    return "".join(_transliterate_char(c) for c in text)


def fix_mid_word_caps(text):
    """Lowercase stray mid-word capitals.

    ... single interior capital in a CamelCase-style name (McKinsey, eBay,
    coarse placeholder) is left alone.
    """
    def repl(m):
        word = m.group(0)
        if len(word) <= 1:
            return word
        letters = [c for c in word if c.isalpha()]
        if letters and all(c.isupper() for c in letters):
            return word  # acronym / initialism (IBM, CEO, B2B)
        if word[0].isupper() and word[1:].islower():
            return word  # TitleCase name
        interior = sum(1 for i in range(1, len(word)) if word[i].isupper())
        if interior >= 2:
            return word[0] + word[1:].lower()  # scrambled caps
        chars = list(word)
        changed = False
        for i in range(1, len(chars)):
            if not chars[i].isupper():
                continue
            prev_lower = chars[i - 1].islower()
            nxt_lower = i + 1 < len(chars) and chars[i + 1].islower()
            if prev_lower and nxt_lower and interior == 1:
                continue  # single capital inside a name (McKinsey, eBay, iOS)
            if interior == 1 and (prev_lower or not prev_lower):
                chars[i] = chars[i].lower()
                changed = True
        out = "".join(chars)
        if out == word:
            return word
        return out

    return _WORD_RE.sub(repl, text)


def ensure_terminal_punctuation(text):
    """Force the string to end in '.', '!' or '?' (optionally + quote/paren)."""
    text = (text or "").rstrip()
    if not text:
        return text

    closers = ""
    while text and text[-1] in ")\"'":
        closers = text[-1] + closers
        text = text[:-1].rstrip()

    # strip trailing consent/boilerplate fragments repeatedly
    changed = True
    guards = 0
    while changed and guards < 8:
        changed = False
        matches = list(_BOILER_TAIL.finditer(" " + text))
        if not matches:
            break
        m = matches[-1]
        start = m.start() - 1
        if start < 0:
            start = 0
        new_text = text[:start].rstrip()
        if new_text and new_text != text:
            text = new_text
            changed = True
        guards += 1

    text = text.rstrip()
    text = _PUNCT_RUN_RE.sub(".", text)
    text = _HANGING_RE.sub("", text)
    if text and text[-1] not in ".!?":
        text += "."
    return text + closers


def ascii_clean(text):
    """Full ASCII cleanup pipeline for a job description."""
    if not text:
        return ""
    text = repair_mojibake(str(text))
    text = transliterate_to_ascii(text)
    text = fix_mid_word_caps(text)
    text = ensure_terminal_punctuation(text)
    return text