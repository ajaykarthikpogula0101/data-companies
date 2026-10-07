import csv

# Check if any status/error messages ended up in job_location in our fixed file
file_path = r'D:\data_companies\job_data_cleaner\output\merged_vms_all_cleaned_final_fixed_correct.csv'

print('Checking for status/error messages in job_location column (fixed file):')
print('=' * 70)

# These are the status/error messages we were supposed to move to status column
status_error_patterns = [
    'Unreachable',
    'Career Page Not Found',
    'Career Page Found - Extraction Unsupported',
    'No Jobs Found',
    'Search Completed - No Verified Jobs'
]

with open(file_path, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    header = next(reader)

    job_loc_idx = header.index('job_location')

    issues_found = []
    rows_checked = 0

    for row_num, row in enumerate(reader, start=2):
        rows_checked += 1

        # Ensure row has enough columns
        while len(row) <= job_loc_idx:
            row.append('')

        job_location = row[job_loc_idx]

        # Check if job_location contains status/error patterns
        for pattern in status_error_patterns:
            if pattern in job_location:
                issues_found.append((row_num, pattern, job_location[:100]))
                break  # Only report once per row

        if rows_checked >= 50000:
            break

print('Checked {} rows'.format(rows_checked))
print('Found {} status/error messages in job_location:'.format(len(issues_found)))

if issues_found:
    print('')
    print('Issues found:')
    for i, (row_num, pattern, sample) in enumerate(issues_found):
        print('  Row {}: Found \"{}\" in job_location'.format(row_num, pattern))
        print('    Content: {}...'.format(sample))
        print('')
else:
    print('')
    print('✓ No status/error messages found in job_location column!')

# Also check the source column for the internet-company-name-search pattern
print('')
print('Checking for internet-company-name-search in source column:')
print('-' * 50)

with open(file_path, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    header = next(reader)  # Read header again

    source_idx = header.index('source')
    source_issues = []

    for row_num, row in enumerate(reader, start=2):
        rows_checked += 1

        # Ensure row has enough columns
        while len(row) <= source_idx:
            row.append('')

        source = row[source_idx]

        if 'internet-company-name-search:' in source:
            source_issues.append((row_num, source[:100]))

        if len(source_issues) >= 10:  # Limit output
            break

print('Found {} internet-company-name-search patterns in source column:'.format(len(source_issues)))
if source_issues:
    for i, (row_num, sample) in enumerate(source_issues):
        print('  Row {}: {}'.format(row_num, sample))
else:
    print('✓ No internet-company-name-search patterns found in source column!')