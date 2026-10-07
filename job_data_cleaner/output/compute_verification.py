import csv
import json

input_file = "merged_vms_all_cleaned_fixed_proper.csv"
expected_columns = 27
rogue_lines = 0
column_issues = 0

with open(input_file, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    header = next(reader)
    for i, row in enumerate(reader, start=2):
        if len(row) != expected_columns:
            column_issues += 1
        # Check for replacement character
        for field in row:
            if '�' in field:
                rogue_lines += 1
                break  # only count once per line

validation_passed = (rogue_lines == 0 and column_issues == 0)
column_count_uniform = (column_issues == 0)

issues_found = []
if rogue_lines > 0:
    issues_found.append(f"Found {rogue_lines} lines with replacement characters (encoding not fully fixed)")
if column_issues > 0:
    issues_found.append(f"Found {column_issues} lines with incorrect column count")

result = {
    "rogueValuesRemaining": rogue_lines,
    "columnCountUniform": column_count_uniform,
    "validationPassed": validation_passed,
    "issuesFound": issues_found
}

print(json.dumps(result))