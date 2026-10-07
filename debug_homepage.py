import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from job_scraper.session import ScrapeSession
from job_scraper.urlutils import normalize_website

# Test with one company and see what happens with homepage fetch
company_name = "B2C2 LTD"
website = "www.b2c2.com"
country = "United Kingdom"

print(f"Testing homepage fetch for: {company_name}")
print(f"Website: {website}")
print(f"Country: {country}")
print("=" * 50)

# Create a session
session = ScrapeSession()

# Normalize the website
base = normalize_website(website)
print(f"Normalized base: {base}")

# Fetch homepage
print("Fetching homepage...")
resp = session.fetch(base, timeout=20)
print(f"Response object: {resp}")
if resp is not None:
    print(f"Status code: {resp.status_code}")
    if resp.status_code < 400:
        print("Homepage fetch successful!")
        homepage_url = resp.url or base
        print(f"Homepage URL: {homepage_url}")
        ctype = resp.headers.get("Content-Type", "")
        print(f"Content-Type: {ctype}")
        if "json" not in ctype.lower():
            homepage_html = resp.text
            print(f"Homepage HTML length: {len(homepage_html) if homepage_html else 0}")
            if homepage_html:
                print("First 200 chars of homepage:")
                print(homepage_html[:200])
            else:
                print("Homepage HTML is None or empty")
        else:
            print("Content is JSON, not HTML")
    else:
        print(f"Homepage fetch failed with status {resp.status_code}")
        # Try http variant
        print("Trying http:// variant...")
        http_url = "http://" + (base.split("://")[1] if "://" in base else base)
        print(f"HTTP URL: {http_url}")
        resp2 = session.fetch(http_url, timeout=15)
        print(f"HTTP Response: {resp2}")
        if resp2 is not None and resp2.status_code < 400:
            print("HTTP fallback successful!")
            homepage_url = resp2.url or http_url
            homepage_html = resp2.text
            print(f"Homepage HTML length: {len(homepage_html) if homepage_html else 0}")
        else:
            print("HTTP fallback also failed")
else:
    print("Homepage fetch returned None")

print("=" * 50)