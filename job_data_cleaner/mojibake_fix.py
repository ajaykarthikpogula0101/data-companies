"""Mojibake fixing utilities for job data cleaning."""

import re


def fix_mojibake(text: str) -> str:
    """Fix common mojibake patterns where UTF-8 text was decoded as Latin-1/CP1252.

    Common examples:
    - Ã¼ -> ü
    - Ã¶ -> ö
    - Ã -> ß
    - â€œ -> "
    - â€” -> —

    Args:
        text: Input string that may contain mojibake

    Returns:
        Fixed string with mojibake corrected
    """
    if not text or not isinstance(text, str):
        return text

    # Quick check: if text doesn't contain likely mojibake patterns, return as-is
    if not re.search(r'[ÃâÂ]', text):
        return text

    try:
        # Try to fix by re-encoding as latin-1 then decoding as utf-8
        # This works for the common case where utf-8 bytes were interpreted as latin-1
        fixed = text.encode('latin-1').decode('utf-8')

        # Validate that the fix improved the text (reduced strange characters)
        # Count non-ascii characters that are likely to be legitimate vs mojibake
        original_weird = len(re.findall(r'[ÃâÂ][^\s]', text))
        fixed_weird = len(re.findall(r'[ÃâÂ][^\s]', fixed))

        # If fix reduces weird patterns or makes text more reasonable, use it
        if fixed_weird < original_weird or (fixed_weird == 0 and original_weird > 0):
            return fixed

    except (UnicodeEncodeError, UnicodeDecodeError):
        # If encoding/decoding fails, return original
        pass

    return text


def has_mojibake(text: str) -> bool:
    """Check if text likely contains mojibake.

    Args:
        text: Input string to check

    Returns:
        True if mojibake patterns are detected
    """
    if not text or not isinstance(text, str):
        return False

    # Common mojibake starter characters
    mojibake_pattern = r'[ÃâÂ][^\s]'
    return bool(re.search(mojibake_pattern, text))


def clean_with_mojibake_fix(value: object) -> str:
    """Clean value and fix mojibake encoding issues.

    Args:
        value: Input value to clean

    Returns:
        Cleaned string with mojibake fixed
    """
    text = "" if value is None else str(value).strip()
    if text.lower() in {"", "none", "null", "nan", "n/a", "na", "not specified", "unknown"}:
        return ""
    return fix_mojibake(text)