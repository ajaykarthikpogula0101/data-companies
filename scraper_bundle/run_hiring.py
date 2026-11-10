"""Scrape the Hiring_OCT2026 careers_Link workbook into a raw job CSV.

The client workbook's ``careers_Link`` sheet has one row per company
(ID_GLOBAL_ULTIMATE, COMPANY_NAME, Source, Tempid), where *Source* is the
company's career-page URL.  This runner scrapes every one of those pages with
the existing job_scraper pipeline and writes one CSV row per scraped posting.
The delivery export (``rescrape/export_hiring_sample.py``) then filters the
raw rows down to the C-level roles in the five target departments and writes
the client's Job_Hiring layout.

    # process everything (resumable: companies already in the CSV are skipped)
    python run_hiring.py --workers 25

    # a small slice first, to gauge throughput
    python run_hiring.py --limit 20

    # re-attempt only the companies that failed transiently
    python run_hiring.py --retry-failures

    # inspect one company without touching the output file
    python run_hiring.py --verify "A24 GROUP LIMITED"
"""
import argparse
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import openpyxl

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from job_scraper.config import OUTPUT_COLUMNS, DEFAULT_WORKERS  # noqa: E402
from job_scraper.company import process_company_details  # noqa: E402
from job_scraper.session import ScrapeSession  # noqa: E402
from job_scraper.fields import now_iso, clean_text  # noqa: E402
from job_scraper.clean_html import html_to_plain_text  # noqa: E402
from job_scraper.ascii_clean import ascii_clean  # noqa: E402
from job_scraper.detect_language import detect_language  # noqa: E402
from job_scraper.fields import extract_labeled_fields, experience_year_range  # noqa: E402
from job_scraper.pipeline import CsvWriter  # noqa: E402
from job_scraper.criteria import load_criteria_from_excel  # noqa: E402

DEFAULT_INPUT = os.path.join(ROOT, "Copy of Hiring_OCT2026_Links.xlsx")
RAW_COLUMNS = OUTPUT_COLUMNS + ["id_global_ultimate", "tempid", "duns_number"]

_RETRYABLE_STATUSES = {"Unreachable", "Career Page Not Found",
                       "Career Page Found - Extraction Unsupported", "Error"}


def _norm_header(value):
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")


def _pick_sheet(wb, preferred="careers_Link"):
    if preferred in wb.sheetnames:
        return wb[preferred]
    normalized = {_norm_header(name): name for name in wb.sheetnames}
    for key in ("career_link", "careers_link", "career_links", "links",
                "companies", "sheet1"):
        if key in normalized:
            return wb[normalized[key]]
    return wb.active


def read_careers_links(input_file, sheet="careers_Link"):
    """Rows: (id, name, source_url, tempid, duns, web_domain, country).
    Extra columns such as DUNS_NUMBER, Web Domain or COUNTRY are picked up
    by header name when present, otherwise left empty."""
    if not os.path.exists(input_file):
        raise SystemExit("Input file not found: %s" % input_file)
    try:
        wb = openpyxl.load_workbook(input_file, read_only=True)
    except Exception as exc:
        raise SystemExit(
            "Cannot open %r as an Excel workbook (%s). Use the real file path, "
            "e.g. --input \"C:\\path\\to\\Copy of Hiring_OCT2026_Links.xlsx\"."
            % (input_file, exc))
    ws = _pick_sheet(wb, sheet)
    if ws.title.lower() != sheet.lower() and _norm_header(ws.title) != "careers_link":
        print("Note: reading sheet '%s' (expected '%s')" % (ws.title, sheet))

    rows_iter = ws.iter_rows(values_only=True)
    header = [_norm_header(c) for c in next(rows_iter)]

    def find(candidates, fallback):
        for i, cell in enumerate(header):
            if cell in candidates:
                return i
        for i, cell in enumerate(header):
            for candidate in candidates:
                if candidate and candidate in cell:
                    return i
        return fallback

    id_index = find(("id_global_ultimate", "global_ultimate", "ultimate",
                     "id_company", "keyid"), 0)
    name_index = find(("company_name", "company", "name", "partyname",
                       "party_name"), 1)
    source_index = find(("source", "source_url", "career_page_url", "url",
                         "website", "career_link"), 2)
    tempid_index = find(("tempid", "temp_id", "temp_id_global"), -1)
    duns_index = find(("duns_number", "duns", "duns_id"), -1)
    domain_index = find(("web_domain", "company_domain", "domain", "website_domain"), -1)
    country_index = find(("country", "country_name", "nation", "location"), -1)

    companies = []
    for row in rows_iter:
        if not row:
            continue

        def cell(index):
            if index is None or index < 0 or index >= len(row):
                return ""
            value = row[index]
            return str(value).strip() if value is not None else ""

        name = cell(name_index)
        if not name:
            continue
        companies.append((cell(id_index), name, cell(source_index),
                          cell(tempid_index), cell(duns_index),
                          cell(domain_index), cell(country_index)))
    wb.close()
    return companies


def _company_key(row):
    return "%s|%s" % (row[1], row[2])


def load_completed(output_file):
    done = set()
    if not os.path.exists(output_file):
        return done
    import csv
    with open(output_file, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            done.add("%s|%s" % (row.get("company_name", ""),
                                row.get("website", "")))
    return done


def remove_retryable_rows(output_file):
    if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
        return 0
    import csv
    import tempfile
    directory = os.path.dirname(os.path.abspath(output_file))
    fd, temporary = tempfile.mkstemp(prefix=".retry_", suffix=".csv",
                                     dir=directory)
    removed = kept = 0
    try:
        with open(output_file, "r", encoding="utf-8-sig", newline="") as source, \
                os.fdopen(fd, "w", encoding="utf-8-sig", newline="") as destination:
            reader = csv.DictReader(source)
            fieldnames = list(reader.fieldnames or [])
            if not fieldnames:
                return 0
            writer = csv.DictWriter(destination, fieldnames=fieldnames,
                                    extrasaction="ignore")
            writer.writeheader()
            for row in reader:
                if row.get("job_status") in _RETRYABLE_STATUSES:
                    removed += 1
                    continue
                writer.writerow(row)
                kept += 1
            destination.flush()
            os.fsync(destination.fileno())
        if removed:
            os.replace(temporary, output_file)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return removed


def _job_row(name, source_url, id_global, tempid, duns, web_domain, details,
             job, status, source, scraped_at):
    raw = job.get("job_description", "")
    clean = clean_text(html_to_plain_text(raw), max_len=0)
    clean_ascii = ascii_clean(clean)
    labeled = extract_labeled_fields(clean)
    experience_text = job.get("years_of_experience", "") or \
        labeled.get("years_of_experience", "")
    derived_min, derived_max = experience_year_range(experience_text)
    job_source = job.get("source", "") or source
    structured = job_source in ("jsonld", "microdata", "hrmanager-detail")
    return {
        "company_name": name,
        "country": "",
        "website": web_domain or source_url,
        "career_page_url": details.get("career_page_url", ""),
        "career_page_status": details.get("career_page_status", ""),
        "career_page_discovery_method": details.get("career_page_discovery_method", ""),
        "resolved_website": details.get("resolved_website", ""),
        "website_discovery": details.get("website_discovery", ""),
        "job_title": job.get("job_title", ""),
        "job_category": job.get("job_category", ""),
        "job_location": job.get("job_location", ""),
        "posted_date": job.get("posted_date", ""),
        "application_deadline": job.get("application_deadline", ""),
        "closed_date": job.get("closed_date", ""),
        "job_status": job.get("job_status", "Active"),
        "extraction_status": "Job Detail Extracted",
        "extraction_confidence": job.get("extraction_confidence") or
                                ("High" if structured else "Medium"),
        "extraction_evidence": job.get("extraction_evidence") or job_source,
        "last_checked_at": job.get("last_checked_at", ""),
        "education_stream": job.get("education_stream", ""),
        "education_type": job.get("education_type", ""),
        "education_qualification": job.get("education_qualification", ""),
        "years_of_experience_min": job.get("years_of_experience_min", "") or derived_min,
        "years_of_experience_max": job.get("years_of_experience_max", "") or derived_max,
        "seniority_level": job.get("seniority_level", ""),
        "employment_type": job.get("employment_type", ""),
        "skills": job.get("skills", ""),
        "description_language": detect_language(clean),
        "job_description": clean_ascii,
        "job_description_clean": clean_ascii,
        "job_url": job.get("job_url", ""),
        "salary_disclosed": bool(job.get("salary") or job.get("min_salary")
                                 or job.get("max_salary")),
        "salary": job.get("salary", ""),
        "min_salary": job.get("min_salary", ""),
        "max_salary": job.get("max_salary", ""),
        "currency": job.get("currency", ""),
        "source": job_source,
        "scraped_at": scraped_at,
        "num_positions": int(details.get("num_positions", 1) or 0),
        "id_global_ultimate": id_global,
        "tempid": tempid,
        "duns_number": duns,
    }


def _empty_row(name, source_url, id_global, tempid, duns, web_domain, details,
               status, source, scraped_at):
    return {
        "company_name": name,
        "country": "",
        "website": web_domain or source_url,
        "career_page_url": details.get("career_page_url", ""),
        "career_page_status": details.get("career_page_status", ""),
        "career_page_discovery_method": details.get("career_page_discovery_method", ""),
        "resolved_website": details.get("resolved_website", ""),
        "website_discovery": details.get("website_discovery", ""),
        "job_status": {
            "no_jobs": "No Jobs Found",
            "unsupported": "Career Page Found - Extraction Unsupported",
            "career_not_found": "Career Page Not Found",
        }.get(status, status.replace("_", " ").title()),
        "extraction_status": {
            "no_jobs": "Explicit No-Openings Evidence",
            "unsupported": "Extraction Unsupported",
            "career_not_found": "Career Page Not Found",
            "unreachable": "Website Unreachable",
        }.get(status, "Processing Error"),
        "extraction_confidence": "High" if status == "no_jobs" else "Low",
        "extraction_evidence": source,
        "source": source,
        "scraped_at": scraped_at,
        "num_positions": int(details.get("num_positions", 0) or 0),
        "id_global_ultimate": id_global,
        "tempid": tempid,
        "duns_number": duns,
    }


def main():
    ap = argparse.ArgumentParser(description="Hiring_OCT2026 career scraper")
    ap.add_argument("--input", default=DEFAULT_INPUT, help="Input Excel file")
    ap.add_argument("--output", default=os.path.join(ROOT, "hiring_raw_jobs.csv"),
                    help="Output raw CSV")
    ap.add_argument("--limit", type=int, default=0, help="Max companies (0=all)")
    ap.add_argument("--offset", type=int, default=0, help="Skip first N companies")
    ap.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    ap.add_argument("--no-resume", action="store_true")
    ap.add_argument("--no-search", action="store_true",
                    help="Disable web-search fallbacks (faster, fewer requests)")
    ap.add_argument("--c-level-only", action="store_true",
                    help="Write only C-level postings in the five target "
                         "departments instead of every posting")
    ap.add_argument("--retry-failures", action="store_true")
    ap.add_argument("--verify", metavar="COMPANY_NAME",
                    help="Process one company and print its jobs")
    args = ap.parse_args()

    if args.verify:
        companies = read_careers_links(args.input)
        match = [c for c in companies
                 if c[1].strip().lower() == args.verify.strip().lower()]
        if not match:
            print("Company not found in careers_Link sheet.")
            return 1
        row = match[0]
        print("Processing: %s | %s" % (row[1], row[2]))
        details = process_company_details((row[1], row[2], ""),
                                          enable_search=not args.no_search)
        print("status:", details["status"], "| source:", details["source"],
              "| jobs:", len(details["jobs"]))
        print("career page:", details.get("career_page_url") or "not found",
              "| validation:", details.get("career_page_status"),
              "| method:", details.get("career_page_discovery_method") or "n/a")
        for j in details["jobs"][:30]:
            print("- %s | posted=%s | emp=%s | %s"
                  % (j.get("job_title"), j.get("posted_date"),
                     j.get("employment_type"), j.get("job_url")))
        if len(details["jobs"]) > 30:
            print("... and %d more jobs" % (len(details["jobs"]) - 30))
        return 0

    companies = read_careers_links(args.input)
    if args.offset:
        companies = companies[args.offset:]
    if args.limit:
        companies = companies[:args.limit]

    criteria = None
    if args.c_level_only:
        criteria = load_criteria_from_excel(args.input)
        print("Filtering to C-level postings in the five target departments "
              "(criteria loaded from the workbook's Columns sheet)")

    if args.retry_failures:
        removed = remove_retryable_rows(args.output)
        print("Removed %d retry-eligible rows before reprocessing" % removed)

    writer = CsvWriter(args.output, RAW_COLUMNS)
    completed = load_completed(args.output) if not args.no_resume else set()
    todo = [c for c in companies if _company_key(c) not in completed]

    print("companies: %d | to do: %d | workers: %d | search: %s"
          % (len(companies), len(todo), args.workers,
             "off" if args.no_search else "on"), flush=True)
    if not todo:
        print("Nothing to do.")
        return 0

    counters = {"processed": 0, "jobs": 0, "no_jobs": 0, "unsupported": 0,
                "career_not_found": 0, "unreachable": 0, "error": 0, "ok": 0}
    lock = threading.Lock()

    def process(row):
        id_global, name, source_url, tempid, duns, web_domain, country = row
        try:
            details = process_company_details(
                (name, source_url, ""), enable_search=not args.no_search)
            status, jobs, source = (details["status"], details["jobs"],
                                    details["source"])
        except Exception as exc:
            status, jobs, source = "error", [], str(exc)[:200]
            details = {}
        if criteria is not None:
            jobs = [j for j in jobs
                    if criteria.is_target_job(
                        j.get("job_title", ""),
                        j.get("job_description_clean", "") or
                        j.get("job_description", ""))]
        scraped_at = now_iso()
        out_rows = [_job_row(name, source_url, id_global, tempid, duns,
                             web_domain, details, j, status, source,
                             scraped_at) for j in jobs]
        if not out_rows:
            # One row per company even with no postings, so resume can skip
            # processed companies and the raw CSV doubles as a coverage log.
            out_rows.append(_empty_row(name, source_url, id_global, tempid,
                                       duns, web_domain, details, status,
                                       source, scraped_at))
        writer.write_rows(out_rows)
        with lock:
            counters["processed"] += 1
            counters[status] = counters.get(status, 0) + 1
            counters["jobs"] += len(jobs)
            p = counters["processed"]
            if p % 25 == 0 or p == len(todo):
                print("[%d/%d] ok=%d no_jobs=%d unreach=%d err=%d jobs=%d "
                      "last=%s status=%s"
                      % (p, len(todo), counters["ok"], counters["no_jobs"],
                         counters["unreachable"], counters["error"],
                         counters["jobs"], name, status), flush=True)
        return _company_key(row)

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(process, c): c for c in todo}
        try:
            for future in as_completed(futures):
                future.result()
        except KeyboardInterrupt:
            print("Interrupted; progress saved. Re-run with --no-resume to "
                  "start fresh, or default resume to continue.")
            ex.shutdown(wait=False, cancel_futures=True)
            raise

    print("Done. %s" % counters)
    print("Output written to:", args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())