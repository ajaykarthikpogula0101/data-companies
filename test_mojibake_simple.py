#!/usr/bin/env python3
"""Test the mojibake fix functionality."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'job_data_cleaner'))

from clean_jobs import clean

def test_mojibake_fix():
    """Test that mojibake is properly fixed."""
    print("Testing mojibake fix...")

    # Test cases with mojibake
    test_cases = [
        # (input, expected_output, description)
        ("GlÃ¼ckstein", "Glückstein", "German umlaut ue"),
        ("MÃ¼nchen", "München", "German umlaut ue"),
        ("StraÃe", "Straße", "German sharp s"),
        ("KÃ¶ln", "Köln", "German umlaut oe"),
        ("BjÃ¶rk", "Björk", "Swedish oe"),
        ("GroÃŸenÃ¶ffnung", "Großenöffnung", "Multiple mojibake"),
        ("Preis: 10â‚¬", "Preis: 10€", "Euro symbol"),
        # Test integration with clean function
        (None, "", "None input"),
        ("", "", "Empty string"),
        ("   ", "", "Whitespace only"),
        ("none", "", "None keyword"),
        ("N/A", "", "N/A keyword"),
        ("  GlÃ¼ckstein  ", "Glückstein", "Mojibake with whitespace"),
        ("  MÃ¼nchen  ", "München", "Mojibake with whitespace"),
    ]

    passed = 0
    failed = 0

    for input_val, expected, description in test_cases:
        try:
            result = clean(input_val)
            if result == expected:
                print("PASS: {}".format(description))
                passed += 1
            else:
                print("FAIL: {}".format(description))
                print("  Input: {}".format(repr(input_val)))
                print("  Expected: {}".format(repr(expected)))
                print("  Got: {}".format(repr(result)))
                failed += 1
        except Exception as e:
            print("ERROR: {}".format(description))
            print("  Input: {}".format(repr(input_val)))
            print("  Exception: {}".format(e))
            failed += 1

    print("\nResults: {} passed, {} failed".format(passed, failed))
    return failed == 0

if __name__ == "__main__":
    success = test_mojibake_fix()
    sys.exit(0 if success else 1)