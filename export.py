import duckdb, time
con = duckdb.connect(r"D:\data_companies\jobs.duckdb")
con.execute("SET memory_limit='3GB'")
con.execute("SET threads=4")
con.execute("SET temp_directory='D:/data_companies/duck_tmp'")

# ---- 1. FULL final table ----
print("exporting full final table ...")
t0 = time.time()
con.execute("""
COPY (SELECT * FROM final)
TO 'D:/data_companies/final_all_records.csv' (HEADER, DELIMITER ',', QUOTE '"')
""")
print("  done in %.1f min" % ((time.time()-t0)/60))

# ---- 2. Criteria-filtered file (matched_any_senior logic) ----
print("exporting criteria-filtered file ...")
t0 = time.time()
con.execute(r"""
COPY (
  SELECT * FROM final
  WHERE job_url IS NOT NULL AND job_url <> ''
    AND job_title IS NOT NULL AND job_title <> ''
    AND (
      -- C-suite / owner
      regexp_matches(job_title, '(?i)\b(ceo|cfo|coo|cto|cio|cmo|chro|ciso|cro|cpo|cdo)\b|(?i)\bchief\s+[a-z]+(\s+[a-z]+)?\s+officer\b|(?i)\b(president|founder|co-founder|owner|proprietor|managing\s+director|managing\s+partner)\b')
      -- Director / VP / Head-of
      OR regexp_matches(job_title, '(?i)\b(director|vice\s+president|vp|svp|evp|avp|head\s+of|general\s+manager)\b')
      -- senior finance
      OR (regexp_matches(job_title, '(?i)\b(financ[a-z]*|account[a-z]*|controller|treasur[a-z]*|audit[a-z]*|tax|bookkeep[a-z]*|payroll|fp&a)\b')
          AND regexp_matches(job_title, '(?i)\b(chief|director|vice\s+president|vp|svp|evp|avp|head\s+of|general\s+manager|senior\s+manager|principal|partner)\b'))
      -- senior operations
      OR (regexp_matches(job_title, '(?i)\b(operations?|operational|ops)\b')
          AND regexp_matches(job_title, '(?i)\b(chief|director|vice\s+president|vp|svp|evp|avp|head\s+of|general\s+manager|senior\s+manager|principal|partner)\b'))
      -- senior procurement
      OR (regexp_matches(job_title, '(?i)\b(procurement|purchas[a-z]*|sourcing|supply\s+chain|buyer|vendor\s+manage[a-z]*|category\s+manager)\b')
          AND regexp_matches(job_title, '(?i)\b(chief|director|vice\s+president|vp|svp|evp|avp|head\s+of|general\s+manager|senior\s+manager|principal|partner)\b'))
      -- chief-level IT only
      OR regexp_matches(job_title, '(?i)\b(cto|cio|ciso|cdo)\b|(?i)\bchief\s+(technolog[a-z]*|information|digital|data|technical|security|innovation|product|ai|analytics)\s+(and\s+[a-z]+\s+)?officer\b')
    )
)
TO 'D:/data_companies/final_criteria_leadership.csv' (HEADER, DELIMITER ',', QUOTE '"')
""")
print("  done in %.1f min" % ((time.time()-t0)/60))

# ---- row counts ----
full = con.execute("SELECT count(*) FROM final").fetchone()[0]
crit = con.execute("SELECT count(*) FROM read_csv('D:/data_companies/final_criteria_leadership.csv', header=true, all_varchar=true)").fetchone()[0]
print("\nfull records     :", full)
print("criteria records :", crit)
con.close()
