"""Filter and format the Hiring_OCT2026 scrape into the client's Job_Hiring layout.

The raw scrape produced by ``run_hiring.py`` holds every posting found on
every company's career page.  This script:

  1. keeps only the postings that are C-level (GM / MD / Chief / CEO / CTO /
     CIO / COO / Chairman / President / Owner / Partner / CFO / Founder, ...)
     AND belong to one of the five target departments (Operations,
     Procurement, Finance, IT, Purchasing) -- the exact rules live in the
     workbook's ``Columns`` sheet and are loaded from it;
  2. maps each posting onto the column layout of the client's reference file
     (see ``Samples.xlsx``).

    python rescrape/export_hiring_sample.py --scrape hiring_raw_jobs.csv ^
        --workbook "C:\\...\\Copy of Hiring_OCT2026_Links.xlsx" ^
        --out hiring_delivery.xlsx
"""
import argparse
import csv
import os
import re
import sys

import pandas as pd
import tldextract

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from job_scraper.criteria import load_criteria_from_excel  # noqa: E402
from job_scraper.fields import infer_education  # noqa: E402
from location_country import location_country  # noqa: E402

csv.field_size_limit(min(sys.maxsize, 10 * 1024 * 1024))

# A stored qualification is kept only when it reads like a complete value;
# the old extractor left many rows with a sentence cut off mid-phrase.
_COMPLETE_QUAL = re.compile(
    r"(?:required|preferred|desired|equivalent|degree|education)\s*[.!]?$",
    re.I)


def complete_qualification(value):
    value = str(value or "").strip()
    if not value:
        return ""
    if value[-1] in ".!?)]" or _COMPLETE_QUAL.search(value):
        return value
    return ""

# Header as in the client's reference output (Samples.xlsx), minus the
# duplicate "Job description new" column.
OUTPUT_COLUMNS = [
    "Total openings", "Job Title", "Posted date", "Deleted/Closed Date",
    "Education stream", "Education type", "Education Qualification",
    "Years of experience", "Seniority Level1", "Employment Type", "Skills",
    "Job description", "Country", "Job Status", "Salary_USD",
    "Salary_USD_Min", "Salary_USD_Max", "Company Name New", "Website",
    "Source URL", "Title_Department", "domain",
]

_EDU_TYPE = {
    "Bachelor": "Bachelor's Degree", "Master": "Master's Degree",
    "Doctorate": "Doctorate", "Associate Degree": "Associate Degree",
    "Diploma": "Diploma", "Certification": "Certification",
    "High School": "High School", "Vocational": "Vocational Training",
}
_EMPLOYMENT = {
    "full time": "Full Time", "full-time": "Full Time", "fulltime": "Full Time",
    "regular": "Full Time", "part time": "Part Time", "part-time": "Part Time",
    "contract": "Contract", "contractor": "Contract", "temporary": "Contract",
    "fixed term": "Contract", "internship": "Internship", "intern": "Internship",
    "apprenticeship": "Apprenticeship", "permanent": "Permanent",
    "volunteer": "OTHER", "per diem": "OTHER", "prn": "OTHER",
    "seasonal": "Contract",
}


def yyyymmdd(value):
    v = str(value or "").strip()
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", v)
    if m:
        return int(m.group(1) + m.group(2) + m.group(3))
    m = re.match(r"^(\d{8})$", v)
    if m:
        return int(m.group(1))
    return None


def years_of_experience(minimum, maximum):
    def num(x):
        try:
            x = float(str(x).strip())
            return x if x > 0 else None
        except (TypeError, ValueError):
            return None

    lo, hi = num(minimum), num(maximum)
    if lo and hi and hi >= lo:
        val = (lo + hi) / 2.0
    else:
        val = lo or hi
    if not val:
        return ""
    return ("%g Years" % val) if val != int(val) else ("%d Years" % int(val))


def usd_salary(salary, minimum, maximum, currency):
    text = str(salary or "")
    cur = str(currency or "").strip().upper()
    is_usd = cur in ("USD", "US$", "$") or (
        not cur and "$" in text
        and not re.search(r"(?:A|C|S|NZ|HK|R|MX)\$", text))

    def num(x):
        try:
            x = float(str(x).replace(",", "").strip())
            return x if x > 0 else None
        except (TypeError, ValueError):
            return None

    lo, hi = num(minimum), num(maximum)
    if not is_usd or not (lo or hi):
        return "", None, None
    lo = lo or hi
    hi = hi or lo
    fmt = lambda v: ("%d" % v) if v == int(v) else ("%.2f" % v)
    return "$%s - $%s" % (fmt(lo), fmt(hi)), lo, hi


def employment_type(value):
    v = str(value or "").strip()
    if not v:
        return ""
    key = v.lower()
    for k, label in _EMPLOYMENT.items():
        if k in key:
            return label
    return v[:40]


def total_openings(value):
    """Total positions scraped for the company, as reported by the board."""
    try:
        n = int(float(value))
    except (TypeError, ValueError):
        return ""
    return str(n) if n > 0 else ""


def domain_of(website):
    try:
        ext = tldextract.extract(website or "")
        if ext.domain and ext.suffix:
            return "%s.%s" % (ext.domain, ext.suffix)
    except Exception:
        pass
    return ""


_NOT_OWNER = re.compile(
    r"\b(?:process|product|service|data|risk|system|application|platform|"
    r"feature|epic|story|control|capability|workflow|business\s+process|"
    r"technical|solution)\s+owner\b", re.I)


def seniority_level(title):
    """Seniority label for any title (used by the all-jobs workbook)."""
    t = _NOT_OWNER.sub(" ", (title or "").lower())
    if re.search(r"\bchief\b|\b(ceo|cfo|coo|cto|cio|cmo|chro|ciso|cro|cpo|"
                 r"cdo)\b|\bpresident\b|\bfounder\b|\bowner\b|\bproprietor\b",
                 t) and not re.search(r"\bvice[\s-]?president\b", t):
        return "C-Level"
    if re.search(r"\bvice\s+president\b|\bvp\b|\bsvp\b|\bevp\b|\bavp\b", t):
        return "V-Level"
    if re.search(r"\bdirector\b|\bmanaging\s+director\b|\bmanaging\s+partner\b", t):
        return "D-Level"
    if re.search(r"\bhead\s+of\b|\bhead\b|\bgeneral\s+manager\b", t):
        return "H-Level"
    if re.search(r"\bsenior\s+manager\b|\bprincipal\b|\bpartner\b|"
                 r"\bsr\.?\s+manager\b", t):
        return "M-Level"
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scrape", required=True, help="raw CSV from run_hiring.py")
    ap.add_argument("--workbook", required=True,
                    help="Copy of Hiring_OCT2026_Links.xlsx (for the Columns sheet)")
    ap.add_argument("--out", default=os.path.join(ROOT, "hiring_delivery.xlsx"),
                    help="output Excel path (C-level postings only)")
    ap.add_argument("--all-out", default="",
                    help="optional Excel with EVERY scraped posting "
                         "(same layout, unfiltered)")
    ap.add_argument("--csv-out", default="",
                    help="optional CSV copy of the delivered rows")
    ap.add_argument("--all-csv-out", default="",
                    help="optional CSV copy of EVERY scraped posting")
    ap.add_argument("--desc-max", type=int, default=0,
                    help="truncate Job description to N characters "
                         "(0 = no truncation, the default)")
    ap.add_argument("--include-desc", action="store_true",
                    help="match the department via the description as well "
                         "as the title")
    args = ap.parse_args()

    criteria = load_criteria_from_excel(args.workbook)
    raw = pd.read_csv(args.scrape, dtype=str, keep_default_na=False,
                      engine="python")
    if raw.empty:
        print("No rows in %s" % args.scrape)
        return 1

    jobs = raw[raw["job_title"].str.strip() != ""].copy()
    print("raw postings: %d across %d companies"
          % (len(jobs), jobs["company_name"].nunique()))

    all_rows = []
    kept = []
    dropped = {"not_senior": 0, "not_target_department": 0}
    for r in jobs.itertuples(index=False):
        d = r._asdict()
        title = d.get("job_title", "")
        description = d.get("job_description_clean", "") or ""
        seniority = criteria.seniority_label(title)
        is_senior = bool(seniority)

        loc = d.get("job_location", "")
        country = location_country(loc)
        sal_text, sal_lo, sal_hi = usd_salary(
            d.get("salary"), d.get("min_salary"), d.get("max_salary"),
            d.get("currency"))
        desc = str(description)
        if args.desc_max and args.desc_max > 0:
            desc = desc[:args.desc_max]
        # Re-derive the education qualification from the full description:
        # the scraper's old extractor truncated it at 90 characters.
        _, _, derived_qual = infer_education(str(description))
        qualification = derived_qual or complete_qualification(
            d.get("education_qualification", ""))
        website = d.get("resolved_website", "") or d.get("website", "")
        row = {
            "Total openings": total_openings(d.get("num_positions")),
            "Job Title": title.strip(),
            "Posted date": yyyymmdd(d.get("posted_date")),
            "Deleted/Closed Date": yyyymmdd(d.get("closed_date")),
            "Education stream": d.get("education_stream", ""),
            "Education type": _EDU_TYPE.get(d.get("education_type", ""),
                                            d.get("education_type", "")),
            "Education Qualification": qualification,
            "Years of experience": years_of_experience(
                d.get("years_of_experience_min"),
                d.get("years_of_experience_max")),
            "Seniority Level1": seniority or seniority_level(title),
            "Employment Type": employment_type(d.get("employment_type")),
            "Skills": d.get("skills", ""),
            "Job description": desc,
            "Country": country,
            "Job Status": d.get("job_status", "Active") or "Active",
            "Salary_USD": sal_text,
            "Salary_USD_Min": sal_lo,
            "Salary_USD_Max": sal_hi,
            "Company Name New": d.get("company_name", ""),
            "Website": website,
            "Source URL": d.get("job_url", ""),
            "Title_Department": seniority.replace("-", " ") if is_senior
                                else "",
            "domain": domain_of(website),
        }
        all_rows.append(row)
        if not is_senior:
            dropped["not_senior"] += 1
            continue
        department = criteria.classify_department(
            title, description if args.include_desc else "")
        if not department:
            dropped["not_target_department"] += 1
            continue
        kept.append(row)

    out = pd.DataFrame(kept, columns=OUTPUT_COLUMNS)
    out = out.sort_values(["Company Name New", "Job Title"]).reset_index(drop=True)
    print("C-level postings in the five target departments: %d across %d companies"
          % (len(out), out["Company Name New"].nunique()))
    print("dropped: %s" % dropped)

    with pd.ExcelWriter(args.out, engine="openpyxl") as xw:
        out.to_excel(xw, sheet_name="Job_Hiring", index=False)
        summary = pd.DataFrame(
            [("Raw postings scraped", len(jobs)),
             ("C-level postings, five target departments", len(out)),
             ("C-level postings in other departments / not target", dropped["not_target_department"]),
             ("Postings below C/V/D level", dropped["not_senior"]),
             ("Companies with delivered postings", out["Company Name New"].nunique())],
            columns=["Metric", "Value"])
        summary.to_excel(xw, sheet_name="Summary", index=False)
    print("wrote", args.out)

    if args.all_out:
        all_out = pd.DataFrame(all_rows, columns=OUTPUT_COLUMNS)
        all_out = all_out.sort_values(["Company Name New", "Job Title"]) \
                         .reset_index(drop=True)
        with pd.ExcelWriter(args.all_out, engine="openpyxl") as xw:
            all_out.to_excel(xw, sheet_name="All_Jobs", index=False)
            summary = pd.DataFrame(
                [("All postings scraped", len(all_out)),
                 ("Companies with postings", all_out["Company Name New"].nunique()),
                 ("C-level postings (all departments)", int(
                     (all_out["Title_Department"] == "C Level").sum())),
                 ("C-level postings, five target departments", len(out))],
                columns=["Metric", "Value"])
            summary.to_excel(xw, sheet_name="Summary", index=False)
        print("wrote", args.all_out)

    if args.csv_out:
        out.to_csv(args.csv_out, index=False, encoding="utf-8-sig")
        print("wrote", args.csv_out)

    if args.all_csv_out and args.all_out:
        all_out = pd.DataFrame(all_rows, columns=OUTPUT_COLUMNS)
        all_out = all_out.sort_values(["Company Name New", "Job Title"]) \
                         .reset_index(drop=True)
        all_out.to_csv(args.all_csv_out, index=False, encoding="utf-8-sig")
        print("wrote", args.all_csv_out)
    return 0


if __name__ == "__main__":
    sys.exit(main())