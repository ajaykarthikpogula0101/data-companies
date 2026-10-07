#!/usr/bin/env python3
"""Test with real mojibaked strings from the data."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'job_data_cleaner'))

from clean_jobs import fix_mojibake

def test_with_real_data():
    """Test with actual mojibaked strings from the CSV."""
    print("=== Testing with real mojibaked strings ===")

    # These are the actual mojibaked strings from the CSV data
    test_cases = [
        # (mojibaked_string, expected_correct_string, description)
        ("MÃ¼nchen Gilching", "München Gilching", "Muenchen from CSV"),
        ("GlÃ¼ckstein", "Glückstein", "Glueckstein from CSV"),
        ("WeiÃes Quartier", "Weißes Quartier", "Weisses from CSV"),
        ("GespÃ¼r", "Gespür", "Gespuert from CSV"),
        ("Hands-on-MentalitÃ¤t", "Hands-on-Mentalität", "Mentalitaet from CSV"),
        ("Teilzeit", "Teilzeit", "Correct as-is"),
        ("Vollzeit", "Vollzeit", "Correct as-is"),
    ]

    all_passed = True
    for mojibaked, expected, desc in test_cases:
        try:
            result = fix_mojibake(mojibaked)
            if result == expected:
                print("PASS: %s" % desc)
                print("    %r -> %r" % (mojibaked, result))
            else:
                print("FAIL: %s" % desc)
                print("    %r -> %r (expected %r)" % (mojibaked, result, expected))
                all_passed = False
        except Exception as e:
            print("ERROR: %s" % desc)
            print("    %r -> Exception: %s" % (mojibaked, str(e)))
            all_passed = False
        print()

    return all_passed

def test_clean_function():
    """Test the clean function."""
    print("=== Testing clean function ===")

    from clean_jobs import clean

    test_cases = [
        # (input_value, expected_output, description)
        (None, "", "None input"),
        ("", "", "Empty string"),
        ("   MÃ¼nchen   ", "München", "Mojibake with spaces"),
        ("  GlÃ¼ckstein  ", "Glückstein", "Glueckstein with spaces"),
        ("Teilzeit", "Teilzeit", "Already correct"),
        ("null", "", "null keyword"),
        ("N/A", "", "N/A keyword"),
        ("not specified", "", "not specified keyword"),
    ]

    all_passed = True
    for inp, expected, desc in test_cases:
        try:
            result = clean(inp)
            if result == expected:
                print("PASS: %s" % desc)
                print("    %r -> %r" % (inp, result))
            else:
                print("FAIL: %s" % desc)
                print("    %r -> %r (expected %r)" % (inp, result, expected))
                all_passed = False
        except Exception as e:
            print("ERROR: %s" % desc)
            print("    %r -> Exception: %s" % (inp, str(e)))
            all_passed = False
        print()

    return all_passed

def main():
    print("Testing mojibake fix with real data from CSV...\n")

    test1 = test_with_real_data()
    test2 = test_clean_function()

    print("=" * 60)
    if test1 and test2:
        print("SUCCESS: All tests passed!")
        print("The mojibake fix is working correctly.")
        return 0
    else:
        print("FAILURE: Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())