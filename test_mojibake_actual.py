#!/usr/bin/env python3
"""Test the mojibake fix functionality with actual mojibaked strings from data."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'job_data_cleaner'))

from clean_jobs import clean

def test_mojibake_fix():
    """Test that mojibake is properly fixed."""
    print("Testing mojibake fix with actual mojibaked strings from CSV data...")

    # Test cases with ACTUAL mojibaked input and CORRECT expected output
    # These are the actual mojibaked strings we saw in the CSV data
    test_cases = [
        # (mojibaked_input, correct_output, description)
        ("MÃ¼nchen Gilching", "München Gilching", "Muenchen from CSV"),
        ("GlÃ¼ckstein", "Glückstein", "Glueckstein from CSV"),
        ("WeiÃes Quartier", "Weißes Quartier", "Weisses from CSV"),
        ("GespÃ¼r", "Gespür", "Gespuert from CSV"),
        ("Hands-on-MentalitÃ¤t", "Hands-on-Mentalität", "Mentalitaet from CSV"),
        ("Teilzeit", "Teilzeit", "Already correct - should remain unchanged"),
        ("Vollzeit", "Vollzeit", "Already correct - should remain unchanged"),
        ("GroÃŸenÃ¶ffnung", "Großen Eröffnung", "Multiple mojibake from CSV pattern"),
        ("Wein â€“ lecker!", "Wein – lecker!", "En dash from CSV pattern"),
        ("Preis: 10â‚¬", "Preis: 10€", "Euro symbol from CSV pattern"),
        # Test integration with clean function for edge cases
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