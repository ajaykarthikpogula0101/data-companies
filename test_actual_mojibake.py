#!/usr/bin/env python3
"""Test script to verify mojibake fixing with actual mojibaked strings."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'job_data_cleaner'))

from clean_jobs import fix_mojibake

def test_actual_mojibake():
    """Test fix_mojibake with actual mojibaked strings from the data."""
    print("=== Testing fix_mojibake with actual mojibaked strings ===")

    # Test cases with actual mojibake from the CSV data
    test_cases = [
        # (mojibaked_input, expected_correct_output, description)
        ("MÃ¼nchen Gilching", "München Gilching", "München with umlaut"),
        ("GlÃ¼ckstein", "Glückstein", "Glückstein with umlaut"),
        ("WeiÃes Quartier", "Weißes Quartier", "Weißes with sharp s"),
        ("GespÃ¼r", "Gespür", "Gespür with umlaut"),
        ("Hands-on-MentalitÃ¤t", "Hands-on-Mentalität", "Mentalität with umlaut"),
        ("Teilzeit", "Teilzeit", "Already correct - no change"),
        ("Vollzeit", "Vollzeit", "Already correct - no change"),
        ("GroÃŸenÃ¶ffnung", "Großenöffnung", "Multiple mojibake"),
        ("Quartier", "Quartier", "Already correct - no change"),
    ]

    all_passed = True
    for inp, expected, desc in test_cases:
        try:
            result = fix_mojibake(inp)
            if result == expected:
                print(f"✓ PASS: {desc}")
                print(f"    '{inp}' -> '{result}'")
            else:
                print(f"✗ FAIL: {desc}")
                print(f"    '{inp}' -> '{result}' (expected '{expected}')")
                all_passed = False
        except Exception as e:
            print(f"✗ ERROR: {desc}")
            print(f"    '{inp}' -> Exception: {e}")
            all_passed = False
        print()

    return all_passed

def test_clean_integration():
    """Test that the clean function properly handles mojibake."""
    print("=== Testing clean function integration ===")

    # Import clean function
    from clean_jobs import clean

    test_cases = [
        # (input, expected_output, description)
        (None, "", "None input"),
        ("", "", "Empty string"),
        ("   MÃ¼nchen   ", "München", "Mojibake with whitespace"),
        ("  GlÃ¼ckstein  ", "Glückstein", "Glückstein with whitespace"),
        ("WeiÃes", "Weißes", "Weißes mojibake"),
        ("Normal text", "Normal text", "Already correct text"),
        ("null", "", "null keyword"),
        ("N/A", "", "N/A keyword"),
    ]

    all_passed = True
    for inp, expected, desc in test_cases:
        try:
            result = clean(inp)
            if result == expected:
                print(f"✓ PASS: {desc}")
                print(f"    {repr(inp)} -> {repr(result)}")
            else:
                print(f"✗ FAIL: {desc}")
                print(f"    {repr(inp)} -> {repr(result)} (expected {repr(expected)})")
                all_passed = False
        except Exception as e:
            print(f"✗ ERROR: {desc}")
            print(f"    {repr(inp)} -> Exception: {e}")
            all_passed = False
        print()

    return all_passed

def main():
    """Run all verification tests."""
    print("Verifying mojibake fix with actual data samples...\n")

    test1_passed = test_actual_mojibake()
    test2_passed = test_clean_integration()

    print("=" * 60)
    if test1_passed and test2_passed:
        print("🎉 ALL TESTS PASSED!")
        print("The mojibake fix is working correctly with actual data.")
        return 0
    else:
        print("❌ SOME TESTS FAILED!")
        print("Please review the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())