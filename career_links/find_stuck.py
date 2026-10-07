"""List shard rows not yet written (debug helper)."""
import csv
import sys
import zlib

shard, count, offset, limit, out = (int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]),
                                    int(sys.argv[4]), sys.argv[5])
rows = list(csv.DictReader(open(r"D:\data_companies\career_links\parent_input.csv",
                                encoding="utf-8-sig")))[offset:offset + limit]
rows = [r for r in rows if zlib.crc32(r["web_domain"].strip().lower().encode()) % count == shard]
done = {r["DUNS_NUMBER"] for r in csv.DictReader(open(out, encoding="utf-8"))}
print(" ".join(r["web_domain"] for r in rows if r["DUNS_NUMBER"] not in done))
