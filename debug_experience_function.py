import sys
sys.path.append('D:/data_companies/job_data_cleaner')

from clean_jobs_extractors import experience

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

print("Testing experience function...")
for text in test_cases:
    result = experience(text)
    print(f"Input: {text}")
    print(f"Output: {result}")
    print("-" * 50)