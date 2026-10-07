import sys
sys.path.insert(0, '/d/data_companies')
from job_data_cleaner.clean_jobs import clean

def mojibake(char):
    """Return mojibake version of a UTF-8 character."""
    return char.encode('utf-8').decode('latin-1')

# Test mojibake fixing
test_cases = [
    # (input, expected_output)
    ('', ''),
    (None, ''),
    ('   ', ''),
    ('none', ''),
    ('Null', ''),
    ('N/A', ''),
    ('not specified', ''),
    ('unknown', ''),
    ('  valid text  ', 'valid text'),  # stripped
    ('valid ü text', 'valid ü text'),      # already correct
    (mojibake('ü') + ' text', 'ü text'),   # u-umlaut mojibake
    ('valid ' + mojibake('ö'), 'valid ö'), # o-umlaut mojibake
    ('valid ' + mojibake('ß'), 'valid ß'), # sharp s mojibake
    ('valid ' + mojibake('ä'), 'valid ä'), # a-umlaut mojibake
    ('valid ' + mojibake('Ä'), 'valid Ä'), # A-umlaut mojibake
    ('valid ' + mojibake('Ö'), 'valid Ö'), # O-umlaut mojibake
    ('valid ' + mojibake('“'), 'valid “'), # left double quotation mark
    ('valid ' + mojibake('—'), 'valid —'), # em dash
    ('valid ' + mojibake('‘'), "valid ‘"), # left single quotation mark
    ('valid ' + mojibake('’'), "valid ’"), # right single quotation mark
    ('valid ' + mojibake('•'), 'valid •'), # bullet
    ('valid ' + mojibake('…'), 'valid …'), # horizontal ellipsis
    # Mixed mojibake
    (mojibake('ü') + mojibake('ö') + mojibake('ß'), 'üöß'),
    # No mojibake
    ('normal text', 'normal text'),
    ('Text with numbers 123 and symbols !@#', 'Text with numbers 123 and symbols !@#'),
]

print("Testing clean function with mojibake fixes:")
all_passed = True
for inp, expected in test_cases:
    try:
        result = clean(inp)
        passed = result == expected
        if not passed:
            all_passed = False
        print(f"{'PASS' if passed else 'FAIL'}: Input={repr(inp)} -> Output={repr(result)} (expected={repr(expected)})")
    except Exception as e:
        all_passed = False
        print(f"ERROR: Input={repr(inp)} -> Exception: {e}")

print(f"\nAll tests passed: {all_passed}")
sys.exit(0 if all_passed else 1)