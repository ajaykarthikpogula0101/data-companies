import sys
sys.path.insert(0, 'job_data_cleaner')
from clean_jobs import fix_mojibake

def test_case(mojibake, expected):
    result = fix_mojibake(mojibake)
    print(f'Input: {repr(mojibake)}')
    print(f'  Result: {repr(result)}')
    print(f'  Expected: {repr(expected)}')
    print(f'  OK: {result == expected}')
    # Also show code points
    if result is not None and expected is not None:
        print(f'  Result code points: {[hex(ord(c)) for c in result]}')
        print(f'  Expected code points: {[hex(ord(c)) for c in expected]}')
    print()

# Test cases
print('Testing fix_mojibake:')
test_case('Ã¼', 'ü')
test_case('Ã¶', 'ö')
test_case('Ã', 'ß')
test_case('â€œ', '“')
test_case('â€”', '—')
test_case('Ã¤', 'ä')
test_case('Ã„', 'Ä')
test_case('normal', 'normal')
test_case('', '')
test_case(None, None)