import duckdb
con = duckdb.connect(r"D:\data_companies\jobs.duckdb")
con.execute("""
CREATE OR REPLACE TABLE criteria AS
SELECT * FROM read_csv(
  'D:/data_companies/final/final_criteria_leadership.csv',
  header = true, all_varchar = true, sample_size = -1
)
""")
print("rows:", con.execute("SELECT count(*) FROM criteria").fetchone()[0])
con.close()
