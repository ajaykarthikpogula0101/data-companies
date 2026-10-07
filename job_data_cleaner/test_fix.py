import sys
sys.path.append('.')
from mojibake_fix import fix_mojibake

# Test cases
test_cases = [
    ('GlÃ¼ckstein', 'Glückstein'),
    ('MÃ¼nchen', 'München'),
    ('WeiÃes', 'Weißes'),
    ('KlarheitÂ bei', 'Klarheit bei'),  # Non-breaking space
    ('GeschÃ¤fts', 'Geschäfts'),
    ('RMÃ–', 'RMÖ'),  # This might not fix correctly but let's see
    ('Quartier', 'Quartier'),  # Should remain unchanged
    ('normal text', 'normal text'),  # Should remain unchanged
]
print('Testing mojibake fix:')
for input_str, expected in test_cases:
    result = fix_mojibake(input_str)
    status = 'PASS' if result == expected else 'FAIL'
    print(f'{status} {repr(input_str)} -> {repr(result)} (expected: {repr(expected)})')