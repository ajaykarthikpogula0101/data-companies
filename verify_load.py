import duckdb, csv, glob, os, sys
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

con = duckdb.connect(r"D:\data_companies\jobs.duckdb")
db = dict(con.execute(r"""
  SELECT regexp_extract(filename, '([^/\\]+)$', 1), count(*)
  FROM raw GROUP BY 1
""").fetchall())

print("%-30s %12s %12s %s" % ("file", "in_csv", "in_duckdb", "match"))
ok = True
for path in sorted(glob.glob(r"D:\data_companies\shards\*.csv")):
    name = os.path.basename(path)
    with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
        n = sum(1 for _ in csv.reader(f)) - 1   # minus header
    d = db.get(name, 0)
    same = (n == d)
    ok = ok and same
    print("%-30s %12d %12d %s" % (name, n, d, "OK" if same else "*** MISMATCH ***"))

print("\nALL FILES MATCH" if ok else "\nSOME FILES DO NOT MATCH -- do not proceed")
con.close()
