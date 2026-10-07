#!/usr/bin/env python3
"""Check the raw bytes in the CSV file to see what's actually stored."""

import csv

def check_raw_bytes():
    """Check the raw bytes of specific fields in the CSV."""
    filename = r'D:\data_companies\job_data_cleaner\output\company_jobs_aligned_cleaned.csv'

    with open(filename, 'rb') as f:
        content = f.read().decode('utf-8')
        lines = content.splitlines()
        reader = csv.reader(lines)
        header = next(reader)

        # Find the indices of columns we care about
        try:
            job_location_idx = header.index('job_location')
            job_description_idx = header.index('job_description')
        except ValueError as e:
            print("Error finding column indices: {}".format(e))
            return

        print("Checking first few rows for mojibake patterns...")
        for i, row in enumerate(reader):
            if i >= 3:  # Just check first 3 rows
                break

            location = row[job_location_idx]
            description = row[job_description_idx][:200]  # First 200 chars

            print("\nRow {}:".format(i+2))
            print("  Job location: {}".format(repr(location)))
            print("  Job description (first 200 chars): {}".format(repr(description)))

            # Check for mojibake patterns
            if 'Ã¼' in location or 'Ã¼' in description:
                print("  *** FOUND MOJIBAKE PATTERN Ã¼ ***")
            if 'Ã¶' in location or 'Ã¶' in description:
                print("  *** FOUND MOJIBAKE PATTERN Ã¶ ***")
            if 'Ã' in location or 'Ã' in description:
                print("  *** FOUND MOJIBAKE PATTERN Ã ***")
            if 'â€œ' in location or 'â€œ' in description:
                print("  *** FOUND MOJIBAKE PATTERN â€œ ***")
            if 'â€”' in location or 'â€”' in description:
                print("  *** FOUND MOJIBAKE PATTERN â€” ***")

if __name__ == "__main__":
    check_raw_bytes()