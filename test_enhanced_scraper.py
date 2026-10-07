import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from job_scraper.company import process_company_details
import pandas as pd

# Read a small sample of companies from VM1_no_job_titles.csv
# Skip the header and take first 5 companies with "Career Page Found - Extraction Unsupported"
df = pd.read_csv("D:/data_companies/VM1_no_job_titles.csv", quotechar='"', escapechar='\\')
# Filter for companies with extraction issues
sample_df = df[df['extraction_status'] == 'Extraction Unsupported'].head(5)

print(f"Testing {len(sample_df)} companies with extraction issues...")
print("=" * 60)

for idx, row in sample_df.iterrows():
    company_name = row['company_name']
    website = row['website']
    country = row['country']

    print(f"Processing: {company_name}")
    print(f"Website: {website}")
    print(f"Country: {country}")
    print("-" * 40)

    # Process the company
    result = process_company_details((company_name, website, country))
    status = result['status']
    jobs = result['jobs']
    source = result['source']

    print(f"Status: {status}")
    print(f"Source: {source}")
    print(f"Number of jobs found: {len(jobs)}")
    print(f"Career page URL: {result.get('career_page_url', 'Not found')}")
    print(f"Career page status: {result.get('career_page_status', 'Not found')}")

    if jobs:
        print("First job found:")
        first_job = jobs[0]
        for key in ['job_title', 'job_location', 'employment_type']:  # Fixed duplicate employment_type
            if key in first_job:
                print(f"  {key}: {first_job[key]}")
    else:
        print("No jobs found.")

    print("=" * 60)
    print()

print("Test completed.")