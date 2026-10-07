"""Merge shard CSVs into one Excel workbook in the input's row order.

    python career_links\\merge_results.py
    python career_links\\merge_results.py --out D:\\Parent_Hiring_Career_Links.xlsx
"""
import argparse
import collections
import csv
import glob
import os

import openpyxl
from openpyxl.styles import Font

HERE = os.path.dirname(os.path.abspath(__file__))
COLUMNS = ["DUNS_NUMBER", "COMPANY_NAME", "web_domain", "COUNTRY1", "EMPLOYEES_TOTAL",
           "career_page_url", "ats_board_url", "ats_vendor", "status",
           "discovery_method", "resolved_website", "note", "checked_at"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=os.path.join(HERE, "parent_input.csv"))
    ap.add_argument("--shards", default=os.path.join(HERE, "career_links_shard*.csv"))
    ap.add_argument("--out", default=r"D:\Parent_Hiring_Career_Links.xlsx")
    args = ap.parse_args()

    csv.field_size_limit(10 * 1024 * 1024)
    results = {}
    for path in sorted(glob.glob(args.shards)):
        with open(path, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                results[r["DUNS_NUMBER"]] = r  # later rows (retries) win

    with open(args.input, encoding="utf-8-sig", newline="") as f:
        inputs = list(csv.DictReader(f))

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Career_Links"
    ws.append(COLUMNS)
    counts = collections.Counter()
    for row in inputs:
        r = results.get(row["DUNS_NUMBER"])
        if r is None:
            r = dict(row, status="Not Processed")
        counts[r.get("status", "")] += 1
        ws.append([r.get(c, "") for c in COLUMNS])
    for cell in ws[1]:
        cell.font = Font(bold=True)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    summary = wb.create_sheet("Summary")
    summary.append(["status", "companies", "share"])
    for status, n in counts.most_common():
        summary.append([status, n, round(100.0 * n / max(1, len(inputs)), 1)])
    summary.append(["TOTAL", len(inputs), 100.0])
    for cell in summary[1]:
        cell.font = Font(bold=True)

    wb.save(args.out)
    print("wrote %s  (%d rows)" % (args.out, len(inputs)))
    for status, n in counts.most_common():
        print("  %-30s %6d" % (status, n))


if __name__ == "__main__":
    main()
