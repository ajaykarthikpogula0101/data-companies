import sys
sys.path.append('D:/data_companies/job_data_cleaner')

import re
from clean_jobs_extractors import GERMAN_SALARY_PATTERNS

test_text = "Jahresbruttogehalt von 60.000-112.000€"
print(f"Testing: {test_text}")
print()

for i, pattern in enumerate(GERMAN_SALARY_PATTERNS):
    print(f"Pattern {i}: {pattern.pattern}")
    match = pattern.search(test_text)
    if match:
        print(f"  MATCH: {match.group()}")
        print(f"  Groups: {match.groups()}")
        print(f"  Group dict: {match.groupdict()}")
        if match.lastindex:
            print(f"  Last index: {match.lastindex}")
            for j in range(1, match.lastindex + 1):
                print(f"    Group {j}: {match.group(j)}")
    else:
        print("  NO MATCH")
    print()