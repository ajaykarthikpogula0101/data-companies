"""Convert Parent_Hiring.xlsx to a CSV input and profile it."""
import collections
import csv
import sys

import openpyxl

SRC = r"C:\Users\Ajay karthik pogula\Downloads\Parent_Hiring.xlsx"
OUT = r"D:\data_companies\career_links\parent_input.csv"

wb = openpyxl.load_workbook(SRC, read_only=True)
rows = list(wb.worksheets[0].iter_rows(values_only=True))
hdr = [str(h).lstrip("\ufeff") for h in rows[0]]
body = [["" if v is None else str(v).strip() for v in r] for r in rows[1:]]
body = [r for r in body if any(r)]
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(hdr)
    w.writerows(body)

dom = [r[2].lower() for r in body]
print("header", hdr)
print("rows", len(body), "blank domain", sum(1 for d in dom if not d),
      "unique domains", len(set(dom)))
print("dup DUNS", len(body) - len(set(r[0] for r in body)))
print(collections.Counter(r[3] for r in body).most_common(20))
