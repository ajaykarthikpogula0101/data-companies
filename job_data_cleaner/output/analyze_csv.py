import csv
import sys

def analyze_csv(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        print(f"Header: {header}")
        print(f"Number of columns: {len(header)}")

        # Count total rows
        row_count = 0
        issue_count = 0

        for row in reader:
            row_count += 1

            # Check if row has the expected number of columns
            if len(row) != len(header):
                print(f"Row {row_count}: Column count mismatch. Expected {len(header)}, got {len(row)}")
                issue_count += 1
                continue

            # Check for specific problematic patterns
            status = row[4] if len(row) > 4 else ""
            job_description = row[20] if len(row) > 20 else ""  # 0-indexed, so column 21 is index 20
            education_stream = row[12] if len(row) > 12 else ""  # column 13 is index 12
            source = row[25] if len(row) > 25 else ""  # column 26 is index 25

            # Look for status-like messages in wrong columns
            if job_description and ("Career Page" in job_description or "Unreachable" in job_description or "No Jobs Found" in job_description):
                print(f"Row {row_count}: Found status-like message in job_description: '{job_description}'")
                print(f"  Status column (5): '{status}'")
                issue_count += 1

            if education_stream and ("Career Page" in education_stream or "Unreachable" in education_stream or "No Jobs Found" in education_stream):
                print(f"Row {row_count}: Found status-like message in education_stream: '{education_stream}'")
                print(f"  Status column (5): '{status}'")
                issue_count += 1

            if source and "internet-company-name-search" in source:
                print(f"Row {row_count}: Found unexpected data in source: '{source}'")
                print(f"  Status column (5): '{status}'")
                issue_count += 1

        print(f"\nTotal rows processed: {row_count}")
        print(f"Rows with issues: {issue_count}")

if __name__ == "__main__":
    csv_file = r"D:\data_companies\job_data_cleaner\output\merged_vms_all_cleaned_final.csv"
    analyze_csv(csv_file)