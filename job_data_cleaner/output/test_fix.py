import csv
import sys

def test_fix():
    # Test with first 30 rows
    file_path = r"D:\data_companies\job_data_cleaner\output\merged_vms_all_cleaned_final.csv"

    rows = []
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows.append(header)

        # Process first 30 rows for testing
        for i, row in enumerate(reader):
            if i >= 30:  # Only process first 30 rows for testing
                break

            # Ensure row has enough columns
            while len(row) < len(header):
                row.append('')

            # Check if we have misplaced data in job_description (column index 23)
            if len(row) > 23:
                job_desc = row[23]  # job_description column
                status = row[4] if len(row) > 4 else ''  # status column

                # Define patterns that indicate misplaced status/error messages in job_description
                misplaced_patterns = [
                    'Unreachable',
                    'Career Page Not Found',
                    'Career Page Found - Extraction Unsupported',
                    'No Jobs Found',
                    'Search Completed - No Verified Jobs'
                ]

                # Check if job_description contains a misplaced pattern
                if any(pattern in job_desc for pattern in misplaced_patterns):
                    print(f"Row {i+2}: Found misplaced data in job_description: '{job_desc}'")
                    print(f"  Current status: '{status}'")

                    # If status column is empty or already contains a similar message,
                    # we might want to combine or replace
                    if not status or status == 'Validated':
                        # Move the job_description content to status column
                        row[4] = job_desc
                        # Clear the job_description column
                        row[23] = ''
                        print(f"  Moved to status, cleared job_description")
                    elif status and status != 'Validated':
                        # Both status and job_description have content - combine them intelligently
                        # For now, let's put the job_description content in status if it seems more specific
                        if job_desc not in status:
                            row[4] = f"{status}; {job_desc}"
                        row[23] = ''
                        print(f"  Combined with existing status, cleared job_description")

            rows.append(row)

    # Write the test file
    test_file_path = file_path.replace('.csv', '_test_fixed.csv')
    with open(test_file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    print(f"Test fixed CSV written to: {test_file_path}")
    return test_file_path

if __name__ == "__main__":
    test_fix()