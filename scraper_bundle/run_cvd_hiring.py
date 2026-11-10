"""Fresh C/V/D-level delivery scrape for Hiring_new_9k_12-10-2026.xlsx.

Scrapes every company's career page, keeps only postings that are C-Level,
V-Level or D-Level AND belong to one of the five target departments
(Operations, Procurement, Finance, IT, Purchasing), translates non-English
titles/descriptions/skills to English with Argos Translate (offline models),
and writes one row per posting in the hiring_CVD_delivery layout.

    python run_cvd_hiring.py --input Hiring_new_9k_12-10-2026.xlsx ^
        --output hiring_new9k_CVD_delivery.csv --workers 25
"""
import argparse
import csv
import logging
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# JOB_SCRAPER_DISABLE_RENDER=1 turns off Camoufox rendering entirely.
# Rendered pages go through the synchronous browser queue, and on a run with
# many 403/JS-shell sites that queue backs up to ~15 min per page -- far past
# the company budget.  With rendering off those pages fail fast and the run
# keeps moving.
if os.environ.get("JOB_SCRAPER_DISABLE_RENDER", "") == "1":
    from job_scraper import browser_fetch
    browser_fetch._BROWSER_UNAVAILABLE.set()
    browser_fetch._BROWSER_UNAVAILABLE_REASON[:] = [
        "disabled by JOB_SCRAPER_DISABLE_RENDER=1"]

from job_scraper.ascii_clean import ascii_clean  # noqa: E402

from job_scraper.config import (  # noqa: E402
    DEFAULT_WORKERS, JOB_DETAIL_TIMEOUT, OUTPUT_COLUMNS,
)
from job_scraper.company import process_company_details  # noqa: E402
from job_scraper.clean_html import html_to_plain_text  # noqa: E402
from job_scraper.criteria import Criteria  # noqa: E402
from job_scraper.detect_language import detect_language  # noqa: E402
from job_scraper.fields import (  # noqa: E402
    clean_text, enrich_job, infer_education, now_iso,
    extract_labeled_fields, experience_year_range,
)
from job_scraper.session import ScrapeSession  # noqa: E402
from job_scraper.pipeline import _job_url_is_owned  # noqa: E402
from job_scraper.translate import translate_text  # noqa: E402
from job_scraper.urlutils import english_locale_url  # noqa: E402
from rescrape.export_hiring_sample import (  # noqa: E402
    complete_qualification, domain_of, employment_type, total_openings,
    usd_salary, years_of_experience, yyyymmdd, _EDU_TYPE,
)
from rescrape.location_country import location_country  # noqa: E402
from run_hiring import read_careers_links  # noqa: E402

DELIVERY_COLUMNS = [
    "Total openings", "Job Title", "Posted date", "Deleted/Closed Date",
    "Education stream", "Education type", "Education Qualification",
    "Years of experience", "Seniority Level1", "Employment Type", "Skills",
    "Job description", "Country", "Job Status", "Salary_USD",
    "Salary_USD_Min", "Salary_USD_Max", "Company Name New", "Website",
    "Source URL", "Title_Department", "Department", "domain",
]

# Full raw scraper columns are kept alongside the delivery layout so the
# output carries every field the scraper extracts, not just the posting URL.
RAW_COLUMNS = OUTPUT_COLUMNS + ["id_global_ultimate", "tempid", "duns_number"]
ALL_COLUMNS = DELIVERY_COLUMNS + RAW_COLUMNS

# Argos handles ~800 chars/sec per worker, and translation is serialised
# across workers by a process lock.  Capping the translated portion keeps one
# pathological 30k-char description from stalling the run; the remainder is
# appended verbatim.
TRANSLATE_DESC_MAX = 20000

# Seconds spent fetching missing Workday descriptions for one company, at
# most, before the posting ships with the description it already has.
WORKDAY_BACKFILL_BUDGET = 60

criteria = Criteria()


def _delivery_row(row, details, job, seniority, out_title, out_desc,
                  out_skills, department):
    name, source_url, web_domain = row[1], row[2], row[5]
    num_positions = int(details.get("num_positions", 1) or 0)
    website = details.get("resolved_website", "") or web_domain or source_url
    loc = job.get("job_location", "")
    sal_text, sal_lo, sal_hi = usd_salary(
        job.get("salary"), job.get("min_salary"), job.get("max_salary"),
        job.get("currency"))
    _, _, derived_qual = infer_education(str(out_desc))
    qualification = derived_qual or complete_qualification(
        job.get("education_qualification", ""))
    raw_desc = clean_text(html_to_plain_text(
        job.get("job_description", "")), max_len=0)
    raw_desc_ascii = ascii_clean(raw_desc)
    labeled = extract_labeled_fields(raw_desc)
    experience_text = job.get("years_of_experience", "") or \
        labeled.get("years_of_experience", "")
    derived_min, derived_max = experience_year_range(experience_text)
    job_source = job.get("source", "") or ""
    structured = job_source in ("jsonld", "microdata", "hrmanager-detail")
    return {
        "Total openings": total_openings(num_positions),
        "Job Title": (out_title or "").strip(),
        "Posted date": yyyymmdd(job.get("posted_date")),
        "Deleted/Closed Date": yyyymmdd(job.get("closed_date")),
        "Education stream": job.get("education_stream", ""),
        "Education type": _EDU_TYPE.get(job.get("education_type", ""),
                                        job.get("education_type", "")),
        "Education Qualification": qualification,
        "Years of experience": years_of_experience(
            job.get("years_of_experience_min"),
            job.get("years_of_experience_max")),
        "Seniority Level1": seniority,
        "Employment Type": employment_type(job.get("employment_type")),
        "Skills": out_skills or "",
        "Job description": ascii_clean(out_desc) or "",
        "Country": location_country(loc),
        "Job Status": job.get("job_status", "Active") or "Active",
        "Salary_USD": sal_text,
        "Salary_USD_Min": sal_lo,
        "Salary_USD_Max": sal_hi,
        "Company Name New": name,
        "Website": website,
        "Source URL": job.get("job_url", ""),
        "Title_Department": seniority.replace("-", " "),
        "Department": department,
        "domain": domain_of(website),
        # Full raw scraper fields.
        "company_name": name,
        "country": row[6] if len(row) > 6 else "",
        "website": website,
        "career_page_url": details.get("career_page_url", ""),
        "career_page_status": details.get("career_page_status", ""),
        "career_page_discovery_method": details.get(
            "career_page_discovery_method", ""),
        "resolved_website": details.get("resolved_website", ""),
        "website_discovery": details.get("website_discovery", ""),
        "job_title": job.get("job_title", ""),
        "job_category": job.get("job_category", ""),
        "job_location": loc,
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
        "years_of_experience_min": job.get(
            "years_of_experience_min", "") or derived_min,
        "years_of_experience_max": job.get(
            "years_of_experience_max", "") or derived_max,
        "seniority_level": job.get("seniority_level", ""),
        "employment_type": job.get("employment_type", ""),
        "skills": job.get("skills", ""),
        "description_language": detect_language(raw_desc),
        "job_description": raw_desc_ascii,
        "job_description_clean": raw_desc_ascii,
        "job_url": job.get("job_url", ""),
        "salary_disclosed": bool(job.get("salary") or job.get("min_salary")
                                 or job.get("max_salary")),
        "salary": job.get("salary", ""),
        "min_salary": job.get("min_salary", ""),
        "max_salary": job.get("max_salary", ""),
        "currency": job.get("currency", ""),
        "source": job_source,
        "scraped_at": now_iso(),
        "num_positions": num_positions,
        "id_global_ultimate": row[0] if len(row) > 0 else "",
        "tempid": row[3] if len(row) > 3 else "",
        "duns_number": row[4] if len(row) > 4 else "",
    }


def _translate_desc(text, lang):
    text = str(text or "")
    if not text:
        return text
    head = translate_text(text[:TRANSLATE_DESC_MAX], lang)
    if len(text) > TRANSLATE_DESC_MAX:
        return head + text[TRANSLATE_DESC_MAX:]
    return head


def _fetch_workday_description(session, job):
    """Fetch the missing full description of a Workday posting.

    The listing API never carries descriptions; the parser enriches up to
    MAX_ATS_DETAIL_ENRICH postings per board (leadership first), so a C/V/D
    posting past that budget would ship with an empty description.  The job
    URL is now https://{host}/{site}/job/... and the detail JSON lives at
    {host}/wday/cxs/{tenant}/{site}{path-after-site}.
    """
    from urllib.parse import urlparse
    url = (job.get("job_url") or "").strip()
    if "myworkdayjobs" not in url:
        return job
    try:
        parsed = urlparse(url)
        host = "%s://%s" % (parsed.scheme or "https", parsed.netloc)
        match = re.match(r"^([a-z0-9\-_]+)\.wd\d+\.myworkdayjobs\.com$",
                         (parsed.netloc or "").lower())
        if not match:
            return job
        tenant = match.group(1)
        segments = [s for s in parsed.path.split("/") if s]
        locale = re.match(r"^[a-z]{2}([-_][A-Za-z]{2})?$", segments[0]) \
            if segments else None
        if locale:
            segments = segments[1:]
        if not segments:
            return job
        site, rest = segments[0], "/" + "/".join(segments[1:])
        detail_url = "%s/wday/cxs/%s/%s%s" % (host, tenant, site, rest)
        detail = session.fetch_json(detail_url, timeout=JOB_DETAIL_TIMEOUT)
        if isinstance(detail, dict):
            posting = detail.get("jobPostingInfo") or detail.get("jobPosting") or {}
            description = posting.get("jobDescription") or posting.get("description")
            if description and not job.get("job_description"):
                job["job_description"] = description
            if not job.get("job_location"):
                primary = posting.get("location")
                if isinstance(primary, dict):
                    job["job_location"] = " ".join(
                        str(primary.get(k, "")) for k in
                        ("city", "subdivision", "countryDescriptor")
                        if primary.get(k)).strip()
    except Exception as exc:
        logging.getLogger("job_scraper").debug(
            "workday detail backfill failed for %s: %s", url, str(exc)[:120])
    return job


def process_company(row, enable_search=True, one_per_level=False,
                    one_per_department=False, one_per_level_company=False):
    name, source_url = row[1], row[2]
    country = row[6] if len(row) > 6 else ""
    session = ScrapeSession()

    def scrape(url):
        try:
            details = process_company_details((name, url, country),
                                              session=session,
                                              enable_search=enable_search)
            return (details["status"], details["jobs"], details["source"],
                    details)
        except Exception as exc:
            return ("error", [], str(exc)[:200], {})

    # Sites that serve locale paths (de/, fr/, ja/, ...) usually have an
    # English sibling (/en/) - scraping that directly costs nothing and saves
    # a translation pass afterwards.  Only the leading locale segment is
    # rewritten, and the original URL is retried whenever the English variant
    # yields nothing.
    en_url = english_locale_url(source_url)
    if en_url and en_url != source_url:
        status, jobs, source, details = scrape(en_url)
        if not jobs:
            status, jobs, source, details = scrape(source_url)
    else:
        status, jobs, source, details = scrape(source_url)

    qualified = []
    for job in jobs:
        # Never attach a posting from an unrelated organisation, even when a
        # search/domain fallback produced it.  Rejected jobs are dropped before
        # the one-per-level dedupe so they cannot occupy a valid slot.
        if not _job_url_is_owned(
                job.get("job_url", ""),
                details.get("resolved_website") or row[5] or row[2],
                name):
            continue
        raw = job.get("job_description", "")
        clean_desc = clean_text(html_to_plain_text(raw), max_len=0)
        enrich_job(job, clean_desc)
        clean_desc = clean_text(html_to_plain_text(
            job.get("job_description", "")), max_len=0)
        lang = (detect_language(clean_desc) or "").strip().lower()
        is_en = lang in ("", "en", "en-us", "en-gb")
        title = (job.get("job_title") or "").strip()
        # Seniority and department rules are English; non-English titles are
        # translated first so e.g. "Finanzdirektor" is not silently dropped.
        if is_en:
            work_title, work_desc = title, clean_desc
        else:
            work_title = translate_text(title, lang)
            work_desc = None  # translate only once the posting qualifies
        seniority = criteria.seniority_label(work_title)
        if not seniority:
            continue
        department = criteria.classify_department(work_title, "")
        if not department:
            continue
        qualified.append((job, lang, is_en, work_title, work_desc, seniority,
                          department))

    # One posting per department x seniority level: e.g. IT keeps at most one
    # C-Level, one V-Level, one D-Level and one H-Level row per company.
    if one_per_level:
        deduped = {}
        for item in qualified:
            key = (item[6], item[5])
            if key not in deduped:
                deduped[key] = item
        qualified = list(deduped.values())

    # One posting per department per company, keeping the most senior role
    # (C > V > H > D).  --one-per-level keeps one per department x level
    # instead, which can produce up to four rows for the same department.
    if one_per_department:
        rank = {"C-Level": 4, "V-Level": 3, "H-Level": 2, "D-Level": 1}
        best = {}
        for item in qualified:
            department, seniority = item[6], item[5]
            if department not in best or \
                    rank.get(seniority, 0) > rank.get(best[department][0], 0):
                best[department] = (seniority, item)
        qualified = [value[1] for value in best.values()]

    # One posting per seniority level per company (at most one C, one V,
    # one D and one H), regardless of department.
    if one_per_level_company:
        deduped = {}
        for item in qualified:
            deduped.setdefault(item[5], item)
        qualified = list(deduped.values())

    # Full descriptions for qualifying postings the parser's detail budget
    # did not reach.  Bounded per company so a slow/hung board cannot stall
    # the worker: stop after WORKDAY_BACKFILL_BUDGET seconds and move on.
    missing = [job for job, *_ in qualified
               if not (job.get("job_description") or "").strip()
               and "myworkdayjobs" in (job.get("job_url") or "")]
    if missing:
        deadline = time.time() + WORKDAY_BACKFILL_BUDGET
        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = [pool.submit(_fetch_workday_description, session, job)
                       for job in missing]
            try:
                for future in as_completed(futures):
                    if time.time() > deadline:
                        break
                    future.result()
            except Exception:
                pass

    out_rows = []
    for job, lang, is_en, work_title, work_desc, seniority, department in qualified:
        clean_desc = clean_text(html_to_plain_text(
            job.get("job_description", "")), max_len=0)
        if not is_en:
            if work_desc is None:
                work_desc = _translate_desc(clean_desc, lang)
            out_skills = translate_text(job.get("skills", ""), lang)
        else:
            work_desc, out_skills = clean_desc, job.get("skills", "")
        out_rows.append(_delivery_row(row, details, job, seniority,
                                      work_title, work_desc, out_skills,
                                      department))
    return name, source_url, status, out_rows


class ProgressLog:
    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        self.done = set()
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as handle:
                for line in handle:
                    self.done.add(line.strip())

    def mark(self, key):
        with self.lock:
            self.done.add(key)
            with open(self.path, "a", encoding="utf-8") as handle:
                handle.write(key + "\n")

    def contains(self, key):
        return key in self.done


def main():
    ap = argparse.ArgumentParser(description="C/V/D-level delivery scraper")
    ap.add_argument("--input", required=True, help="Input Excel workbook")
    ap.add_argument("--output",
                    default=os.path.join(ROOT, "hiring_new9k_CVD_delivery.csv"),
                    help="Output CSV in the hiring_CVD_delivery layout")
    ap.add_argument("--limit", type=int, default=0, help="Max companies (0=all)")
    ap.add_argument("--offset", type=int, default=0, help="Skip first N companies")
    ap.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    ap.add_argument("--no-resume", action="store_true")
    ap.add_argument("--no-search", action="store_true",
                    help="Disable web-search fallbacks (faster, fewer requests)")
    ap.add_argument("--one-per-level", action="store_true",
                    help="Keep at most ONE posting per department x seniority "
                         "level per company (e.g. IT/C-Level, IT/V-Level ...)")
    ap.add_argument("--one-per-department", action="store_true",
                    help="Keep at most ONE posting per department per company, "
                         "choosing the most senior (C > V > H > D)")
    ap.add_argument("--one-per-level-company", action="store_true",
                    help="Keep at most ONE posting per seniority level "
                         "(C, V, H, D) per company, across all departments")
    ap.add_argument("--names", metavar="FILE",
                    help="Process only companies whose names are listed in "
                         "FILE (one per line), in that order")
    ap.add_argument("--verify", metavar="COMPANY_NAME",
                    help="Process one company and print qualifying postings")
    args = ap.parse_args()

    companies = read_careers_links(args.input)
    if args.names:
        with open(args.names, "r", encoding="utf-8-sig") as handle:
            wanted = [line.strip() for line in handle if line.strip()]
        wanted_lower = [w.lower() for w in wanted]
        companies = [c for c in companies
                     if (c[1] or "").strip().lower() in wanted_lower]
        print("--names: %d wanted, %d matched"
              % (len(wanted), len(companies)), flush=True)
    if args.offset:
        companies = companies[args.offset:]
    if args.limit:
        companies = companies[:args.limit]
    print("companies: %d | workers: %d" % (len(companies), args.workers),
          flush=True)

    def key(row):
        return "%s|%s" % (row[1], row[2])

    if args.verify:
        match = [c for c in companies
                 if c[1].strip().lower() == args.verify.strip().lower()]
        if not match:
            print("Company not found.")
            return 1
        name, source_url, status, rows = process_company(
            match[0], enable_search=not args.no_search,
            one_per_level=args.one_per_level,
            one_per_department=args.one_per_department,
            one_per_level_company=args.one_per_level_company)
        print("status: %s | qualifying postings: %d" % (status, len(rows)))
        for r in rows:
            print("- %s | %s | %s | %s"
                  % (r["Job Title"], r["Title_Department"], r["Country"],
                     r["Source URL"]))
        return 0

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
    print("existing delivery rows: %d (dedup keys loaded)"
          % len(seen_urls), flush=True)
    # An existing file already carries its header; never append a second one.
    if os.path.exists(args.output) and os.path.getsize(args.output) > 0:
        header_written[0] = True

    def writer_guard():
        if not header_written[0]:
            header_written[0] = True
            with open(args.output, "a", encoding="utf-8-sig", newline="") as fh:
                csv_writer = csv.DictWriter(fh, fieldnames=ALL_COLUMNS)
                csv_writer.writeheader()

    def process(row):
        name, source_url, status, rows = process_company(
            row, enable_search=not args.no_search,
            one_per_level=args.one_per_level,
            one_per_department=args.one_per_department,
            one_per_level_company=args.one_per_level_company)
        writer_guard()
        with lock:
            written = 0
            with open(args.output, "a", encoding="utf-8-sig", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=ALL_COLUMNS,
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