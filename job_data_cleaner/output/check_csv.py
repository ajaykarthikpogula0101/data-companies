import csv

with open('5k records.csv', 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    for i, row in enumerate(reader):
        if i < 10:
            print(f"Line {i}: {len(row)} fields")
            # Print first field and last field to see
            if len(row) > 0:
                print(f"  First: {row[0][:50]}")
                print(f"  Last: {row[-1][:50]}")
        else:
            break