import csv
import sys

input_file = "merged_vms_all_cleaned_fixed_proper.csv"
expected_columns = 27
issues = []

with open(input_file, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    header = next(reader)  # skip header
    for i, row in enumerate(reader, start=2):  # line numbers start at 2 (header is line 1)
        if len(row) != expected_columns:
            issues.append(f"Line {i}: Expected {expected_columns} columns, found {len(row)}")
        # Check for replacement character in any field
        for field in row:
            if '�' in field:
                issues.append(f"Line {i}: Found replacement character (�) in field: {field[:100]}...")
                break  # only report once per line
        # Optionally, check for other mojibake patterns?
        # But we trust the cleaning report that encoding artifacts fixed.
        if i % 100000 == 0:
            print(f"Processed {i} lines...")

if issues:
    print("Issues found:")
    for issue in issues[:10]:  # limit output
        print(issue)
    if len(issues) > 10:
        print(f"... and {len(issues) - 10} more issues.")
    sys.exit(1)
else:
    print(f"All checks passed. Processed {i} lines.")
    sys.exit(0)