"""Merge shard CSVs from the VMs into one file, streaming (no pandas, no RAM cliff).

    python deploy/merge_shards.py shards/*.csv -o merged_all.csv

Keeps the header from the first file, checks the others match, drops duplicate
company keys (a company appears in exactly one shard, but a re-run with a
different --shard-count could overlap), and prints row/position totals.
"""

import argparse
import csv
import glob
import os
import sys

csv.field_size_limit(min(sys.maxsize, 10 * 1024 * 1024))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", help="shard CSVs (globs are expanded)")
    ap.add_argument("-o", "--output", default="merged_all.csv")
    ap.add_argument("--key", default="",
                    help="extra dedupe column; by default rows are deduped on "
                         "(company_name, job_url), which is the real identity of "
                         "a row -- the output has ONE ROW PER JOB POSTING, so "
                         "deduping on the company alone throws away every "
                         "posting but the first.")
    args = ap.parse_args()

    paths = []
    for pattern in args.files:
        hits = sorted(glob.glob(pattern))
        paths.extend(hits or [pattern])
    paths = [p for p in paths if os.path.isfile(p)]
    if not paths:
        sys.exit("no input files")

    header = None
    key_cols = []
    seen = set()
    written = dup = skipped = 0
    positions = 0.0
    postings_seen = [0]
    counted_companies = set()
    per_file = []

    with open(args.output, "w", newline="", encoding="utf-8-sig") as out:
        writer = csv.writer(out)
        for path in paths:
            rows_here = 0
            with open(path, newline="", encoding="utf-8-sig", errors="replace") as fh:
                reader = csv.reader(fh)
                try:
                    this_header = next(reader)
                except StopIteration:
                    per_file.append((path, 0))
                    continue
                if header is None:
                    header = this_header
                    # One row per job posting: identity is the company plus the
                    # job URL. Falling back to the whole row keeps every row
                    # rather than silently dropping data.
                    wanted = ([args.key] if args.key else []) + ["company_name", "job_url"]
                    key_cols = [header.index(c) for c in wanted if c in header]
                    writer.writerow(header)
                elif this_header != header:
                    print("WARNING: header differs in %s -- mapping by name" % path)
                    if sorted(this_header) != sorted(header):
                        sys.exit("incompatible columns in %s" % path)
                pos_index = header.index("num_positions") if "num_positions" in header else -1
                remap = None
                if this_header != header:
                    order = [this_header.index(c) for c in header]
                    remap = order
                for row in reader:
                    if remap:
                        row = [row[i] if i < len(row) else "" for i in remap]
                    if key_cols:
                        key = tuple(row[i] if i < len(row) else "" for i in key_cols)
                        # A company row with no job has an empty job_url; those
                        # are never duplicates of each other across shards
                        # because a company belongs to exactly one shard.
                        if any(key) and key in seen:
                            dup += 1
                            continue
                        seen.add(key)
                    writer.writerow(row)
                    written += 1
                    rows_here += 1
                    url_index = header.index("job_url") if "job_url" in header else -1
                    if url_index >= 0 and len(row) > url_index and row[url_index].strip():
                        postings_seen[0] += 1
                    # num_positions repeats on every row of a company, so count
                    # it once per company or the total is multiplied by the
                    # number of postings.
                    comp_index = header.index("company_name") if "company_name" in header else -1
                    comp_name = row[comp_index] if comp_index >= 0 and len(row) > comp_index else ""
                    if comp_name not in counted_companies:
                        counted_companies.add(comp_name)
                        if pos_index >= 0 and len(row) > pos_index:
                            try:
                                positions += float(row[pos_index] or 0)
                            except ValueError:
                                skipped += 1
            per_file.append((path, rows_here))

    print("\nmerged -> %s" % args.output)
    for path, n in per_file:
        print("  %-50s %8d rows" % (os.path.basename(path), n))
    print("  %-50s %8d rows" % ("TOTAL", written))
    if dup:
        print("  duplicate company keys dropped: %d" % dup)
    companies = len({k[0] for k in seen}) if seen else 0
    print("  distinct companies: %d" % companies)
    print("  job postings (rows with a job_url): %d" % postings_seen[0])
    print("  positions column total (first row per company): %d" % positions)
    if skipped:
        print("  unparsable num_positions values: %d" % skipped)


if __name__ == "__main__":
    main()
