import csv

with open('D:/data_companies/medium_sample.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    # Get the first 5 rows with non-empty salary
    count = 0
    for row in reader:
        salary = row['salary']
        if salary and salary.strip():
            print(f"Row {reader.line_num}: {repr(salary)}")
            count += 1
            if count >= 10:
                break