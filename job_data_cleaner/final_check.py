import csv

# Final verification - focus on the byte transformation
with open('D:/data_companies/merged_vms_all.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    orig_row = next(reader)
    orig_loc = orig_row['job_location']

with open('D:/data_companies/job_data_cleaner/output/merged_vms_all_cleaned_fixed.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    fixed_row = next(reader)
    fixed_loc = fixed_row['job_location']

orig_bytes = orig_loc.encode('utf-8')
fixed_bytes = fixed_loc.encode('utf-8')

print('MOJIBAKE FIX VERIFICATION - BYTE LEVEL')
print('=' * 50)
print()

# Check specific transformations
transformations = [
    # (original_sequence, fixed_sequence, description)
    ([0x47, 0x6c, 0xc3, 0x83, 0xc2, 0xbc], [0x47, 0x6c, 0xc3, 0xbc], "GlÃ¼ckstein -> Glückstein"),
    ([0x20, 0x4d, 0xc3, 0x83, 0xc2, 0xbc], [0x20, 0x4d, 0xc3, 0xbc], " MÃ¼nchen -> München"),
]

print('TRANSFORMATION VERIFICATION:')
print('-' * 30)
for orig_seq, fixed_seq, desc in transformations:
    # Find the sequence in original bytes
    orig_found = False
    fixed_found = False

    for i in range(len(orig_bytes) - len(orig_seq) + 1):
        if list(orig_bytes[i:i+len(orig_seq)]) == orig_seq:
            orig_found = True
            break

    for i in range(len(fixed_bytes) - len(fixed_seq) + 1):
        if list(fixed_bytes[i:i+len(fixed_seq)]) == fixed_seq:
            fixed_found = True
            break

    status = "PASS" if (orig_found and fixed_found) else "FAIL"
    print(f'{status}: {desc}')
    if orig_found:
        print(f'  Found original pattern in input')
    if fixed_found:
        print(f'  Found fixed pattern in output')
    print()

# Count mojibake patterns
import re
def count_mojibake_patterns(text):
    return len(re.findall(r'[ÃâÂ][^\s]', text))

orig_count = count_mojibake_patterns(orig_loc)
fixed_count = count_mojibake_patterns(fixed_loc)

print('MOJIBAKE PATTERN COUNT:')
print('-' * 30)
print(f'Original text: {orig_count} mojibake patterns')
print(f'Fixed text:    {fixed_count} mojibake patterns')
print(f'Improvement:   {orig_count - fixed_count} patterns removed')
print()

if fixed_count == 0:
    print('RESULT: SUCCESS! All detectable mojibake patterns have been eliminated.')
else:
    print('RESULT: Some mojibake patterns may remain - manual inspection recommended.')

# Show sample of fixed text
print()
print('SAMPLE OF FIXED TEXT:')
print('-' * 30)
print(repr(fixed_loc[:100]))