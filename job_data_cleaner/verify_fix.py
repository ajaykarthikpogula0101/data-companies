import csv
import re

print('=== COMPARISON: ORIGINAL vs FIXED ===')
print()

# Check original data (first few rows)
with open('D:/data_companies/merged_vms_all.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    orig_row = next(reader)
    orig_loc = orig_row['job_location']

# Check fixed data
with open('D:/data_companies/job_data_cleaner/output/merged_vms_all_cleaned_fixed.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    fixed_row = next(reader)
    fixed_loc = fixed_row['job_location']

print('ORIGINAL (has mojibake):')
print('Location:', repr(orig_loc))
print('Bytes:', orig_loc.encode('utf-8'))
print()

print('FIXED (mojibake repaired):')
print('Location:', repr(fixed_loc))
print('Bytes:', fixed_loc.encode('utf-8'))
print()

# Show the key differences
print('KEY CORRECTIONS:')
# Check for specific mojibake patterns in original and their fixes
corrections = [
    ('GlÃ¼ckstein', 'Glückstein'),
    ('MÃ¼nchen', 'München'),
    ('WeiÃes', 'Weißes'),
    ('TheresienhÃ¶he', 'Theresienhöhe')
]

for orig_pattern, fixed_pattern in corrections:
    if orig_pattern in orig_loc:
        # Check if the fixed version has the proper UTF-8 for the fixed pattern
        try:
            fixed_decoded = fixed_loc.encode('utf-8').decode('utf-8')
            if fixed_pattern in fixed_decoded:
                print(f'PASS: {orig_pattern} -> {fixed_pattern}')
            else:
                print(f'FAIL: {orig_pattern} -> expected {fixed_pattern} not found')
        except:
            # Byte comparison approach
            orig_bytes = orig_pattern.encode('utf-8')
            # The fixed pattern in UTF-8 bytes
            if fixed_pattern == 'Glückstein':
                fixed_bytes = b'Gl\xc3\xbcckstein'
            elif fixed_pattern == 'München':
                fixed_bytes = b'M\xc3\xbcnchen'
            elif fixed_pattern == 'Weißes':
                fixed_bytes = b'Wei\xc3\x9fes'
            elif fixed_pattern == 'Theresienhöhe':
                fixed_bytes = b'Theresienh\xc3\xb6he'

            if fixed_bytes in fixed_loc.encode('utf-8'):
                print(f'PASS: {orig_pattern} -> {fixed_pattern}')
            else:
                print(f'FAIL: {orig_pattern} -> expected {fixed_pattern} bytes not found')

# Verify no mojibake remains in fixed version
orig_mojibake = len(re.findall(r'[ÃâÂ][^\s]', orig_loc))
fixed_mojibake = len(re.findall(r'[ÃâÂ][^\s]', fixed_loc))
print()
print(f'Original mojibake patterns: {orig_mojibake}')
print(f'Fixed mojibake patterns: {fixed_mojibake}')
print(f'Improvement: {orig_mojibake - fixed_mojibake} patterns fixed')

if fixed_mojibake == 0:
    print('SUCCESS: No mojibake patterns remain in fixed output!')
else:
    print('WARNING: Some mojibake patterns may remain')