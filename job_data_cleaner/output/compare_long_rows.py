import csv

# Compare original vs fixed for the very long job_location rows
original_path = r'D:\data_companies\job_data_cleaner\output\merged_vms_all_cleaned_final.csv'
fixed_path = r'D:\data_companies\job_data_cleaner\output\merged_vms_all_cleaned_final_fixed_correct.csv'

# These are the rows we identified with very long job_location values
row_numbers = [284, 342, 343, 344, 345, 484, 542, 543, 544, 545]  # 1-indexed data rows

print('Comparing original vs fixed for very long job_location rows:')
print('=' * 80)

for target_row in row_numbers:
    print('')
    print('ROW {} (1-indexed including header):'.format(target_row + 1))
    print('-' * 60)

    def get_row_data(file_path, row_index):
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
            for i, row in enumerate(reader):
                if i == row_index:
                    return header, row
            return None, None

    # Convert to zero-based index for data rows (subtract 1 for header)
    data_row_index = target_row  # Because target_row is already 1-indexed for data rows

    orig_header, orig_row = get_row_data(original_path, data_row_index)
    fixed_header, fixed_row = get_row_data(fixed_path, data_row_index)

    if orig_row and fixed_row:
        # Focus on job_location and job_description columns
        try:
            job_loc_idx = orig_header.index('job_location')
            job_desc_idx = orig_header.index('job_description')
            status_idx = orig_header.index('status')

            orig_job_loc = orig_row[job_loc_idx] if job_loc_idx < len(orig_row) else ''
            orig_job_desc = orig_row[job_desc_idx] if job_desc_idx < len(orig_row) else ''
            orig_status = orig_row[status_idx] if status_idx < len(orig_row) else ''

            fixed_job_loc = fixed_row[job_loc_idx] if job_loc_idx < len(fixed_row) else ''
            fixed_job_desc = fixed_row[job_desc_idx] if job_desc_idx < len(fixed_row) else ''
            fixed_status = fixed_row[status_idx] if status_idx < len(fixed_row) else ''

            print('Job Location:')
            print('  Original: {} chars'.format(len(orig_job_loc)))
            print('  Fixed:    {} chars'.format(len(fixed_job_loc)))
            if len(orig_job_loc) != len(fixed_job_loc):
                print('  Length change: {} -> {} ({:+d})'.format(len(orig_job_loc), len(fixed_job_loc), len(fixed_job_loc) - len(orig_job_loc)))

            print('Job Description:')
            print('  Original: {} chars'.format(len(orig_job_desc)))
            print('  Fixed:    {} chars'.format(len(fixed_job_desc)))
            if len(orig_job_desc) != len(fixed_job_desc):
                print('  Length change: {} -> {} ({:+d})'.format(len(orig_job_desc), len(fixed_job_desc), len(fixed_job_desc) - len(orig_job_desc)))

            print('Status:')
            print('  Original: {} chars'.format(len(orig_status)))
            print('  Fixed:    {} chars'.format(len(fixed_status)))
            if len(orig_status) != len(fixed_status):
                print('  Length change: {} -> {} ({:+d})'.format(len(orig_status), len(fixed_status), len(fixed_status) - len(orig_status)))

            print()

            # Show samples if they're different
            if orig_job_loc != fixed_job_loc:
                print('  Job Location sample (first 150 chars):')
                print('    Original: {}'.format(orig_job_loc[:150]))
                print('    Fixed:    {}'.format(fixed_job_loc[:150]))
                print()

            if orig_job_desc != fixed_job_desc:
                print('  Job Description sample (first 150 chars):')
                print('    Original: {}'.format(orig_job_desc[:150]))
                print('    Fixed:    {}'.format(fixed_job_desc[:150]))
                print()

        except ValueError as e:
            print('  Error accessing columns: {}'.format(e))
    else:
        print('  Could not retrieve row data')
        print()