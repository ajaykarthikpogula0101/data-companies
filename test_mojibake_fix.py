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
        ("GlÃ¼ckstein", "Glückstein", "German umlaut ü"),
        ("MÃ¼nchen", "München", "German umlaut ü"),
        ("StraÃe", "Straße", "German sharp s ß"),
        ("KÃ¶ln", "Köln", "German umlaut ö"),
        ("BjÃ¶rk", "Björk", "Swedish ö"),
        ("â€œHelloâ€”", '"Hello"—', "Quotation marks and em dash"),
        ("GroÃŸenÃ¶ffnung", "Großenöffnung", "Multiple mojibake"),
        ("Wein â€“ lecker!", "Wein – lecker!", "En dash"),
        ("Preis: 10â‚¬", "Preis: 10€", "Euro symbol"),
        ("Hello World", "Hello World", "Already correct ASCII"),
        ("Guten Tag", "Guten Tag", "Already correct German"),
        ("Straße", "Straße", "Already correct ß"),
        # Test integration with clean function
        (None, "", "None input"),
        ("", "", "Empty string"),
        ("   ", "", "Whitespace only"),
        ("none", "", "None keyword"),
        ("Null", "", "Null keyword"),
        ("N/A", "", "N/A keyword"),
        ("not specified", "", "not specified"),
        ("unknown", "", "unknown"),
        ("  GlÃ¼ckstein  ", "Glückstein", "Mojibake with whitespace"),
        ("  MÃ¼nchen  ", "München", "Mojibake with whitespace"),
    ]

    passed = 0
    failed = 0

    for input_val, expected, description in test_cases:
        try:
            result = clean(input_val)
            if result == expected:
                print(f"✓ PASS: {description}")
                passed += 1
            else:
                print(f"✗ FAIL: {description}")
                print(f"  Input: {repr(input_val)}")
                print(f"  Expected: {repr(expected)}")
                print(f"  Got: {repr(result)}")
                failed += 1
        except Exception as e:
            print(f"✗ ERROR: {description}")
            print(f"  Input: {repr(input_val)}")
            print(f"  Exception: {e}")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0

if __name__ == "__main__":
    success = test_mojibake_fix()
    sys.exit(0 if success else 1)