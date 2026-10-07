import csv

# The correct string we want to eventually see after fixing
correct = "We are looking for an engineer with knowledge of Ändern and Übertragung. Also we need someone who can work with Müller und Schmitt."

# Create the mojibake version: encode as UTF-8, then decode as latin-1
mojibake = correct.encode('utf-8').decode('latin-1')
print("Mojibake string:", repr(mojibake))

# Write a CSV with this mojibake in the job_description field
rows = [{
    "company_name": "Test Corp",
    "job_title": "Software Engineer",
    "job_description": mojibake,
    "job_location": "Berlin",
    "years_of_expereince": "3",
    "employment_type": "",
    "skills": "",
    "education_type": "",
    "education_stream": "",
    "education_qualification": "",
    "seniority_level": "",
    "salary": "",
    "min_salary": "",
    "max_salary": "",
    "application_deadline": "",
    "posted_date": "",
    "website": "",
    "career_page_url": "",
    "status": "",
    "closed_date": "",
    "job_Status": "",
    "job_category": "",
    "description_language": "",
    "job_url": "",
    "source": "",
    "country": "",
    "career_page_status": "",
}]

with open('test_mojibake_real.csv', 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print("Written test_mojibake_real.csv")