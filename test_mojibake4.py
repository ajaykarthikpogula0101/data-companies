import sys
sys.path.insert(0, 'job_data_cleaner')
from clean_jobs import fix_mojibake, clean

def mojibake(s: str) -> str:
    """Return the mojibake version of s (UTF-8 bytes decoded as latin-1)."""
    return s.encode('utf-8').decode('latin-1')

def test_fix_mojibake():
    print('Testing fix_mojibake with generated mojibake:')
    test_chars = [
        'ü', 'ö', 'ß', 'ä', 'Ä', 'Ö',  # German
        '“', '”', '—', '–',  # punctuation
        '€',  # euro sign
    ]
    for c in test_chars:
        m = mojibake(c)
        result = fix_mojibake(m)
        ok = result == c
        print(f'Char: {repr(c)} -> mojibake: {repr(m)} -> fixed: {repr(result)} {"OK" if ok else "FAIL"}')

def test_clean():
    print('\nTesting clean with mojibake:')
    test_strings = [
        ('', ''),
        ('   ', ''),
        ('none', ''),
        ('Null', ''),
        ('N/A', ''),
        ('not specified', ''),
        ('unknown', ''),
        ('  valid text  ', 'valid text'),
        (mojibake('üöß'), 'üöß'),  # mojibake sequence
        ('valid ' + mojibake('ü') + ' text', 'valid ü text'),  # mojibake in middle
    ]
    for inp, expected in test_strings:
        result = clean(inp)
        ok = result == expected
        print(f'Input: {repr(inp)} -> {repr(result)} (expected: {repr(expected)}) {"OK" if ok else "FAIL"}')

if __name__ == '__main__':
    test_fix_mojibake()
    test_clean()