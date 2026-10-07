#!/usr/bin/env python3
"""Test the mojibake fix with real mojibaked strings from the CSV."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'job_data_cleaner'))

from clean_jobs import clean

def test_mojibake_fix():
    """Test that mojibake is properly fixed using real examples from CSV."""
    print("Testing mojibake fix with real examples from CSV data...")
    print("=" * 60)

    # Test cases based on what we actually found in the CSV
    # Format: (input_mojibaked, expected_correct, description)
    test_cases = [
        # From the CSV data we examined
        ("Wei�\x9fes Quartier", "Weißes Quartier", "Weißes Quartier mojibake"),
        ("klarheit�", "klarheit�", "This is actually the replacement char, not mojibake to fix"),

        # Let's test the actual mojibake patterns we saw in the byte analysis
        # From the debug_bytes.py output, we saw:
        # 'GroÃŸenÃ¶ffnung' -> should become 'Großenöffnung'
        # 'Wein â€“ lecker!' -> should become 'Wein – lecker!'
        # 'Preis: 10â‚¬' -> should become 'Preis: 10€'
        ('GroÃŸenÃ¶ffnung', 'Großenöffnung', 'Großenöffnung mojibake pattern'),
        ('Wein â€“ lecker!', 'Wein – lecker!', 'En dash mojibake pattern'),
        ('Preis: 10â‚¬', 'Preis: 10€', 'Euro symbol mojibake pattern'),

        # Basic German umlauts
        ('GlÃ¼ckstein', 'Glückstein', 'Glückstein basic umlaut'),
        ('MÃ¼nchen', 'München', 'München basic umlaut'),
        ('StraÃe', 'Straße', 'Straße sharp s'),
        ('KÃ¶ln', 'Köln', 'Köln umlaut'),
        ('BjÃ¶rk', 'Björk', 'Björk Swedish umlaut'),

        # Edge cases
        (None, '', 'None input'),
        ('', '', 'Empty string'),
        ('   ', '', 'Whitespace only'),
        ('none', '', 'None keyword'),
        ('N/A', '', 'N/A keyword'),
        ('not specified', '', 'not specified keyword'),
        ('unknown', '', 'unknown keyword'),

        # Whitespace around mojibake
        ('  GlÃ¼ckstein  ', 'Glückstein', 'Glückstein with whitespace'),
        ('  MÃ¼nchen  ', 'München', 'München with whitespace'),

        # Already correct strings should remain unchanged
        ('Hello World', 'Hello World', 'Already correct ASCII'),
        ('Guten Tag', 'Guten Tag', 'Already correct German'),
        ('Straße', 'Straße', 'Already correct ß'),
        ('Weißes', 'Weißes', 'Already correct Weißes'),
        ('München', 'München', 'Already correct München'),
        ('Großenöffnung', 'Großenöffnung', 'Already correct Großenöffnung'),
        ('Wein – lecker!', 'Wein – lecker!', 'Already correct en dash'),
        ('Preis: 10€', 'Preis: 10€', 'Already correct euro symbol'),
    ]

    passed = 0
    failed = 0

    for input_val, expected, description in test_cases:
        try:
            result = clean(input_val)
            if result == expected:
                print("✓ PASS: {}".format(description))
                passed += 1
            else:
                print("✗ FAIL: {}".format(description))
                print("  Input (mojibaked):    {!r}".format(input_val))
                print("  Expected (correct):   {!r}".format(expected))
                print("  Got (from clean):     {!r}".format(result))
                failed += 1
        except Exception as e:
            print("✗ ERROR: {}".format(description))
            print("  Input: {!r}".format(input_val))
            print("  Exception: {}".format(e))
            failed += 1

    print("\n" + "=" * 60)
    print("RESULTS: {} passed, {} failed".format(passed, failed))

    if failed == 0:
        print("🎉 ALL TESTS PASSED!")
        print("The mojibake fix is working correctly.")
        return True
    else:
        print("❌ {} TEST(S) FAILED!".format(failed))
        print("Please review the implementation.")
        return False

if __name__ == "__main__":
    success = test_mojibake_fix()
    sys.exit(0 if success else 1)