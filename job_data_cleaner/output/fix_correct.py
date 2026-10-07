import csv
import sys

def fix_csv(input_path, output_path):
    # Define patterns for misplaced status messages in job_description
    job_description_patterns = [
        "Career Page Not Found",
        "Career Page Found - Extraction Unsupported",
        "No Jobs Found",
        "Unreachable",
        "Search Completed - No Verified Jobs"
    ]
    # Pattern for internet-company-name-search in source
    source_pattern = "internet-company-name-search:"

    with open(input_path, 'r', encoding='utf-8-sig') as infile:  # utf-8-sig strips BOM
        reader = csv.reader(infile)
        # Read the header
        header = next(reader)
        # Determine column indices
        try:
            status_col = header.index('status')
            job_desc_col = header.index('job_description')
            source_col = header.index('source')
        except ValueError as e:
            print(f"Error: Column not found in header: {e}")
            sys.exit(1)

        # Open output file for writing
        with open(output_path, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.writer(outfile)
            # Write header
            writer.writerow(header)

            # Process each row
            for row_num, row in enumerate(reader, start=2):  # start at line 2 (1-indexed)
                # Ensure row has at least the maximum column index we need + 1
                max_col = max(status_col, job_desc_col, source_col)
                while len(row) <= max_col:
                    row.append('')

                # Get the relevant columns
                status = row[status_col]
                job_description = row[job_desc_col]
                source = row[source_col]

                fixed = False

                # Check if job_description contains misplaced status messages
                for pattern in job_description_patterns:
                    if pattern in job_description:
                        # Found misplaced status in job_description
                        if status == '' or status == 'Validated':
                            # Status is empty or just "Validated", replace it
                            row[status_col] = job_description
                        else:
                            # Status has meaningful content, append the job_description
                            row[status_col] = f"{status}; {job_description}"
                        # Clear the job_description field
                        row[job_desc_col] = ''
                        fixed = True
                        break

                # Check if source contains internet-company-name-search pattern
                if source_pattern in source:
                    if status == '' or status == 'Validated':
                        # Status is empty or just "Validated", replace it
                        row[status_col] = source
                    else:
                        # Status has meaningful content, append the source
                        row[status_col] = f"{status}; {source}"
                    # Clear the source field
                    row[source_col] = ''
                    fixed = True

                # Write the row
                writer.writerow(row)

                # Progress indicator
                if row_num % 10000 == 0:
                    print(f"Processed {row_num} rows", file=sys.stderr)

if __name__ == "__main__":
    input_file = r"D:\data_companies\job_data_cleaner\output\merged_vms_all_cleaned_final.csv"
    output_file = r"D:\data_companies\job_data_cleaner\output\merged_vms_all_cleaned_final_fixed_correct.csv"
    fix_csv(input_file, output_file)
    print("Done.", file=sys.stderr)