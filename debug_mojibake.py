#!/usr/bin/env python3
"""Debug script to understand mojibake fixing."""

def debug_fix_mojibake(text: str) -> str:
    """Debug version of fix_mojibake with detailed logging."""
    print(f"Input: {repr(text)}")
    if not text or not isinstance(text, str):
        print("  Not a string or empty")
        return text

    # Quick check: if text doesn't contain likely mojibake patterns, return as-is
    import re
    if not re.search(r'[ÃâÂ]', text):
        print("  No mojibake patterns found")
        return text

    print("  Mojibake patterns detected, attempting fix...")
    try:
        # Try to fix by re-encoding as latin-1 then decoding as utf-8
        # This works for the common case where utf-8 bytes were interpreted as latin-1
        encoded = text.encode('latin-1')
        print(f"  After latin-1 encode: {repr(encoded)}")
        fixed = encoded.decode('utf-8')
        print(f"  After utf-8 decode: {repr(fixed)}")

        # Validate that the fix improved the text (reduced strange characters)
        # Count non-ascii characters that are likely to be legitimate vs mojibake
        original_weird = len(re.findall(r'[ÃâÂ][^\s]', text))
        fixed_weird = len(re.findall(r'[ÃâÂ][^\s]', fixed))
        print(f"  Original weird patterns: {original_weird}")
        print(f"  Fixed weird patterns: {fixed_weird}")

        # If fix reduces weird patterns or makes text more reasonable, use it
        if fixed_weird < original_weird or (fixed_weird == 0 and original_weird > 0):
            print(f"  Fix applied: {repr(text)} -> {repr(fixed)}")
            return fixed
        else:
            print(f"  Fix not beneficial, keeping original")
    except (UnicodeEncodeError, UnicodeDecodeError) as e:
        # If encoding/decoding fails, return original
        print(f"  Encoding/decoding error: {e}")
        pass

    print(f"  No fix applied, returning original: {repr(text)}")
    return text

# Test the debug function
test_cases = [
    "GlÃ¼ckstein",
    "MÃ¼nchen",
    "StraÃe",
    "KÃ¶ln",
    "BjÃ¶rk",
    "â€œHelloâ€”",
    "GroÃŸenÃ¶ffnung",
]

print("=== Debugging mojibake fix ===")
for test in test_cases:
    result = debug_fix_mojibake(test)
    print(f"Result: {repr(result)}")
    print()