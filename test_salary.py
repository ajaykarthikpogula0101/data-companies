#!/usr/bin/env python3
"""Test script to validate salary extraction enhancements"""

import sys
sys.path.append('D:/data_companies/job_data_cleaner')

from clean_jobs_extractors import salary

# Test cases based on the data we saw
test_cases = [
    "Jahresbruttogehalt von 60.000-112.000€",
    "monatliches Bruttogehalt ab 2.251€",
    "Je nach Qualifikation und Erfahrung ein Bruttojahresgehalt ab 31.640 €",
    "60.000€",
    "60k€",
    "ab 31.640 €",
    "60 Tausend €"
]

print("Testing salary extraction...")
for text in test_cases:
    result = salary(text)
    print(f"Input: {text}")
    print(f"Output: {result}")
    print("-" * 50)