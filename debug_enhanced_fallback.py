import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from job_scraper.company import process_company_details
from job_scraper.session import ScrapeSession

# Test with one company and see what happens in detail
company_name = "B2C2 LTD"
website = "www.b2c2.com"
country = "United Kingdom"

print(f"Testing enhanced fallback for: {company_name}")
print(f"Website: {website}")
print(f"Country: {country}")
print("=" * 50)

# Create a session
session = ScrapeSession()

# Import the function we want to test
from job_scraper.company import process_company_details

# Call the function and capture the result
result = process_company_details((company_name, website, country), session=session)

print(f"Result status: {result['status']}")
print(f"Result source: {result['source']}")
print(f"Number of jobs: {len(result['jobs'])}")

if result['jobs']:
    print("Jobs found:")
    for i, job in enumerate(result['jobs'][:3]):
        print(f"  Job {i+1}: {job.get('job_title', 'N/A')} - {job.get('job_location', 'N/A')}")
else:
    print("No jobs found in result.")

# Let's also check what the discovery metadata contains
print(f"\nDiscovery metadata:")
for key in ['career_page_url', 'career_page_status', 'career_page_discovery_method']:
    if key in result:
        print(f"  {key}: {result.get(key, 'Not present')}")