#!/usr/bin/env python3
"""
Verification script to check that the fix worked correctly.
Verifies that no rogue values remain in job_description and source columns.
"""

import csv
import sys

def verify_fixed_csv(file_path):
    # Define the patterns that should NOT appear in job_description or source columns
    bad_job_desc_patterns = [
        'Unreachable',
        'Career Page Not Found',
        'Career Page Found - Extraction Unsupported',
        'No Jobs Found',
        'Search Completed - No Verified Jobs'
    ]
    bad_source_pattern = 'internet-company-name-search:'

    issues_found = []
    rows_processed = 0

    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)

        # Get column indices
        try:
            status_col = header.index('status')
            job_desc_col = header.index('job_description')
            source_col = header.index('source')
        except ValueError as e:
            print(f"Error: Could not find required column: {e}")
            return False

        print(f"Column indices - status: {status_col}, job_description: {job_desc_col}, source: {source_col}")

        # Check each row
        for row_num, row in enumerate(reader, start=2):  # start at line 2 (1-indexed)
            rows_processed += 1

            # Ensure row has enough columns
            while len(row) <= max(status_col, job_desc_col, source_col):
                row.append('')

            job_desc = row[job_desc_col]
            source = row[source_col]

            # Check job_description for bad patterns
            for pattern in bad_job_desc_patterns:
                if pattern in job_desc:
                    issues_found.append(f"Line {row_num}: Found '{pattern}' in job_description column")
                    break  # Only report once per row

            # Check source for bad pattern
            if bad_source_pattern in source:
                issues_found.append(f"Line {row_num}: Found '{bad_source_pattern}' in source column")

    print(f"\nProcessed {rows_processed} data rows")

    if issues_found:
        print(f"Found {len(issues_found)} issues:")
        for issue in issues_found[:10]:  # Show first 10 issues
            print(f"  {issue}")
        if len(issues_found) > 10:
            print(f"  ... and {len(issues_found) - 10} more issues")
        return False
    else:
        print("✓ SUCCESS: No rogue values found in job_description or source columns!")
        return True

if __name__ == "__main__":
    csv_file = r"D:\data_companies\job_data_cleaner\output\merged_vms_all_cleaned_final_fixed_correct.csv"
    success = verify_fixed_csv(csv_file)
    sys.exit(0 if success else 1)