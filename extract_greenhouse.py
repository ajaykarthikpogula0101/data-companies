import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from job_scraper.session import ScrapeSession
from job_scraper.urlutils import normalize_website
import re
import json

# Try to extract Greenhouse job board URL from JavaScript
company_name = "B2C2 LTD"
website = "www.b2c2.com"
country = "United Kingdom"

print(f"Trying to extract Greenhouse URL for: {company_name}")
print(f"Website: {website}")
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
        # Look for the specific script content we saw earlier
        print("\nSearching for Greenhouse references in JavaScript...")

        # Look for the pattern we saw in the debug output
        greenhouse_patterns = [
            r'boards\.eu\.greenhouse\.io',
            r'job-boards\.eu\.greenhouse\.io',
            r'greenhouse\.io',
            r'boards\.greenhouse\.io',
            r'job-boards\.greenhouse\.io'
        ]

        found_patterns = []
        for pattern in greenhouse_patterns:
            matches = re.findall(pattern, career_html, re.IGNORECASE)
            if matches:
                found_patterns.extend(matches)
                print(f"Pattern '{pattern}' found {len(matches)} times")
                # Show unique matches
                unique_matches = list(set(matches))
                for match in unique_matches[:5]:
                    print(f"  Match: {match}")

        if not found_patterns:
            print("No Greenhouse patterns found in HTML")

        # Now let's look for the actual URL in the TERMLY_CUSTOM_BLOCKING_MAP or similar
        print("\nSearching for Greenhouse URLs in JavaScript objects...")

        # Look for assignments that might contain greenhouse URLs
        url_patterns = [
            r'["\'](https?://[^"\']*greenhouse\.io[^"\']*)["\']',
            r'["\'](https?://[^"\']*boards\.eu\.greenhouse\.io[^"\']*)["\']',
            r'["\'](https?://[^"\']*job-boards\.eu\.greenhouse\.io[^"\']*)["\']'
        ]

        found_urls = []
        for pattern in url_patterns:
            matches = re.findall(pattern, career_html, re.IGNORECASE)
            if matches:
                found_urls.extend(matches)
                print(f"URL pattern '{pattern}' found {len(matches)} matches")
                for url in matches[:3]:
                    print(f"  URL: {url}")

        # Also look for the specific object we saw
        termly_pattern = r'window\.TERMLY_CUSTOM_BLOCKING_MAP\s*=\s*({[^}]+})'
        termly_match = re.search(termly_pattern, career_html)
        if termly_match:
            print(f"\nFound TERMLY_CUSTOM_BLOCKING_MAP: {termly_match.group(1)[:200]}...")
            # Try to parse it as JSON (might need some cleaning)
            try:
                # This is likely not valid JSON as-is, but let's see what we can extract
                map_content = termly_match.group(1)
                # Look for greenhouse URLs within this map
                greenhouse_in_map = re.findall(r'https?://[^,\s\']*greenhouse\.io[^\s,\']*', map_content, re.IGNORECASE)
                if greenhouse_in_map:
                    print(f"Found greenhouse URLs in TERMLY map: {greenhouse_in_map}")
                else:
                    print("No greenhouse URLs found in TERMLY map")
            except Exception as e:
                print(f"Error parsing TERMLY map: {e}")

        # Let's also try to extract any URLs that look like they could be job board URLs
        print("\nSearching for any potential job board URLs...")
        # More general pattern for job board URLs
        general_url_pattern = r'https?://[^\s"\'>]+(?:greenhouse|lever|workday|smartrecruiters)[^\s"\'>]*'
        general_matches = re.findall(general_url_pattern, career_html, re.IGNORECASE)
        if general_matches:
            print(f"Found {len(general_matches)} potential job board URLs:")
            for url in list(set(general_matches))[:10]:  # Show unique ones, limit to 10
                print(f"  {url}")
        else:
            print("No potential job board URLs found with general pattern")

        # Let's look at the actual script content that contained the greenhouse reference
        print("\nLooking for the specific script containing greenhouse references...")
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(career_html, "html.parser")
        scripts = soup.find_all("script")

        for i, script in enumerate(scripts):
            if script.string and ('greenhouse' in script.string.lower() or 'boards.eu' in script.string.lower()):
                print(f"\nScript {i} contains greenhouse/boards reference:")
                content = script.string
                # Show a reasonable excerpt
                if len(content) > 500:
                    print(f"  Length: {len(content)} characters")
                    # Try to find the interesting part
                    greenhouse_pos = content.lower().find('greenhouse')
                    if greenhouse_pos != -1:
                        start = max(0, greenhouse_pos - 100)
                        end = min(len(content), greenhouse_pos + 300)
                        print(f"  Context: {content[start:end]}")
                    else:
                        print(f"  First 200 chars: {content[:200]}")
                else:
                    print(f"  Content: {content}")

    else:
        print("No HTML content retrieved")
else:
    print(f"Failed to fetch career page: {resp.status_code if resp else 'None'}")

print("=" * 50)