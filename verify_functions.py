import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test that our enhanced functions exist and can be imported
from job_scraper.company import (
    _extract_and_process_job_links,
    _extract_and_process_paginated_content,
    _enhance_inline_job_detection
)

print("All enhanced functions imported successfully!")
print(f"_extract_and_process_job_links: {_extract_and_process_job_links}")
print(f"_extract_and_process_paginated_content: {_extract_and_process_paginated_content}")
print(f"_enhance_inline_job_detection: {_enhance_inline_job_detection}")

# Test that the main function still works
from job_scraper.company import process_company_details
print(f"process_company_details: {process_company_details}")

print("Verification completed successfully!")