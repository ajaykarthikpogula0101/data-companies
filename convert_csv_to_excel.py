import csv
import openpyxl
from openpyxl.utils import get_column_letter

# Read first 1000 rows from CSV (for smoke test)
input_csv = r'D:\data_companies\data_7.7m_405k.csv'
output_excel = r'D:\data_companies\smoke_test_input.xlsx'
sample_size = 1000

# Create workbook and worksheet
wb = openpyxl.Workbook()
ws = wb.active
ws.title = 'Companies'

# Read CSV and write to Excel
with open(input_csv, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    for row_idx, row in enumerate(reader):
        if row_idx >= sample_size:
            break
        for col_idx, value in enumerate(row, 1):
            ws.cell(row=row_idx+1, column=col_idx, value=value)

# Save the workbook
wb.save(output_excel)
print(f'Created {output_excel} with {sample_size} rows from CSV')
