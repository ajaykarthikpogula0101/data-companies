import sys
sys.path.insert(0, 'job_data_cleaner')
from clean_jobs import fix_mojibake, clean

# Test fix_mojibake
print('Testing fix_mojibake:')
test_cases = [
    ('Ã¼', 'ü'),
    ('Ã¶', 'ö'),
    ('Ã', 'ß'),
    ('â€œ', '"'),
    ('â€”', '—'),
    ('Ã¤', 'ä'),
    ('Ã„', 'Ä'),
    ('normal', 'normal'),
    ('', ''),
    (None, None),
]
for inp, expected in test_cases:
    result = fix_mojibake(inp)
    if inp is None:
        # The function returns None for None input
        ok = result is None
    else:
        ok = result == expected
    print(f'Input: {inp!r} -> {result!r} (expected: {expected!r}) {"OK" if ok else "FAIL"}')

# Test clean function
print('\nTesting clean:')
clean_tests = [
    (None, ''),
    ('', ''),
    ('   ', ''),
    ('none', ''),
    ('Null', ''),
    ('N/A', ''),
    ('not specified', ''),
    ('unknown', ''),
    ('  valid text  ', 'valid text'),
    ('Ã¼Ã¶Ã', 'üöß'),  # mojibake sequence
    ('valid Ã¼ text', 'valid ü text'),  # mojibake in middle
    ('', ''),
]
for inp, expected in clean_tests:
    result = clean(inp)
    ok = result == expected
    print(f'Input: {inp!r} -> {result!r} (expected: {expected!r}) {"OK" if ok else "FAIL"}')