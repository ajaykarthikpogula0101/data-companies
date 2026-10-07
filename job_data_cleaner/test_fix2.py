import sys
sys.path.append('.')
from mojibake_fix import fix_mojibake

# Test with raw bytes to avoid console encoding issues
def test_bytes():
    # These are the actual byte sequences we see in the CSV
    # GlÃ¼ckstein in UTF-8 bytes: b'Gl\xc3\x83\xc2\xbcckstein'
    # Which should become: b'Gl\xc3\xbcckstein' (Glückstein in UTF-8)

    test_cases = [
        # (input_string, expected_output_string, description)
        ('GlÃ¼ckstein', 'Glückstein', 'umlaut u'),
        ('MÃ¼nchen', 'München', 'umlaut u'),
        ('WeiÃes', 'Weißes', 'sharp s'),
        ('KlarheitÂ bei', 'Klarheit bei', 'non-breaking space'),
        ('GeschÃ¤fts', 'Geschäfts', 'umlaut a'),
    ]

    print('Testing mojibake fix with byte analysis:')
    for input_str, expected, desc in test_cases:
        result = fix_mojibake(input_str)
        status = 'PASS' if result == expected else 'FAIL'
        print(f'{status} {desc}: {repr(input_str)} -> {repr(result)}')
        if result != expected:
            print(f'  Expected: {repr(expected)}')

        # Show byte analysis for first case
        if 'GlÃ¼ckstein' in input_str:
            print(f'  Input bytes:  {input_str.encode("utf-8")}')
            print(f'  Result bytes: {result.encode("utf-8")}')
            expected_bytes = 'Glückstein'.encode('utf-8')
            print(f'  Expected bytes: {expected_bytes}')

test_bytes()