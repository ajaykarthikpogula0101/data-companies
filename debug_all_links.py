import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from job_scraper.session import ScrapeSession
from job_scraper.urlutils import normalize_website, url_join
from bs4 import BeautifulSoup
import re

# Test with one company and see all the links on the career page
company_name = "B2C2 LTD"
website = "www.b2c2.com"
country = "United Kingdom"

print(f"Examining all links on career page for: {company_name}")
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

        # Get all links
        all_links = soup.find_all("a", href=True)
        print(f"Total <a> tags with href: {len(all_links)}")

        # Show first 30 links
        print("\nFirst 30 links:")
        for i, link in enumerate(all_links[:30]):
            href = link.get("href", "")
            text = link.get_text(" ", strip=True)
            # Clean up text for display
            clean_text = ' '.join(text.split())[:50]  # Limit length and normalize whitespace
            full_url = url_join(career_url, href) if not href.startswith('http') else href
            print(f"  {i+1:2d}. href='{href}'")
            print(f"       text='{clean_text}'")
            print(f"       full='{full_url}'")
            print()

        # Look for links that might be job-related based on text
        print("Links with job-related text:")
        job_related_count = 0
        for i, link in enumerate(all_links):
            href = link.get("href", "")
            text = link.get_text(" ", strip=True).lower()

            # Check for job-related keywords in text
            job_keywords = ['job', 'position', 'role', 'vacancy', 'opening', 'apply', 'career', 'opportunity']
            if any(keyword in text for keyword in job_keywords):
                clean_text = ' '.join(text.split())[:60]
                full_url = url_join(career_url, href) if not href.startswith('http') else href
                print(f"  {job_related_count+1:2d}. text='{clean_text}' -> href='{href}'")
                job_related_count += 1
                if job_related_count >= 10:  # Limit output
                    break

        if job_related_count == 0:
            print("  No links with obvious job-related text found")

        print("\n" + "="*50)
        print("Checking if career page contains job listings in other formats...")

        # Look for common job listing structures
        # Check for headings that might be job titles
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        print(f"Found {len(headings)} heading tags")

        job_title_like_headings = []
        for heading in headings[:20]:  # Check first 20 headings
            text = heading.get_text(" ", strip=True)
            if len(text) > 5 and len(text) < 100:  # Reasonable job title length
                # Check if it looks like a job title
                if any(word in text.lower() for word in ['engineer', 'developer', 'manager', 'analyst', 'specialist', 'consultant']):
                    job_title_like_headings.append((heading.name, text))

        if job_title_like_headings:
            print(f"Found {len(job_title_like_headings)} headings that look like job titles:")
            for tag, text in job_title_like_headings[:10]:
                print(f"  <{tag}>: {text}")
        else:
            print("No obvious job title headings found")

        # Look for divs or sections that might contain job listings
        print("\nLooking for potential job listing containers...")
        containers = soup.find_all(['div', 'section', 'li', 'tr', 'article', 'dl'])
        job_containers = []
        for container in containers[:50]:  # Check first 50 containers
            # Look for elements that might contain job info
            container_text = container.get_text(" ", strip=True).lower()
            if len(container_text) > 50:  # Substantial content
                # Check for job-related keywords
                if any(keyword in container_text for keyword in ['apply', 'position', 'role', 'job', 'vacancy', 'responsibilities']):
                    # Check if it has some structure (like multiple lines or list-like elements)
                    lines = [line.strip() for line in container_text.split('\n') if line.strip()]
                    if len(lines) > 3:
                        job_containers.append(container)

        print(f"Found {len(job_containers)} potential job listing containers")
        if job_containers:
            print("Examining first container:")
            container = job_containers[0]
            container_text = container.get_text(" ", strip=True)
            print(f"Container text preview: {container_text[:200]}...")
else:
    print(f"Failed to fetch career page: {resp.status_code if resp else 'None'}")

print("=" * 50)