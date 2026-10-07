import sys
sys.path.insert(0, 'job_data_cleaner')
from clean_jobs import fix_mojibake, clean

def test_fix_mojibake():
    print('Testing fix_mojibake:')
    # Each tuple: (mojibake_input, expected_output)
    test_cases = [
        ('Ã¼', 'ü'),
        ('Ã¶', 'ö'),
        ('Ã', 'ß'),
        ('â€œ', '“'),
        ('â€”', '—'),
        ('Ã¤', 'ä'),
        ('Ã„', 'Ä'),
        ('normal', 'normal'),
        ('', ''),
        (None, None),  # function returns None for None input
    ]
    for inp, expected in test_cases:
        result = fix_mojibake(inp)
        if inp is None:
            ok = result is None
        else:
            ok = result == expected
        print(f'Input: {repr(inp)} -> {repr(result)} (expected: {repr(expected)}) {"OK" if ok else "FAIL"}')

def test_clean():
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
    ]
    for inp, expected in clean_tests:
        result = clean(inp)
        ok = result == expected
        print(f'Input: {repr(inp)} -> {repr(result)} (expected: {repr(expected)}) {"OK" if ok else "FAIL"}')

if __name__ == '__main__':
    test_fix_mojibake()
    test_clean()