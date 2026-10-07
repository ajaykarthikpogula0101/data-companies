import csv

# Check if any job_description content ended up in job_location in our fixed file
file_path = r'D:\data_companies\job_data_cleaner\output\merged_vms_all_cleaned_final_fixed_correct.csv'

print('Checking for job description content in job_location column (fixed file):')
print('=' * 70)

with open(file_path, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    header = next(reader)

    job_loc_idx = header.index('job_location')
    job_desc_idx = header.index('job_description')

    # Patterns that suggest job description content in wrong place
    job_desc_patterns = [
        'Job Description:',
        'Position:',
        'Role:',
        'we are looking for',
        'wir suchen',
        'deine mission',
        'deine aufgaben',
        'your responsibilities',
        'wir bieten',
        'we offer',
        'experience:',
        'qualification:',
        'education:',
        'skills:',
        'location:'
    ]

    issues_found = []
    rows_checked = 0

    for row_num, row in enumerate(reader, start=2):
        rows_checked += 1

        # Ensure row has enough columns
        while len(row) <= max(job_loc_idx, job_desc_idx):
            row.append('')

        job_location = row[job_loc_idx].lower()
        job_description = row[job_desc_idx]

        # Check if job_location contains job description indicators
        for pattern in job_desc_patterns:
            if pattern in job_location:
                issues_found.append((row_num, pattern, row[job_loc_idx][:100]))
                break

        if rows_checked >= 50000:
            break

print('Checked {} rows'.format(rows_checked))
print('Found {} issues with job description content in job_location:'.format(len(issues_found)))

if issues_found:
    print('')
    print('First 10 issues:')
    for i, (row_num, pattern, sample) in enumerate(issues_found[:10]):
        print('  Row {}: Found \"{}\" in job_location'.format(row_num, pattern))
        print('    Content: {}...'.format(sample))
        print('')
else:
    print('')
    print('✓ No job description content found in job_location column!')