import csv
import tempfile
import os
import sys
sys.path.insert(0, '/d/data_companies')

from job_data_cleaner.clean_jobs import process
from pathlib import Path

def test_mojibake_integration():
    # Create a sample CSV with mojibake in job_description
    sample_rows = [
        {
            "company_name": "Test Corp",
            "job_title": "Software Engineer",
            "job_description": "We are looking for an engineer with knowledge of Ändern and Übertragung. Also we need someone who can work with Müller und Schmitt.",
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
        }
    ]

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8-sig') as infile:
        writer = csv.DictWriter(infile, fieldnames=sample_rows[0].keys())
        writer.writewriter()
        writer.writerows(sample_rows)
        input_path = infile.name

    output_path = input_path.replace('.csv', '_output.csv')

    try:
        rows, jobs = process(Path(input_path), Path(output_path), None, None)
        print(f"Processed {rows} rows, {jobs} job rows")

        # Read the output and check the job_description
        with open(output_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                desc = row['job_description']
                print(f"Output job_description: {repr(desc)}")
                # Check that mojibake is fixed: Ändern should become ändern? Actually Ä is capital A-umlaut.
                # The input had "Ändern" and "Übertragung". In the string we wrote: "Ändern" and "Über"
                # Actually we wrote: "Ändern and Übertragung. Also we need someone who can work with Müller und Schmitt."
                # Let's see if they are fixed.
                if 'Ä' in desc or 'Ü' in desc or 'Ã' in desc or 'â' in desc:
                    print(f"ERROR: Mojibake still present in description: {repr(desc)}")
                    return False
                else:
                    print("SUCCESS: No mojibake found in description.")
                    return True
    finally:
        try:
            os.unlink(input_path)
            os.unlink(output_path)
        except:
            pass

if __name__ == '__main__':
    success = test_mojibake_integration()
    sys.exit(0 if success else 1)