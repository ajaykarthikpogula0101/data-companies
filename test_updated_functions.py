import sys
sys.path.append('D:/data_companies/job_data_cleaner')

from clean_jobs_extractors import experience, salary

print("Testing UPDATED experience function...")
experience_test_cases = [
    "5 Jahre Berufserfahrung im Controlling, FP&A oder Finance Business Partnering",
    "mindestens 3 bis 5 Jahre Berufserfahrung im Business Development, Vertrieb, Consulting",
    "Du bringst mindestens 5 Jahre Berufserfahrung ... mit",
    "einige Jahre Berufserfahrung",
    "mehrjährige Erfahrung",
    "5+ Jahre Berufserfahrung",
    "3-5 Jahre Berufserfahrung",
    "2.5 Jahre Berufserfahrung",
    "mindestens 2.5 Jahre Berufserfahrung"
]

for text in experience_test_cases:
    result = experience(text)
    print(f"Input: {text}")
    print(f"Output: {result}")
    print("-" * 50)

print("\n\nTesting UPDATED salary function...")
salary_test_cases = [
    "Jahresbruttogehalt von 60.000-112.000€",
    "monatliches Bruttogehalt ab 2.251€",
    "Je nach Qualifikation und Erfahrung ein Bruttojahresgehalt ab 31.640 €",
    "60.000€",
    "60k€",
    "ab 31.640 €",
    "60 Tausend €",
    "60.000€ brutto/Jahr",
    "Je nach Qualifikation und Erfahrung bieten wir 60.000-100.000€"
]

for text in salary_test_cases:
    result = salary(text)
    print(f"Input: {text}")
    print(f"Output: {result}")
    print("-" * 50)