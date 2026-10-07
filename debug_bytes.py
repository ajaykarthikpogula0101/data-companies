#!/usr/bin/env python3
"""Debug the actual byte values of mojibaked strings."""

# Let's see what the actual bytes are
test_strings = [
    "GroÃŸenÃ¶ffnung",
    "Wein â€“ lecker!",
    "Preis: 10â‚¬",
    "GlÃ¼ckstein",
    "MÃ¼nchen Gilching"
]

print("String analysis:")
for s in test_strings:
    print("String: {}".format(repr(s)))
    print("  Length: {}".format(len(s)))
    print("  Bytes (UTF-8): {}".format(s.encode('utf-8')))
    print("  Bytes (Latin-1): {}".format(s.encode('latin-1') if all(ord(c) < 256 for c in s) else "NOT LATIN-1 COMPATIBLE"))
    print()

# Now let's see what they should decode to
print("Testing fix_mojibake manually:")
for s in test_strings:
    try:
        # Try the latin-1 -> utf-8 trick
        if all(ord(c) < 256 for c in s):  # Check if latin-1 encodable
            encoded = s.encode('latin-1')
            decoded = encoded.decode('utf-8')
            print("{} -> {}".format(repr(s), repr(decoded)))
        else:
            print("{} -> (not latin-1 encodable)".format(repr(s)))
    except Exception as e:
        print("{} -> ERROR: {}".format(repr(s), e))