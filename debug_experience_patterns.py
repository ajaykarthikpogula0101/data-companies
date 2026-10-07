import sys
sys.path.append('D:/data_companies/job_data_cleaner')

import re
from clean_jobs_extractors import EXPERIENCE_PATTERNS

# Test cases
test_cases = [
    "5 Jahre Berufserfahrung im Controlling, FP&A oder Finance Business Partnering",
    "mindestens 3 bis 5 Jahre Berufserfahrung im Business Development, Vertrieb, Consulting",
    "Du bringst mindestens 5 Jahre Berufserfahrung ... mit",
    "einige Jahre Berufserfahrung",
    "mehrjährige Erfahrung",
    "5+ Jahre Berufserfahrung",
    "3-5 Jahre Berufserfahrung"
]

print("Testing individual patterns...")
for i, pattern in enumerate(EXPERIENCE_PATTERNS):
    print(f"\nPattern {i}: {pattern.pattern}")
    for text in test_cases:
        match = pattern.search(text)
        if match:
            print(f"  MATCH: '{text}'")
            print(f"    Groups: {match.groups()}")
            print(f"    Group 1: {match.group(1) if match.lastindex and match.lastindex >= 1 else 'N/A'}")
            print(f"    Group 2: {match.group(2) if match.lastindex and match.lastindex >= 2 else 'N/A'}")