import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from job_scraper.session import ScrapeSession
from job_scraper.urlutils import normalize_website, hostname
from job_scraper.ats import find_career_links, common_career_urls
from job_scraper.config import MAX_CAREER_LINKS
from bs4 import BeautifulSoup

# Test with one company and see what happens with career page detection
company_name = "B2C2 LTD"
website = "www.b2c2.com"
country = "United Kingdom"

print(f"Testing career page detection for: {company_name}")
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
homepage_html = None
homepage_url = base

if resp is not None and resp.status_code < 400:
    homepage_url = resp.url or base
    print(f"Homepage URL: {homepage_url}")
    ctype = resp.headers.get("Content-Type", "")
    print(f"Content-Type: {ctype}")
    if "json" not in ctype.lower():
        homepage_html = resp.text
        print(f"Homepage HTML length: {len(homepage_html) if homepage_html else 0}")
    else:
        print("Content is JSON, not HTML")
elif resp is None:
    # try http:// variant
    print("Trying http:// variant...")
    http_url = "http://" + (base.split("://")[1] if "://" in base else base)
    print(f"HTTP URL: {http_url}")
    resp2 = session.fetch(http_url, timeout=15)
    if resp2 is not None and resp2.status_code < 400:
        print("HTTP fallback successful!")
        homepage_url = resp2.url or http_url
        homepage_html = resp2.text
        print(f"Homepage HTML length: {len(homepage_html) if homepage_html else 0}")
    else:
        print("HTTP fallback also failed")
else:
    print(f"Homepage fetch failed with status {resp.status_code}")

if homepage_html:
    print("\nParsing homepage for career links...")
    soup = BeautifulSoup(homepage_html or "", "html.parser")

    # Gather candidate career URLs
    print("Finding career links from homepage...")
    found_links = find_career_links(soup, homepage_url, limit=MAX_CAREER_LINKS * 3)
    print(f"Found {len(found_links)} career links from homepage")

    # Common career URLs
    print("Checking common career URL patterns...")
    common_urls = list(common_career_urls(homepage_url))[:4]
    print(f"Common career URLs to check: {common_urls}")

    # Combine candidates - common_career_urls returns tuples (url, method)
    common_url_strings = [url for url, _ in common_urls]
    candidates = found_links + common_url_strings
    print(f"Total candidates before dedupe: {len(candidates)}")

    # Simulate dedupe
    seen = set()
    cands = []
    for u in candidates:
        normalized = u.split("#")[0].rstrip("/")
        if normalized and normalized not in seen:
            seen.add(normalized)
            cands.append(normalized)
    print(f"Candidates after dedupe: {len(cands)}")

    if cands:
        print(f"First few candidates: {cands[:5]}")

        # Test fetching the first career page
        first_career_url = cands[0]
        print(f"\nTesting first career page: {first_career_url}")
        career_resp = session.fetch(first_career_url, timeout=25)
        if career_resp is not None and career_resp.status_code < 400:
            career_html = career_resp.text
            print(f"Career page HTML length: {len(career_html) if career_html else 0}")
            if career_html:
                print("First 200 chars of career page:")
                print(career_html[:200])

                # Check if this looks like it has job links
                from job_scraper.parsers_generic import _extract_job_links
                job_links = _extract_job_links(career_html, first_career_url)
                print(f"Found {len(job_links)} potential job links in career page")
                if job_links:
                    print(f"First few job links: {job_links[:3]}")
        else:
            print(f"Failed to fetch career page: {career_resp.status_code if career_resp else 'None'}")

print("=" * 50)