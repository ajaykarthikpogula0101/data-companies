import csv
import sys
import io

def fix_mojibake(text):
    if not isinstance(text, str):
        return text
    try:
        return text.encode('windows-1252').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text

def main(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as infile, \
         open(output_file, 'w', encoding='utf-8', newline='') as outfile:
        for line in infile:
            line = line.rstrip('\n')
            if '\t' in line:
                index_part, rest = line.split('\t', 1)
            else:
                index_part = ''
                rest = line
            # Parse rest as CSV
            reader = csv.reader(io.StringIO(rest), delimiter=',', quotechar='"')
            try:
                fields = next(reader)
            except Exception as e:
                fields = [rest]
            # Fix each field
            fixed_fields = [fix_mojibake(f) for f in fields]
            # Write the fixed fields as CSV string
            output_io = io.StringIO()
            writer = csv.writer(output_io, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(fixed_fields)
            fixed_rest = output_io.getvalue().rstrip('\n')
            if index_part:
                outfile.write(f'{index_part}\t{fixed_rest}\n')
            else:
                outfile.write(f'{fixed_rest}\n')

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Usage: python fix_win1252_stream.py <input_file> <output_file>')
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
