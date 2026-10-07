import csv

# Simple verification - just check the bytes
with open('D:/data_companies/merged_vms_all.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    orig_row = next(reader)
    orig_loc = orig_row['job_location']

with open('D:/data_companies/job_data_cleaner/output/merged_vms_all_cleaned_fixed.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    fixed_row = next(reader)
    fixed_loc = fixed_row['job_location']

print('=== MOJIBAKE FIX VERIFICATION ===')
print()
print('Checking first job location field:')
print()
print('ORIGINAL bytes:')
print(orig_loc.encode('utf-8'))
print()
print('FIXED bytes:')
print(fixed_loc.encode('utf-8'))
print()
print('BYTE-BYTE COMPARISON FOR KEY SEQUENCES:')
print()

# Look for the specific sequences that indicate mojibake vs fixed
orig_bytes = orig_loc.encode('utf-8')
fixed_bytes = fixed_loc.encode('utf-8')

# Let's just show the relevant sections and let humans verify
print('1. Checking GlÃ¼ckstein -> Glückstein transformation:')
# Look for the sequence: Gl c3 83 c2 bc (mojibake) should become Gl c3 bc (fixed)
print('   Original around "Gl":')
gl_idx = orig_bytes.find(b'Gl')
if gl_idx != -1:
    print('      ', [f'0x{b:02x}' for b in orig_bytes[gl_idx:gl_idx+10]])
print('   Fixed around "Gl":')
gl_idx_fixed = fixed_bytes.find(b'Gl')
if gl_idx_fixed != -1:
    print('      ', [f'0x{b:02x}' for b in fixed_bytes[gl_idx_fixed:gl_idx_fixed+10]])
print('   Expected fixed: Gl c3 bc ckstein -> 47 6c c3 bc 63 6b 73 74 65 69 6e')
print()

print('2. Checking MÃ¼nchen -> München transformation:')
print('   Original around " M":')
m_idx = orig_bytes.find(b' M')  # Space then M
if m_idx != -1:
    print('      ', [f'0x{b:02x}' for b in orig_bytes[m_idx:m_idx+10]])
print('   Fixed around " M":')
m_idx_fixed = fixed_bytes.find(b' M')
if m_idx_fixed != -1:
    print('      ', [f'0x{b:02x}' for b in fixed_bytes[m_idx_fixed:m_idx_fixed+10]])
print('   Expected fixed: 20 4d c34 4d c3 bc 6e 63 68 65 6e -> " München"')
print()

print('3. Checking WeiÃes -> Weißes transformation:')
print('   Original around "Wei":')
wei_idx = orig_bytes.find(b'Wei')
if wei_idx != -1:
    print('      ', [f'0x{b:02x}' for b in orig_bytes[wei_idx:wei_idx+10]])
print('   Fixed around "Wei":')
wei_idx_fixed = fixed_bytes.find(b'Wei')
if wei_idx_fixed != -1:
    print('      ', [f'0x{b:02x}' for b in fixed_bytes[wei_idx_fixed:wei_idx_fixed+10]])
print('   Expected fixed: 57 65 69 c3 9f 65 73 -> "Weißes"')
print()

# Count potential mojibake markers
import re
orig_mojibake = len(re.findall(r'[ÃâÂ][^\s]', orig_loc))
fixed_mojibake = len(re.findall(r'[ÃâÂ][^\s]', fixed_loc))
print('4. Mojibake pattern count:')
print(f'   Original: {orig_mojibake} patterns of [ÃâÂ][^\\s]')
print(f'   Fixed:    {fixed_mojibake} patterns of [ÃâÂ][^\\s]')
print(f'   Improvement: {orig_mojibake - fixed_mojibake} patterns removed')
print()

if fixed_mojibake == 0:
    print('RESULT: SUCCESS! All mojibake patterns have been fixed.')
else:
    print('RESULT: Some mojibake patterns may remain.')