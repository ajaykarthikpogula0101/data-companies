"""Summarise the downloaded shard CSVs -- companies, postings, quality, attribution.

    python deploy\analyze_shards.py
    python deploy\analyze_shards.py --dir shards --out shard_report.md

Reads every *shard*.csv in the folder with the standard library only (no pandas),
streaming row by row, so a 500MB file costs no more memory than a small one.

The output has one section per shard and a combined total. The part worth reading
closely is ATTRIBUTION: the scraper reaches a company's job board through its
parent group's careers site, so a regional subsidiary can be credited with the
parent's worldwide postings. That section counts how often the posting's own
location matches the country the company is registered in.
"""

import argparse
import csv
import glob
import os
import sys
from collections import Counter, defaultdict

csv.field_size_limit(min(sys.maxsize, 10 * 1024 * 1024))

QUALITY_FIELDS = [
    "job_title", "job_location", "job_url", "posted_date", "employment_type",
    "seniority_level", "job_category", "skills", "years_of_experience_min",
    "education_type", "salary", "currency", "job_description",
]

# Words that appear in a job location for a given country. Only the countries
# that carry the input file are listed; anything else falls back to matching the
# country name itself.
COUNTRY_HINTS = {
    "usa": ("united states", "usa", ", al", ", ak", ", az", ", ar", ", ca", ", co",
            ", ct", ", de", ", fl", ", ga", ", hi", ", id", ", il", ", in", ", ia",
            ", ks", ", ky", ", la", ", me", ", md", ", ma", ", mi", ", mn", ", ms",
            ", mo", ", mt", ", ne", ", nv", ", nh", ", nj", ", nm", ", ny", ", nc",
            ", nd", ", oh", ", ok", ", or", ", pa", ", ri", ", sc", ", sd", ", tn",
            ", tx", ", ut", ", vt", ", va", ", wa", ", wv", ", wi", ", wy"),
    "united kingdom": ("united kingdom", "england", "scotland", "wales", "london"),
    "brazil": ("brazil", "brasil", "sao paulo", "são paulo", "rio de janeiro"),
    "germany": ("germany", "deutschland", "berlin", "munich", "münchen", "hamburg"),
    "india": ("india", "bengaluru", "bangalore", "mumbai", "delhi", "hyderabad",
              "chennai", "pune", "noida", "gurgaon", "gurugram"),
    "japan": ("japan", "tokyo", "osaka"),
    "hong kong": ("hong kong",),
    "china": ("china", "shanghai", "beijing", "shenzhen"),
    "south africa": ("south africa", "johannesburg", "cape town", "pretoria", "durban"),
    "canada": ("canada", "toronto", "vancouver", "montreal", "ontario"),
    "australia": ("australia", "sydney", "melbourne", "brisbane", "perth"),
}


def location_matches_country(location, country):
    """True when the posting's location plausibly sits in the company's country."""
    loc = (location or "").strip().lower()
    ctry = (country or "").strip().lower()
    if not loc or not ctry:
        return None                      # unknowable, counted separately
    for hint in COUNTRY_HINTS.get(ctry, ()):
        if hint in loc:
            return True
    if ctry in loc:
        return True
    return False


def analyse(path):
    stats = {
        "file": os.path.basename(path),
        "mb": round(os.path.getsize(path) / 1e6, 1),
        "rows": 0, "postings": 0,
        "companies": set(), "companies_with_jobs": set(),
        "sources": Counter(), "discovery": Counter(), "status": Counter(),
        "filled": Counter(),
        "per_company": Counter(),
        "loc_match": 0, "loc_mismatch": 0, "loc_unknown": 0,
        "mismatch_by_company": Counter(),
        "countries": Counter(),
        "first_seen": "", "last_seen": "",
    }

    with open(path, newline="", encoding="utf-8-sig", errors="replace") as fh:
        reader = csv.reader(fh)
        header = next(reader, None)
        if not header:
            return stats
        ix = {name: i for i, name in enumerate(header)}

        def g(row, name):
            i = ix.get(name)
            return (row[i] if i is not None and i < len(row) else "").strip()

        for row in reader:
            if not row:
                continue
            stats["rows"] += 1
            company = g(row, "company_name")
            country = g(row, "country")
            stats["companies"].add(company)
            stats["countries"][country or "(blank)"] += 1
            stats["status"][g(row, "career_page_status") or "(blank)"] += 1
            stats["discovery"][g(row, "website_discovery") or "(blank)"] += 1

            when = g(row, "scraped_at")
            if when:
                if not stats["first_seen"] or when < stats["first_seen"]:
                    stats["first_seen"] = when
                if when > stats["last_seen"]:
                    stats["last_seen"] = when

            if not g(row, "job_title"):
                continue                          # a company row with no opening

            stats["postings"] += 1
            stats["companies_with_jobs"].add(company)
            stats["per_company"][company] += 1
            src = g(row, "source")
            # the source column also carries website-resolution notes on no-job
            # rows; keep only real extraction sources
            if src and not src.startswith(("tried:", "website:")):
                stats["sources"][src] += 1
            for field in QUALITY_FIELDS:
                if g(row, field):
                    stats["filled"][field] += 1

            verdict = location_matches_country(g(row, "job_location"), country)
            if verdict is True:
                stats["loc_match"] += 1
            elif verdict is False:
                stats["loc_mismatch"] += 1
                stats["mismatch_by_company"][company] += 1
            else:
                stats["loc_unknown"] += 1
    return stats


def report(stats, out):
    p = out.append
    n_post = stats["postings"] or 1
    p("\n" + "=" * 78)
    p("%s   (%s MB)" % (stats["file"], stats["mb"]))
    p("=" * 78)
    p("  rows in file            : %d" % stats["rows"])
    p("  companies processed     : %d" % len(stats["companies"]))
    p("  companies with openings : %d  (%.1f%%)"
      % (len(stats["companies_with_jobs"]),
         100.0 * len(stats["companies_with_jobs"]) / max(1, len(stats["companies"]))))
    p("  job postings            : %d" % stats["postings"])
    p("  postings per company    : %.1f (of those that had any)"
      % (stats["postings"] / max(1, len(stats["companies_with_jobs"]))))
    if stats["first_seen"]:
        p("  scraped between         : %s  and  %s" % (stats["first_seen"], stats["last_seen"]))

    p("\n  ATTRIBUTION -- does the posting's location match the company's country?")
    p("    same country          : %6d  (%.1f%%)" % (stats["loc_match"], 100.0 * stats["loc_match"] / n_post))
    p("    different country     : %6d  (%.1f%%)" % (stats["loc_mismatch"], 100.0 * stats["loc_mismatch"] / n_post))
    p("    no location given     : %6d  (%.1f%%)" % (stats["loc_unknown"], 100.0 * stats["loc_unknown"] / n_post))
    p("    companies contributing the most out-of-country postings:")
    for name, count in stats["mismatch_by_company"].most_common(12):
        p("      %-52s %6d" % (name[:52], count))

    p("\n  top platforms:")
    for name, count in stats["sources"].most_common(12):
        p("      %-30s %6d  (%.1f%%)" % (name, count, 100.0 * count / n_post))

    p("\n  how the website was found:")
    for name, count in stats["discovery"].most_common(10):
        p("      %-30s %6d" % (name, count))

    p("\n  field completeness across the %d postings:" % stats["postings"])
    for field in QUALITY_FIELDS:
        got = stats["filled"][field]
        p("      %-26s %6d  %5.1f%%" % (field, got, 100.0 * got / n_post))

    p("\n  biggest contributors of postings:")
    for name, count in stats["per_company"].most_common(12):
        p("      %-52s %6d" % (name[:52], count))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="shards")
    ap.add_argument("--out", default="shard_report.txt")
    args = ap.parse_args()

    paths = sorted(glob.glob(os.path.join(args.dir, "*shard*.csv")))
    if not paths:
        sys.exit("no *shard*.csv files found in %s" % args.dir)

    out = []
    all_stats = []
    for path in paths:
        print("reading %s ..." % os.path.basename(path), flush=True)
        st = analyse(path)
        all_stats.append(st)
        report(st, out)

    # ---- combined ---------------------------------------------------------
    companies = set()
    with_jobs = set()
    postings = match = mismatch = unknown = 0
    sources = Counter()
    for st in all_stats:
        companies |= st["companies"]
        with_jobs |= st["companies_with_jobs"]
        postings += st["postings"]
        match += st["loc_match"]; mismatch += st["loc_mismatch"]; unknown += st["loc_unknown"]
        sources.update(st["sources"])

    out.append("\n" + "=" * 78)
    out.append("COMBINED ACROSS %d SHARD FILES" % len(all_stats))
    out.append("=" * 78)
    out.append("  companies processed     : %d of 405,210  (%.1f%%)"
               % (len(companies), 100.0 * len(companies) / 405210))
    out.append("  companies with openings : %d" % len(with_jobs))
    out.append("  job postings            : %d" % postings)
    if postings:
        out.append("  postings in the company's own country : %d  (%.1f%%)"
                   % (match, 100.0 * match / postings))
        out.append("  postings in a different country       : %d  (%.1f%%)"
                   % (mismatch, 100.0 * mismatch / postings))
        out.append("  postings with no location             : %d  (%.1f%%)"
                   % (unknown, 100.0 * unknown / postings))
    out.append("\n  platforms overall:")
    for name, count in sources.most_common(15):
        out.append("      %-30s %6d" % (name, count))

    text = "\n".join(out)
    print(text)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    print("\nwritten to %s" % args.out)


if __name__ == "__main__":
    main()
