import duckdb
con = duckdb.connect(r"D:\data_companies\jobs.duckdb")
con.execute("SET memory_limit='3GB'")
con.execute("SET threads=4")
con.execute("SET temp_directory='D:/data_companies/duck_tmp'")

print("=== COLUMNS ===")
for i, r in enumerate(con.execute("PRAGMA table_info('raw')").fetchall(), 1):
    print("%2d. %s" % (i, r[1]))

print("\n=== TOTALS ===")
q = """
SELECT count(*) AS rows,
       count(DISTINCT company_name) AS companies,
       count(*) FILTER (WHERE job_url IS NOT NULL AND job_url <> '') AS rows_with_url,
       count(DISTINCT job_url) AS distinct_urls
FROM raw
"""
r = con.execute(q).fetchone()
print("rows           :", r[0])
print("companies      :", r[1])
print("rows with url  :", r[2])
print("distinct urls  :", r[3])
print("duplicate rows :", r[2] - r[3])

print("\n=== FIELD COMPLETENESS (% non-empty) ===")
cols = [c[1] for c in con.execute("PRAGMA table_info('raw')").fetchall()]
for c in cols:
    if c == "filename":
        continue
    pct = con.execute(
        'SELECT 100.0 * count(*) FILTER (WHERE "%s" IS NOT NULL AND "%s" <> \'\') / count(*) FROM raw' % (c, c)
    ).fetchone()[0]
    print("  %-32s %6.1f%%" % (c, pct))

con.close()
