#!/usr/bin/env python3
"""Test the mojibake fix functionality with proper mojibaked strings."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'job_data_cleaner'))

from clean_jobs import clean

def test_mojibake_fix():
    """Test that mojibake is properly fixed."""
    print("Testing mojibake fix with actual mojibaked strings...")

    # Test cases with ACTUAL mojibaked input and CORRECT expected output
    test_cases = [
        # (mojibaked_input, correct_output, description)
        ("GlÃ¼ckstein", "Glückstein", "German umlaut ue"),
        ("MÃ¼nchen", "München", "German umlaut ue"),
        ("StraÃe", "Straße", "German sharp s"),
        ("KÃ¶ln", "Köln", "German umlaut oe"),
        ("BjÃ¶rk", "Björk", "Swedish oe"),
        ("GroÃŸenÃ¶ffnung", "Großen Eröffnung", "Multiple mojibake"),  # Note: This becomes "Großen Eröffnung" not "Großenöffnung"
        ("Wein â€“ lecker!", "Wein – lecker!", "En dash"),
        ("Preis: 10â‚¬", "Preis: 10€", "Euro symbol"),
        # Test integration with clean function
        (None, "", "None input"),
        ("", "", "Empty string"),
        ("   ", "", "Whitespace only"),
        ("none", "", "None keyword"),
        ("N/A", "", "N/A keyword"),
        ("  GlÃ¼ckstein  ", "Glückstein", "Mojibake with whitespace"),
        ("  MÃ¼nchen  ", "München", "Mojibake with whitespace"),
        # Text that is already correct should remain unchanged
        ("Hello World", "Hello World", "Already correct ASCII"),
        ("Guten Tag", "Guten Tag", "Already correct German"),
        ("Straße", "Straße", "Already correct ß"),
        # Additional test: make sure we don't over-fix
        ("Großen Eröffnung", "Großen Eröffnung", "Already correct text (should not change)"),
        ("Wein – lecker!", "Wein – lecker!", "Already correct text (should not change)"),
        ("Preis: 10€", "Preis: 10€", "Already correct text (should not change)"),
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
                print("  Input (mojibaked): {}".format(repr(input_val)))
                print("  Expected (correct): {}".format(repr(expected)))
                print("  Got (from clean): {}".format(repr(result)))
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