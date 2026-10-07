import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from job_scraper.session import ScrapeSession
from job_scraper.urlutils import normalize_website, url_join
from job_scraper.parsers_generic import _extract_job_links, JOB_LINK_RE, EXCLUDE
from bs4 import BeautifulSoup
import re

# Test with one company and see what happens with job link extraction
company_name = "B2C2 LTD"
website = "www.b2c2.com"
country = "United Kingdom"

print(f"Testing job link extraction for: {company_name}")
print(f"Website: {website}")
print(f"Country: {country}")
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
        print("First 500 chars of career page:")
        print(career_html[:500])
        print("\n" + "="*50)

        # Parse with BeautifulSoup
        soup = BeautifulSoup(career_html, "html.parser")

        # Look for common job-related text patterns
        print("Searching for job-related text patterns...")
        job_patterns = [
            r'job', r'position', r'vacancy', r'role', r'opening',
            r'apply', r'career', r'join', r'work', r'employment'
        ]

        page_text = soup.get_text(" ", strip=True).lower()
        for pattern in job_patterns:
            matches = re.findall(pattern, page_text)
            if matches:
                print(f"Found '{pattern}' {len(matches)} times")

        print("\n" + "="*50)
        print("Testing job link extraction...")

        # Test our job link extraction
        job_links = _extract_job_links(career_html, career_url)
        print(f"_extract_job_links found: {len(job_links)} links")
        if job_links:
            print("Job links found:")
            for i, link in enumerate(job_links[:10]):
                print(f"  {i+1}. {link}")

        print("\n" + "="*50)
        print("Manual inspection of links...")

        # Let's manually inspect some links to see what we're missing
        all_links = soup.find_all("a", href=True)
        print(f"Total <a> tags with href: {len(all_links)}")

        job_related_links = []
        for link in all_links[:20]:  # Check first 20 links
            href = link.get("href", "")
            text = link.get_text(" ", strip=True).lower()
            full_url = url_join(career_url, href)

            # Check if it looks job-related
            is_job_related = (
                any(pattern in href.lower() for pattern in ['job', 'position', 'vacancy', 'role']) or
                any(pattern in text for pattern in ['job', 'position', 'vacancy', 'role', 'apply', 'career'])
            )

            if is_job_related:
                job_related_links.append((href, text, full_url))
                print(f"Job-related link: href='{href}', text='{text[:50]}...', full='{full_url}'")

        print(f"\nFound {len(job_related_links)} job-related links in first 20 <a> tags")

        print("\n" + "="*50)
        print("Testing JOB_LINK_RE pattern...")

        # Test the JOB_LINK_RE directly on some hrefs
        test_hrefs = [
            "/join-b2c2/careers",
            "/jobs",
            "/careers",
            "/job/software-engineer",
            "/position/manager",
            "/vacancy/analyst",
            "https://www.b2c2.com/jobs",
            "https://www.b2c2.com/careers/software-engineer"
        ]

        for href in test_hrefs:
            full_url = url_join(career_url, href) if not href.startswith('http') else href
            match = JOB_LINK_RE.search(href)
            print(f"Href: '{href}' -> Match: {bool(match)}")

        print("\n" + "="*50)
        print("Checking for potential issues...")

        # Check if our EXCLUDE pattern is blocking legitimate links
        print("Testing EXCLUDE pattern on common hrefs:")
        exclude_tests = [
            "/join-b2c2/careers",
            "/jobs",
            "/careers",
            "/wp-content/",
            "/assets/",
            "/static/",
            "/img/",
            "facebook.com",
            "linkedin.com"
        ]

        for href in exclude_tests:
            match = EXCLUDE.search(href)
            print(f"Href: '{href}' -> EXCLUDE match: {bool(match)}")
else:
    print(f"Failed to fetch career page: {resp.status_code if resp else 'None'}")

print("=" * 50)