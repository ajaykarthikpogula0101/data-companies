import csv
import sys

def replace_replacement_char(text):
    if isinstance(text, str):
        return text.replace('�', '')
    return text

def main(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as infile:
        reader = csv.reader(infile)
        header = next(reader)
        rows = []
        for row in reader:
            # Replace replacement char in each field
            new_row = [replace_replacement_char(field) for field in row]
            rows.append(new_row)
    with open(output_file, 'w', encoding='utf-8', newline='') as outfile:
        writer = csv.writer(outfile)
        writer.writerow(header)
        writer.writerows(rows)
    print(f'Processed {len(rows)} rows, output written to {output_file}')

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Usage: python replace_replacement.py <input_file> <output_file>')
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
