#!/usr/bin/env python3
"""Verification script for mojibake fix in clean_jobs.py."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'job_data_cleaner'))

# Import the actual functions from clean_jobs.py
from clean_jobs import fix_mojibake, clean

def test_fix_mojibake():
    """Test the fix_mojibake function directly."""
    print("=== Testing fix_mojibake function ===")

    # Test cases with expected results
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
        ("", "", "Empty string"),
        ("normal", "normal", "No mojibake"),
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

def test_clean_function():
    """Test the clean function that integrates mojibake fixing."""
    print("=== Testing clean function ===")

    # Test cases for clean function
    test_cases = [
        # (input, expected_output, description)
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
        ("valid Ã¼ text", "valid ü text", "Mojibake in middle"),
        ("Ã¼Ã¶Ã", "üöß", "Multiple mojibake chars"),
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
    print("Verifying mojibake fix implementation...\n")

    test1_passed = test_fix_mojibake()
    test2_passed = test_clean_function()

    print("=" * 50)
    if test1_passed and test2_passed:
        print("🎉 ALL TESTS PASSED!")
        print("The mojibake fix has been successfully implemented.")
        return 0
    else:
        print("❌ SOME TESTS FAILED!")
        print("Please review the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())