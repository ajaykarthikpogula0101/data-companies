import sys
sys.path.append('D:/data_companies/job_data_cleaner')

import re
from clean_jobs_extractors import SALARY_RE, GERMAN_SALARY_PATTERNS

def salary_debug(text: str):
    print(f"Input: {text}")
    # First try the original salary pattern
    match = SALARY_RE.search(text)
    if match:
        print("  Matched SALARY_RE")
        whole = re.sub(r"\s+", " ", match.group(0)).strip()
        print(f"    whole: {whole}")
        print(f"    min: {match.group('min').strip()}")
        print(f"    max: { (match.group('max') or '').strip() }")
        return whole, match.group("min").strip(), (match.group("max") or "").strip()

    # If no match, try German-specific patterns
    print("  Trying GERMAN_SALARY_PATTERNS")
    for i, pattern in enumerate(GERMAN_SALARY_PATTERNS):
        match = pattern.search(text)
        if match:
            print(f"    Matched pattern {i}: {pattern.pattern}")
            whole = re.sub(r"\s+", " ", match.group(0)).strip()
            print(f"      whole: {whole}")
            min_val = match.group("min").strip() if match.group("min") else ""
            print(f"      min: {min_val}")
            # Safely get max group - some patterns don't have it
            max_val = ""
            if match.lastindex and match.lastindex >= 2:  # Check if there are at least 2 groups
                try:
                    max_val = match.group("max").strip() if match.group("max") else ""
                except IndexError:
                    # No max group in this pattern
                    max_val = ""
            print(f"      max: {max_val}")
            return whole, min_val, max_val
    print("    No German pattern matched")
    return "", "", ""

# Test
test_cases = [
    "Jahresbruttogehalt von 60.000-112.000€",
    "monatliches Bruttogehalt ab 2.251€",
    "Je nach Qualifikation und Erfahrung ein Bruttojahresgehalt ab 31.640 €",
    "60.000€",
    "60k€",
    "ab 31.640 €",
    "60 Tausend €"
]

for text in test_cases:
    print("\n---")
    result = salary_debug(text)
    print(f"Result: {result}")