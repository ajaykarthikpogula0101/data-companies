import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from job_scraper.ats import detect_ats_in_url

# Test the URL we found
test_url = "https://boards.eu.greenhouse.io/embed/job_board/js?for=b2c2"
print(f"Testing URL: {test_url}")

ats, captured = detect_ats_in_url(test_url)
print(f"Detected ATS: {ats}")
print(f"Captured: '{captured}'")

# Also test what the regex actually matches
import re
from job_scraper.ats import ATS_URL_PATTERNS

print("\nChecking ATS_URL_PATTERNS for greenhouse:")
for ats, pat in ATS_URL_PATTERNS:
    if ats == "greenhouse":
        print(f"Greenhouse pattern: {pat.pattern}")
        m = pat.search(test_url)
        if m:
            print(f"  Match found: {m.group()}")
            print(f"  Groups: {m.groups()}")
            if m.groups():
                print(f"  Group 1: '{m.group(1)}'")
        else:
            print("  No match found")
        break

print("\nTesting if we should modify the greenhouse pattern to handle query parameters...")

# Test a modified pattern that would capture from query parameters
modified_pattern = re.compile(r"(?:boards|careers)\.greenhouse\.io.*[?&]for=([a-zA-Z0-9\-_.]+)")
m2 = modified_pattern.search(test_url)
if m2:
    print(f"  Modified pattern match: {m2.group()}")
    print(f"  Group 1 (company): '{m2.group(1)}'")
else:
    print("  Modified pattern no match")

# Test if we can extract the for parameter directly
import urllib.parse
parsed = urllib.parse.urlparse(test_url)
query_params = urllib.parse.parse_qs(parsed.query)
print(f"\nQuery parameters: {query_params}")
if 'for' in query_params:
    print(f"  'for' parameter: {query_params['for']}")