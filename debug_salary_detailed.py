import sys
sys.path.append('D:/data_companies/job_data_cleaner')

import re
from clean_jobs_extractors import GERMAN_SALARY_PATTERNS

def debug_salary(text: str):
    print(f"Input: {repr(text)}")
    print(f"Length: {len(text)}")
    for i, ch in enumerate(text):
        print(f"  [{i}] {repr(ch)} (ord: {ord(ch)})")
    print()

    # First try the original salary pattern
    from clean_jobs_extractors import SALARY_RE
    match = SALARY_RE.search(text)
    if match:
        print("  Matched SALARY_RE")
        print(f"    Whole: {repr(match.group(0))}")
        print(f"    Min: {repr(match.group('min'))}")
        print(f"    Max: {repr(match.group('max'))}")
        return

    # If no match, try German-specific patterns
    print("  Trying GERMAN_SALARY_PATTERNS")
    for i, pattern in enumerate(GERMAN_SALARY_PATTERNS):
        print(f"    Pattern {i}: {pattern.pattern}")
        match = pattern.search(text)
        if match:
            print(f"      MATCHED!")
            print(f"        Whole: {repr(match.group(0))}")
            print(f"        Min: {repr(match.group('min')) if match.group('min') else ''}")
            # Safely get max group - some patterns don't have it
            max_val = ""
            if match.lastindex and match.lastindex >= 2:  # Check if there are at least 2 groups
                try:
                    max_val = match.group("max").strip() if match.group("max") else ""
                except IndexError:
                    # No max group in this pattern
                    max_val = ""
            print(f"        Max: {repr(max_val)}")
            print(f"        Lastindex: {match.lastindex}")
            if match.lastindex:
                for j in range(1, match.lastindex + 1):
                    print(f"          Group {j}: {repr(match.group(j))}")
            return
        else:
            print(f"      No match")
    print("    No German pattern matched")

# Test the problematic case - using actual euro symbol
debug_salary("50.000€ - 70.000€")
print("=" * 50)
debug_salary("50.000-70.000€")
print("=" * 50)
debug_salary("ab 31.640 €")