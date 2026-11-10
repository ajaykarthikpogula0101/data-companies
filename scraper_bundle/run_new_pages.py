"""C/V/D-level delivery scrape for new_pages.xlsx (DUNS + Web Domain only).

Reads new_pages.xlsx (columns: DUNS_NUMBER, Web Domain), derives a display
name from the registrable domain, scrapes each company website (career page
discovery happens inside the scraper), keeps only C/V/D-level postings in the
five target departments (Operations, Procurement, Finance, IT, Purchasing),
and writes at most ONE job per department per company in the
hiring_CVD_delivery layout, with English translation of non-English content.

    python run_new_pages.py --output hiring_new_pages_CVD_delivery.csv
"""
import argparse
import csv
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import openpyxl  # noqa: E402

from job_scraper.config import DEFAULT_WORKERS  # noqa: E402
from run_cvd_hiring import (  # noqa: E402
    DELIVERY_COLUMNS, ProgressLog, process_company,
)

INPUT_FILE = os.path.join(ROOT, "new_pages.xlsx")
OUTPUT_FILE = os.path.join(ROOT, "hiring_new_pages_CVD_delivery.csv")


def _sld_labels(domain):
    labels = [label for label in domain.lower().split(".") if label]
    if labels and labels[0] == "www":
        labels = labels[1:]
    if len(labels) > 2:
        labels = labels[-2:]
    return labels


TLD_STOPWORDS = {
    "com", "co", "net", "org", "biz", "info", "io", "us", "uk", "de",
    "fr", "es", "it", "nl", "br", "ca", "au", "in", "jp", "cn", "mx",
    "ru", "za", "se", "ch", "at", "be", "dk", "fi", "no", "pl", "pt",
    "ie", "nz", "sg", "my", "ph", "th", "id", "vn", "ae", "sa", "il",
    "group", "holdings", "holding", "inc", "ltd", "llc", "gmbh", "ag",
    "sa", "corp", "corp.", "company", "co.",
}


def _title_word(word):
    if re.search(r"\d", word):
        return word.upper()
    return word[:1].upper() + word[1:]


def derive_name(domain):
    labels = _sld_labels(domain)
    if labels and labels[0] == "www":
        labels = labels[1:]
    raw = " ".join(w for w in labels if w not in TLD_STOPWORDS)
    words = re.split(r"[^a-z0-9]+", raw)
    words = [w for w in words if w and w not in TLD_STOPWORDS]
    if not words:
        return domain
    name = " ".join(_title_word(w) for w in words)
    return name


def load_companies(input_file):
    wb = openpyxl.load_workbook(input_file, read_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    header = [str(h).strip().lower() if h is not None else "" for h in rows[0]]
    duns_i = next((i for i, h in enumerate(header) if "duns" in h), 0)
    dom_i = next((i for i, h in enumerate(header) if "web" in h or "domain" in h), 1)
    name_i = next((i for i, h in enumerate(header)
                   if "company" in h or h in ("name", "party_name")), -1)

    companies = []
    for row in rows[1:]:
        if not row or not row[dom_i]:
            continue
        domain = str(row[dom_i]).strip()
        if not domain:
            continue
        duns = str(row[duns_i]).strip() if row[duns_i] is not None else ""
        name = ""
        if name_i >= 0 and name_i < len(row) and row[name_i]:
            name = str(row[name_i]).strip()
        if not name:
            name = derive_name(domain)
        companies.append((duns, name, "https://" + domain, "", duns, domain))
    return companies


SENIORITY_RANK = {"c": 4, "v": 3, "h": 2, "d": 1}


def pick_best_per_department(rows):
    best = {}
    for r in rows:
        dept = (r.get("Department") or "").strip()
        title = (r.get("Title_Department") or "").strip().lower()
        rank = SENIORITY_RANK.get(title[:1], 0)
        if dept not in best or rank > best[dept][0]:
            best[dept] = (rank, r)
    return [v[1] for v in best.values()]


def main():
    ap = argparse.ArgumentParser(description="C/V/D delivery for new_pages.xlsx")
    ap.add_argument("--input", default=INPUT_FILE, help="Input Excel workbook")
    ap.add_argument("--output", default=OUTPUT_FILE, help="Output CSV")
    ap.add_argument("--limit", type=int, default=0, help="Max companies (0=all)")
    ap.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    ap.add_argument("--no-resume", action="store_true")
    ap.add_argument("--no-search", action="store_true")
    args = ap.parse_args()

    companies = load_companies(args.input)
    if args.limit:
        companies = companies[:args.limit]
    print("companies: %d | workers: %d" % (len(companies), args.workers),
          flush=True)

    def key(row):
        return "%s|%s" % (row[1], row[2])

    progress = ProgressLog(args.output + ".progress")
    todo = [c for c in companies if args.no_resume or not progress.contains(key(c))]
    print("to do: %d (skipping %d already done)"
          % (len(todo), len(companies) - len(todo)), flush=True)
    if not todo:
        print("Nothing to do.")
        return 0

    counters = {"processed": 0, "rows": 0, "ok": 0, "no_jobs": 0,
                "unreachable": 0, "career_not_found": 0, "error": 0}
    lock = threading.Lock()
    header_written = [False]
    seen_urls = set()
    if os.path.exists(args.output):
        try:
            with open(args.output, "r", encoding="utf-8-sig", newline="") as fh:
                for rec in csv.DictReader(fh):
                    url = (rec.get("Source URL") or "").strip()
                    if url:
                        seen_urls.add(url)
        except Exception:
            seen_urls = set()
    print("existing delivery rows: %d (dedup keys loaded)" % len(seen_urls),
          flush=True)
    if os.path.exists(args.output) and os.path.getsize(args.output) > 0:
        header_written[0] = True

    def writer_guard():
        if not header_written[0]:
            header_written[0] = True
            with open(args.output, "a", encoding="utf-8-sig", newline="") as fh:
                csv_writer = csv.DictWriter(fh, fieldnames=DELIVERY_COLUMNS)
                csv_writer.writeheader()

    def process(row):
        name, source_url, status, rows = process_company(
            row, enable_search=not args.no_search)
        rows = pick_best_per_department(rows)
        writer_guard()
        with lock:
            written = 0
            with open(args.output, "a", encoding="utf-8-sig", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=DELIVERY_COLUMNS,
                                        extrasaction="ignore")
                for r in rows:
                    url = (r.get("Source URL") or "").strip()
                    if url in seen_urls:
                        continue
                    writer.writerow(r)
                    if url:
                        seen_urls.add(url)
                    written += 1
            counters["processed"] += 1
            counters[status] = counters.get(status, 0) + 1
            counters["rows"] += written
            p = counters["processed"]
            if p % 25 == 0 or p == len(todo):
                print("[%d/%d] rows=%d ok=%d no_jobs=%d unreach=%d err=%d "
                      "last=%s status=%s"
                      % (p, len(todo), counters["rows"], counters["ok"],
                         counters["no_jobs"], counters["unreachable"],
                         counters["error"], name, status), flush=True)
        progress.mark(key(row))
        return key(row)

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(process, c): c for c in todo}
        try:
            for future in as_completed(futures):
                future.result()
        except KeyboardInterrupt:
            print("Interrupted; progress saved. Re-run to continue.")
            ex.shutdown(wait=False, cancel_futures=True)
            raise

    print("Done. %s" % counters)
    print("Output written to:", args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())