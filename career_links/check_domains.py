"""Run the finder on a few named rows from the input (debug helper).

    python career_links\\check_domains.py synthesisindia.com mikescarwash.com
"""
import csv
import os
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import find_career_links as fcl  # noqa: E402

fcl.browser_fetch._BROWSER_UNAVAILABLE.set()
fcl.netcache.install()
want = {d.lower() for d in sys.argv[1:]}
rows = [r for r in csv.DictReader(open(os.path.join(HERE, "parent_input.csv"), encoding="utf-8-sig"))
        if r["web_domain"].lower() in want]
finder = fcl.Finder(render=False, search=False)


def one(r):
    res = finder.find(r["COMPANY_NAME"], r["web_domain"], r["COUNTRY1"])
    return "%s | %s | %s | %s | %s" % (r["web_domain"], res["status"], res["career_page_url"],
                                       res["ats_vendor"], res["discovery_method"])


with ThreadPoolExecutor(20) as pool:
    for line in pool.map(one, rows):
        print(line)
