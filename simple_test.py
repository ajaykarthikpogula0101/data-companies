#!/usr/bin/env python3
"""Simple test of mojibake fix."""

def fix_mojibake(text: str) -> str:
    """Attempt to fix double-encoded UTF-8 (mojibake) by encoding as latin-1 and decoding as utf-8."""
    if not isinstance(text, str) or not text:
        return text
    try:
        # Try to encode as latin-1 (this should work if the string is actually latin-1 encoded UTF-8 bytes)
        encoded = text.encode('latin-1')
        # Now decode as utf-8
        fixed = encoded.decode('utf-8')
        # If the fixed string is different, return it (conservative: only change if different)
        if fixed != text:
            return fixed
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    return text

# Test cases from the user's test
test_cases = [
    ('Ã¼', 'ü'),
    ('Ã¶', 'ö'),
    ('Ã', 'ß'),
    ('â€œ', '"'),
    ('â€”', '—'),
    ('Ã¤', 'ä'),
    ('Ã„', 'Ä'),
    ('normal', 'normal'),
    ('', ''),
    (None, None),
]

print("Testing fix_mojibake:")
for inp, expected in test_cases:
    if inp is None:
        result = fix_mojibake(None)
        ok = result is None
        print(f"Input: {inp!r} -> {result!r} (expected: {expected!r}) {'OK' if ok else 'FAIL'}")
    else:
        result = fix_mojibake(inp)
        ok = result == expected
        print(f"Input: {inp!r} -> {result!r} (expected: {expected!r}) {'OK' if ok else 'FAIL'}")

# Additional test: the compound examples
print("\nTesting compound examples:")
compound_tests = [
    ('GlÃ¼ckstein', 'Glückstein'),
    ('MÃ¼nchen', 'München'),
    ('StraÃe', 'Straße'),
]

for inp, expected in compound_tests:
    result = fix_mojibake(inp)
    ok = result == expected
    print(f"Input: {inp!r} -> {result!r} (expected: {expected!r}) {'OK' if ok else 'FAIL'}")