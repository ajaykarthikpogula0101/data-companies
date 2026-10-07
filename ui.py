import duckdb
con = duckdb.connect(r"D:\data_companies\jobs.duckdb")
con.execute("INSTALL ui")
con.execute("LOAD ui")
con.execute("CALL start_ui()")
print("DuckDB UI running at http://localhost:4213")
input("keep this window open. press Enter here to shut the UI down.\n")
con.close()
