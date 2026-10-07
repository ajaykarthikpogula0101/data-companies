"""Print career-ish links on a homepage (debug helper)."""
import re
import sys

from curl_cffi import requests as cr
from bs4 import BeautifulSoup

for dom in sys.argv[1:]:
    try:
        r = cr.get("https://" + dom, impersonate="chrome", timeout=20, verify=False)
    except Exception as e:
        print(dom, "ERR", str(e)[:80])
        continue
    soup = BeautifulSoup(r.text, "html.parser")
    anchors = soup.find_all("a", href=True)
    print("==", dom, r.status_code, r.url, "len", len(r.text), "anchors", len(anchors),
          "scripts", len(soup.find_all("script")))
    for a in anchors:
        t = " ".join(a.get_text(" ", strip=True).split())[:40]
        h = a["href"]
        if re.search(r"job|career|karri|stell|jobb|trabaj|emple|recru|vacan|join|work|"
                     r"employ|arbeid|ledig|opport|talent|hiring|people", t + " " + h, re.I):
            print("   ", repr(t), h[:120])
