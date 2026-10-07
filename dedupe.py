import duckdb
con = duckdb.connect(r"D:\data_companies\jobs.duckdb")
con.execute("SET memory_limit='3GB'")
con.execute("SET threads=4")
con.execute("SET temp_directory='D:/data_companies/duck_tmp'")
con.execute("SET preserve_insertion_order=false")

print("deduplicating ...")
con.execute("""
CREATE OR REPLACE TABLE jobs AS
SELECT * EXCLUDE (rn) FROM (
  SELECT *, row_number() OVER (
    PARTITION BY lower(trim(company_name)), lower(trim(coalesce(job_url,'')))
    ORDER BY scraped_at DESC
  ) AS rn
  FROM raw
) WHERE rn = 1
""")

KEEP = """company_name, country, website, career_page_url, career_page_status,
career_page_discovery_method, resolved_website, website_discovery, job_title,
job_category, job_location, posted_date, application_deadline, closed_date,
job_status, education_stream, education_type, education_qualification,
years_of_experience_min, years_of_experience_max, seniority_level,
employment_type, skills, job_description_clean, job_url, salary_disclosed,
salary, min_salary, max_salary, currency, source, num_positions"""

print("building final 32-column view ...")
con.execute("CREATE OR REPLACE VIEW final AS SELECT %s FROM jobs" % KEEP)

print("\n=== BEFORE / AFTER ===")
print("raw rows        :", con.execute("SELECT count(*) FROM raw").fetchone()[0])
print("after dedupe    :", con.execute("SELECT count(*) FROM jobs").fetchone()[0])
print("companies       :", con.execute("SELECT count(DISTINCT company_name) FROM jobs").fetchone()[0])
print("final columns   :", len(con.execute("SELECT * FROM final LIMIT 0").description))

print("\n=== ROW SHAPE ===")
q = """
SELECT count(*) FILTER (WHERE job_url IS NOT NULL AND job_url <> '')     AS real_postings,
       count(*) FILTER (WHERE job_url IS NULL OR job_url = '')           AS rows_no_url,
       count(DISTINCT company_name) FILTER (WHERE job_url IS NOT NULL AND job_url <> '') AS companies_with_jobs
FROM jobs
"""
r = con.execute(q).fetchone()
print("postings with url   :", r[0])
print("rows without url    :", r[1])
print("companies with jobs :", r[2])

con.close()
