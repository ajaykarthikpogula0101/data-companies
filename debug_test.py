import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Monkey patch to add debug prints
original_process_company_details = None

def debug_process_company_details(company_row, session=None, enable_search=True):
    """Debug version of process_company_details with extra logging"""
    from job_scraper.company import process_company_details as original_func
    from job_scraper.session import ScrapeSession

    name, website, country = company_row
    print(f"\n[DEBUG] Processing company: {name}")
    print(f"[DEBUG] Website: {website}")
    print(f"[DEBUG] Country: {country}")

    session = session or ScrapeSession()
    result = original_func(company_row, session=session, enable_search=enable_search)

    print(f"[DEBUG] Result status: {result['status']}")
    print(f"[DEBUG] Result source: {result['source']}")
    print(f"[DEBUG] Number of jobs: {len(result['jobs'])}")
    if result['jobs']:
        print(f"[DEBUG] First job title: {result['jobs'][0].get('job_title', 'N/A')}")

    return result

# Replace the function in the module
import job_scraper.company
job_scraper.company.process_company_details = debug_process_company_details

# Now test
from job_scraper.company import process_company_details

# Test with a couple of companies from the no_job_titles file
companies_to_test = [
    ("B2C2 LTD", "www.b2c2.com", "United Kingdom"),
    ("B1bank", "www.b1bank.com", "USA"),
]

print("Testing with debug output...")
print("=" * 50)

for company_name, website, country in companies_to_test:
    print(f"\n{'='*20} STARTING {company_name} {'='*20}")
    # Process the company
    result = process_company_details((company_name, website, country))
    status = result['status']
    jobs = result['jobs']
    source = result['source']
    career_page_url = result.get('career_page_url', 'Not found')
    career_page_status = result.get('career_page_status', 'Not found')

    print(f"\n[RESULT] Status: {status}")
    print(f"[RESULT] Source: {source}")
    print(f"[RESULT] Career Page URL: {career_page_url}")
    print(f"[RESULT] Career Page Status: {career_page_status}")
    print(f"[RESULT] Number of jobs found: {len(jobs)}")

    if jobs:
        print("[RESULT] Jobs found:")
        for i, job in enumerate(jobs[:3]):  # Show first 3 jobs
            print(f"  Job {i+1}:")
            for key in ['job_title', 'job_location', 'employment_type']:
                if key in job and job[key]:
                    print(f"    {key}: {job[key]}")
    else:
        print("[RESULT] No jobs found.")

    print("=" * 50)

print("Test completed.")