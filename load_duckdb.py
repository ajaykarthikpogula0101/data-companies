import duckdb, time

con = duckdb.connect(r"D:\data_companies\jobs.duckdb")
con.execute("SET memory_limit='3GB'")
con.execute("SET threads=4")
con.execute("SET temp_directory='D:/data_companies/duck_tmp'")
con.execute("SET preserve_insertion_order=false")

print("loading all shard files ... (this will take a while)")
t0 = time.time()
con.execute("""
CREATE OR REPLACE TABLE raw AS
SELECT * FROM read_csv(
  'D:/data_companies/shards/*.csv',
  header = true,
  union_by_name = true,
  all_varchar = true,
  filename = true,
  sample_size = -1
)
""")
print("done in %.1f minutes" % ((time.time()-t0)/60))

print("\ntotal rows:", con.execute("SELECT count(*) FROM raw").fetchone()[0])

print("\nper shard file:")
rows = con.execute(r"""
SELECT regexp_extract(filename, '([^/\\]+)$', 1) AS shard_file,
       count(*) AS rows,
       count(DISTINCT company_name) AS companies
FROM raw GROUP BY 1 ORDER BY rows DESC
""").fetchall()
for r in rows:
    print("  %-30s %10d rows  %8d companies" % r)

con.close()
