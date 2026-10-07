import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from job_scraper.session import ScrapeSession
from job_scraper.urlutils import normalize_website
from bs4 import BeautifulSoup
import re

# Test with one company and examine the actual content for job listings
company_name = "B2C2 LTD"
website = "www.b2c2.com"
country = "United Kingdom"

print(f"Examining career page content for: {company_name}")
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
        # Parse with BeautifulSoup
        soup = BeautifulSoup(career_html, "html.parser")

        # Get the text content
        page_text = soup.get_text(" ", strip=True)
        print(f"Page text length: {len(page_text)}")

        # Look for common job listing patterns in the text
        print("\nSearching for job-related content in page text...")

        # Patterns that might indicate job listings
        job_patterns = [
            r'(?i)(senior|junior|lead|principal)?\s*(software|developer|engineer|analyst|manager|specialist|consultant|administrator|coordinator)',
            r'(?i)(position|role|vacancy|opening):\s*[^\n]{10,100}',
            r'(?i)we\'?re?\s*(hiring|looking\s+for)\s*[^\n]{10,100}',
            r'(?i)join\s+our\s+team\s*[^\n]{10,100}',
            r'(?i)apply\s+now\s*[^\n]{0,50}',
            r'(?i)responsibilities\s*:?\s*[^\n]{10,200}',
            r'(?i)requirements\s*:?\s*[^\n]{10,200}',
            r'(?i)qualifications\s*:?\s*[^\n]{10,200}'
        ]

        found_patterns = []
        for pattern in job_patterns:
            matches = re.findall(pattern, page_text)
            if matches:
                found_patterns.append((pattern, len(matches)))
                print(f"Pattern '{pattern}' found {len(matches)} matches")
                # Show first few matches
                for i, match in enumerate(matches[:3]):
                    if isinstance(match, tuple):
                        match_str = ' '.join(match)
                    else:
                        match_str = match
                    print(f"  Match {i+1}: {match_str[:100]}...")
                if len(matches) > 3:
                    print(f"  ... and {len(matches) - 3} more")
                print()

        if not found_patterns:
            print("No obvious job listing patterns found in page text")

        print("\n" + "="*50)
        print("Looking for structured job data...")

        # Look for common job listing structures in HTML
        # Check for elements with job-related classes or IDs
        job_elements = soup.find_all(class_=re.compile(r'(job|position|vacancy|career|opening)', re.I))
        print(f"Found {len(job_elements)} elements with job-related class names")

        job_id_elements = soup.find_all(id=re.compile(r'(job|position|vacancy|career|opening)', re.I))
        print(f"Found {len(job_id_elements)} elements with job-related ID names")

        # Look for common job listing containers
        potential_containers = soup.find_all(['div', 'li', 'tr', 'section', 'article'],
                                           class_=re.compile(r'(job|position|vacancy|opening|role)', re.I))
        print(f"Found {len(potential_containers)} potential job containers")

        if potential_containers:
            print("Examining first few containers:")
            for i, container in enumerate(potential_containers[:3]):
                container_text = container.get_text(" ", strip=True)
                if len(container_text) > 20:
                    print(f"  Container {i+1}: {container_text[:150]}...")

        print("\n" + "="*50)
        print("Checking for inline job patterns...")

        # Look for the kind of inline job patterns our parser looks for
        from job_scraper.parsers_generic import INLINE_JOB_TITLE_RE, APPLICATION_TEXT_RE

        inline_title_matches = INLINE_JOB_TITLE_RE.findall(page_text)
        print(f"INLINE_JOB_TITLE_RE found {len(inline_title_matches)} matches")
        if inline_title_matches:
            print(f"  Matches: {inline_title_matches[:5]}")

        application_matches = APPLICATION_TEXT_RE.findall(page_text)
        print(f"APPLICATION_TEXT_RE found {len(application_matches)} matches")
        if application_matches:
            print(f"  Matches: {application_matches[:5]}")

        # Look for headings that might be job titles followed by descriptive text
        print("\nLooking for heading + description patterns...")
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        print(f"Found {len(headings)} headings")

        job_like_headings = []
        for heading in headings:
            heading_text = heading.get_text(" ", strip=True)
            # Look for headings that seem like job titles
            if (len(heading_text) > 5 and len(heading_text) < 150 and
                not any(skip in heading_text.lower() for skip in ['home', 'about', 'contact', 'news', 'solution', 'product', 'team', 'value'])):
                job_like_headings.append(heading_text)

        if job_like_headings:
            print(f"Found {len(job_like_headings)} headings that could be job titles:")
            for i, text in enumerate(job_like_headings[:10]):
                print(f"  {i+1}. {text}")

                # Look for descriptive text after this heading
                # Find the next sibling elements that might contain job description
                heading_element = heading
                # This is a simplified check - in reality we'd need to traverse the DOM
                # But for now, let's just see if there's substantial text nearby
        else:
            print("No obvious job title headings found")

        # Save a sample of the HTML for manual inspection
        print("\n" + "="*50)
        print("Saving sample of HTML for inspection...")
        with open(r"D:\data_companies\b2c2_careers_sample.html", "w", encoding="utf-8") as f:
            f.write(career_html[:5000])  # First 5000 chars
        print("Saved first 5000 chars to b2c2_careers_sample.html")
    else:
        print("No HTML content retrieved")
else:
    print(f"Failed to fetch career page: {resp.status_code if resp else 'None'}")

print("=" * 50)