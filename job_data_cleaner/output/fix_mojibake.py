import csv
import sys

def fix_mojibake(text):
    if not isinstance(text, str):
        return text
    try:
        # Try to encode as latin-1 and then decode as utf-8
        return text.encode('latin-1').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        # If it fails, return original
        return text

def main(input_file, output_file):
    with open(input_file, 'r', newline='', encoding='utf-8') as infile:
        reader = csv.reader(infile)
        # We assume the first column is an index and the rest are comma-separated fields?
        # Actually, the file seems to have: index<TAB>field1,field2,...,fieldN
        # But the reader by default splits on commas, so the first field will be "index<TAB>field1"?
        # Let's change the delimiter to tab for the first field and then comma for the rest?
        # Alternatively, we can read the line and split on the first tab.
        pass

# Instead, we'll read the file line by line and split on the first tab.
    with open(input_file, 'r', encoding='utf-8') as infile:
        lines = infile.readlines()

    if not lines:
        return

    # Process header
    header_line = lines[0].rstrip('\n')
    # Split on first tab
    parts = header_line.split('\t', 1)
    if len(parts) == 2:
        index_header, fields_header = parts
        # The fields_header is a CSV string
        # We'll parse the fields_header as CSV to get the column names? But we don't need to change the header.
        # We'll just fix the mojibake in the fields_header? The header might also have mojibake?
        # Let's fix the fields_header by splitting on commas, fixing each field, and then joining back.
        # But note: the header might have commas inside quoted strings? The header doesn't have quotes.
        # We'll use csv.reader for the fields_header.
        # However, for simplicity, we'll just fix the entire fields_header string? That might break if there are commas.
        # Instead, we'll use csv.reader to parse the fields_header, fix each field, and then write back with csv.writer.
        # We'll do the same for each data line.
        pass
    else:
        # No tab, then the whole line is CSV
        fields_header = header_line
        index_header = None

    # We'll change approach: use csv.reader with delimiter=tab? But then the rest of the fields are comma-separated?
    # Actually, the file is malformed: it uses tab to separate the index from the rest, and then commas for the rest.
    # We can read with two steps: split on tab, then parse the second part as CSV.

    # Let's do:
    # For each line:
    #   Split on the first tab -> [index, rest]
    #   If there is no tab, then index is empty and rest is the whole line.
    #   Then parse rest as CSV (with comma delimiter and quotechar='"') to get a list of fields.
    #   Fix each field in the list.
    #   Then write the index (if exists) followed by a tab and then the fixed fields as CSV.

    # We'll write the output similarly.

    output_lines = []
    for line in lines:
        line = line.rstrip('\n')
        if '\t' in line:
            index_part, rest = line.split('\t', 1)
        else:
            index_part = ''
            rest = line
        # Now parse rest as CSV
        # We'll use csv.reader on a stringio
        import io
        reader = csv.reader(io.StringIO(rest), delimiter=',', quotechar='"')
        try:
            fields = next(reader)
        except Exception as e:
            # If parsing fails, we keep the rest as a single field?
            fields = [rest]
        # Fix each field
        fixed_fields = [fix_mojibake(f) for f in fields]
        # Now write the fixed fields back as CSV string
        output_io = io.StringIO()
        writer = csv.writer(output_io, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(fixed_fields)
        fixed_rest = output_io.getvalue().rstrip('\n')
        if index_part:
            output_line = f"{index_part}\t{fixed_rest}"
        else:
            output_line = fixed_rest
        output_lines.append(output_line)

    with open(output_file, 'w', encoding='utf-8') as outfile:
        outfile.write('\n'.join(output_lines))

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python fix_mojibake.py <input_file> <output_file>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])