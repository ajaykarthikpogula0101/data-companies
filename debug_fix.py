#!/usr/bin/env python3
"""Debug the fix_mojibake function to see what it's actually doing."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'job_data_cleaner'))

from clean_jobs import fix_mojibake

def debug_fix_mojibake(text):
    """Debug version that shows what's happening step by step."""
    print("Input: %r" % text)
    if not isinstance(text, str) or not text:
        print("  Not a string or empty, returning as-is")
        return text

    try:
        print("  Attempting to encode as latin-1...")
        encoded = text.encode('latin-1')
        print("  Encoded bytes: %r" % encoded)
        print("  Decoding as utf-8...")
        fixed = encoded.decode('utf-8')
        print("  Fixed string: %r" % fixed)

        if fixed != text:
            print("  Strings differ, returning fixed version")
            return fixed
        else:
            print("  Strings are identical, returning original")
            return text
    except (UnicodeEncodeError, UnicodeDecodeError) as e:
        print("  Encoding/decoding error: %s" % e)
        return text

# Test with a simple case
print("=== Testing with 'MÃ¼nchen' ===")
result = debug_fix_mojibake("MÃ¼nchen")
print("Final result: %r" % result)
print()

# Test with the actual bytes transformation
print("=== Manual byte transformation ===")
original = "MÃ¼nchen"
print("Original string: %r" % original)
print("Original as bytes (latin-1): %r" % original.encode('latin-1'))
print("Those bytes decoded as utf-8: %r" % original.encode('latin-1').decode('utf-8'))