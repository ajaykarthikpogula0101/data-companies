import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from job_scraper.session import ScrapeSession
from job_scraper.urlutils import normalize_website
from job_scraper.ats import detect_ats_in_url
from job_scraper.company import _candidate_ats
from bs4 import BeautifulSoup

# Test the _candidate_ats function directly
company_name = "B2C2 LTD"
website = "www.b2c2.com"
country = "United Kingdom"

print(f"Testing _candidate_ats function for: {company_name}")
print("=" * 50)

# Create a session
session = ScrapeSession()

# Normalize the website
base = normalize_website(website)
print(f"Normalized base: {base}")

# Fetch the known career page
career_url = "https://www.b2c2.com/join-b2c2/careers"
print(f"Fetching career page: {career_url}")

resp = session.fetch(career_url, timeout=25)
if resp is not None and resp.status_code < 400:
    career_html = resp.text
    print(f"Career page HTML length: {len(career_html) if career_html else 0}")

    if career_html:
        print("\nTesting detect_ats_in_url on career URL directly:")
        ats1, captured1 = detect_ats_in_url(career_url)
        print(f"  URL: {career_url}")
        print(f"  ATS: {ats1}, Captured: '{captured1}'")

        print("\nTesting _candidate_ats function:")
        ats2, captured2 = _candidate_ats(session, career_url, career_html)
        print(f"  URL: {career_url}")
        print(f"  ATS: {ats2}, Captured: '{captured2}'")

        # Let's also check what the embedded regex finds
        print("\nChecking embedded ATS regex match:")
        import re
        embedded_pattern = re.compile(
            r"https?://[^\"'\s<>]+(?:greenhouse\.io|lever\.co|smartrecruiters\.com|"
            r"workable\.com|teamtailor\.com|recruitee\.com|breezy\.hr|applytojob\.com|"
            r"bamboohr\.com|personio\.[a-z.]+|myworkdayjobs\.com|taleo\.net|jobvite\.com)[^\"'\s<>]*",
            re.I)
        embedded_match = embedded_pattern.search(career_html)
        if embedded_match:
            embedded_url = embedded_match.group(0)
            print(f"  Embedded URL found: {embedded_url}")
            ats3, captured3 = detect_ats_in_url(embedded_url)
            print(f"  ATS from embedded: {ats3}, Captured: '{captured3}'")
        else:
            print("  No embedded ATS URL found in HTML")

        # Let's also check if the career URL itself matches any ATS pattern
        print("\nChecking if career URL matches ATS patterns directly:")
        from job_scraper.ats import ATS_URL_PATTERNS
        for ats_name, pat in ATS_URL_PATTERNS:
            m = pat.search(career_url)
            if m:
                print(f"  Matches {ats_name} pattern: {pat.pattern}")
                print(f"    Captured: '{m.group(1) if m.groups() else ''}'")
                break
        else:
            print("  No ATS pattern matched the career URL directly")

    else:
        print("No HTML content retrieved")
else:
    print(f"Failed to fetch career page: {resp.status_code if resp else 'None'}")

print("=" * 50)