import sys
sys.path.append('D:/data_companies/job_data_cleaner')

from clean_jobs_extractors import salary

# Test salary range extraction
test_cases = [
    "Jahresbruttogehalt von 60.000-112.000€",
    "Je nach Qualifikation und Erfahrung bieten wir 60.000-100.000€",
    "60.000-112.000 EUR",
    "50.000 - 70.000€",
    "50.000€ - 70.000€",
    "ab 31.640 €",  # This should only have min
    "60.000€",      # This should only have min
]

print("Testing salary range extraction...")
for text in test_cases:
    result = salary(text)
    print(f"Input: {text}")
    print(f"Output: {result}")
    print("-" * 50)