import csv
import sys

input_file = sys.argv[1]
output_file = sys.argv[2]

with open(input_file, 'r', encoding='utf-8') as infile, open(output_file, 'w', encoding='utf-8', newline='') as outfile:
    reader = csv.reader(infile, delimiter='\t')
    writer = csv.writer(outfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

    for row in reader:
        if len(row) < 2:
            # Skip malformed lines
            continue
        # The second column is the CSV string
        csv_string = row[1]
        # Parse the CSV string
        data_row = list(csv.reader([csv_string], delimiter=',', quotechar='"'))[0]
        writer.writerow(data_row)