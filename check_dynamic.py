import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from job_scraper.session import ScrapeSession
from job_scraper.urlutils import normalize_website
import re

# Check for signs of dynamic content loading
company_name = "B2C2 LTD"
website = "www.b2c2.com"
country = "United Kingdom"

print(f"Checking for dynamic content on: {company_name}")
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
        # Look for signs of dynamic content loading
        print("\nChecking for JavaScript frameworks and dynamic loading...")

        # Common indicators of dynamic/Javascript-heavy sites
        dynamic_indicators = [
            'data-wf-',  # Webflow
            'data-react',
            'data-vue',
            'ng-',  # Angular
            'ajax',
            'fetch(',
            'XMLHttpRequest',
            'loadMore',
            'infinite-scroll',
            'lazy-load',
            '__NEXT_DATA__',  # Next.js
            'window.__PRELOADED_STATE__',
            'data-spa'  # Single Page Application
        ]

        found_indicators = []
        for indicator in dynamic_indicators:
            if indicator in career_html:
                found_indicators.append(indicator)

        if found_indicators:
            print(f"Found dynamic content indicators: {', '.join(found_indicators)}")
        else:
            print("No obvious dynamic content indicators found")

        # Look for script tags that might contain job data
        print("\nChecking for embedded data in script tags...")
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(career_html, "html.parser")
        scripts = soup.find_all("script")
        print(f"Found {len(scripts)} script tags")

        # Look for scripts that might contain JSON data
        json_scripts = 0
        for script in scripts:
            if script.string:
                content = script.string
                # Look for patterns that might indicate job data
                if ('"' in content and
                    ('job' in content.lower() or
                     'position' in content.lower() or
                     'vacancy' in content.lower() or
                     'opening' in content.lower())):
                    json_scripts += 1
                    # Show a sample
                    sample = content[:200].replace('\n', ' ').strip()
                    print(f"  Script with job-related content: {sample}...")

        if json_scripts > 0:
            print(f"Found {json_scripts} script tags with potential job data")
        else:
            print("No script tags with obvious job-related content found")

        # Look for specific Webflow attributes that might indicate dynamic content
        print("\nChecking for Webflow-specific dynamic attributes...")
        webflow_elements = soup.find_all(attrs=re.compile(r'data-wf-'))
        print(f"Found {len(webflow_elements)} elements with data-wf-* attributes")

        if webflow_elements:
            # Show a few examples
            for i, elem in enumerate(webflow_elements[:5]):
                attrs = [attr for attr in elem.attrs if attr.startswith('data-wf-')]
                print(f"  Element {elem.name}: {attrs}")

        # Check if there are any noscript tags (fallback for when JS is disabled)
        noscripts = soup.find_all("noscript")
        print(f"\nFound {len(noscripts)} noscript tags")
        if noscripts:
            for i, noscript in enumerate(noscripts[:3]):
                content = noscript.get_text()[:100]
                print(f"  Noscript {i+1}: {content}...")

    else:
        print("No HTML content retrieved")
else:
    print(f"Failed to fetch career page: {resp.status_code if resp else 'None'}")

print("=" * 50)