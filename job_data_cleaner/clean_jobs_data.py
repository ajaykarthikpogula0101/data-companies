#!/usr/bin/env python3
"""
Data cleaning script for job data CSV files.
This script fixes encoding issues, standardizes fields, and improves data quality.
"""

import pandas as pd
import numpy as np
import re
import json
from typing import Dict, List, Tuple, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_encoding(text: str) -> str:
    """Fix common encoding issues in text."""
    if pd.isna(text) or not isinstance(text, str):
        return text

    # Fix common HTML entities and encoding issues
    replacements = {
        '&': '&',
        '<': '<',
        '>': '>',
        '"': '"',
        "'": "'",
        '&nbsp;': ' ',
        'Ã¼': 'ü',
        'Ã¶': 'ö',
        'Ã¤': 'ä',
        'ÃŸ': 'ß',
        'Ã„': 'Ä',
        'Ã–': 'Ö',
        'Ãœ': 'Ü',
        'Â': '',  # Remove non-breaking space artifacts
        'â‚¬': '€',  # Euro symbol
        'â„¢': '™',  # Trademark
        'Â®': '®',  # Registered trademark
        'Â©': '©',  # Copyright
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text

def parse_salary(salary_str: Optional[str]) -> Tuple[Optional[float], Optional[float]]:
    """
    Parse salary string into min and max values.
    Handles formats like:
    - "60000 - 112000"
    - "27,3K€"
    - "$90,768 - $166,407"
    - "90768" (single value)
    """
    if pd.isna(salary_str) or not isinstance(salary_str, str):
        return None, None

    # Clean the string
    salary_str = salary_str.strip()

    # Handle empty strings
    if not salary_str:
        return None, None

    # Remove currency symbols and spaces
    cleaned = re.sub(r'[€$£¥]', '', salary_str)
    cleaned = re.sub(r'\s+', '', cleaned)

    # Handle K suffix (thousands)
    if 'K' in cleaned.upper():
        # Replace K with 000 and remove the K
        cleaned = cleaned.upper().replace('K', '000')

    # Split by common separators for ranges
    separators = ['-', '–', 'to', 'bis']  # hyphen, en-dash, to, german bis
    parts = None
    used_sep = None

    for sep in separators:
        if sep in cleaned:
            parts = cleaned.split(sep)
            used_sep = sep
            break

    if parts is None:
        # Single value
        try:
            # Handle European decimal format (comma as decimal)
            if ',' in cleaned and cleaned.count(',') == 1:
                # Check if it's likely a decimal (not thousands separator)
                # If there are exactly 3 digits after comma, it's likely decimal
                parts = cleaned.split(',')
                if len(parts) == 2 and len(parts[1]) <= 3:
                    # Treat as decimal
                    value = float(parts[0] + '.' + parts[1])
                    return value, value
                else:
                    # Treat comma as thousands separator - remove it
                    cleaned = cleaned.replace(',', '')

            value = float(cleaned)
            return value, value
        except ValueError:
            logger.warning(f"Could not parse single salary value: {salary_str}")
            return None, None
    else:
        # Range value
        try:
            min_val = parse_single_salary(parts[0])
            max_val = parse_single_salary(parts[1])

            if min_val is not None and max_val is not None:
                return min_val, max_val
            else:
                logger.warning(f"Could not parse salary range: {salary_str}")
                return None, None
        except Exception as e:
            logger.warning(f"Error parsing salary range '{salary_str}': {str(e)}")
            return None, None

def parse_single_salary(val_str: str) -> Optional[float]:
    """Parse a single salary value string."""
    if not val_str:
        return None

    # Handle empty
    if not val_str.strip():
        return None

    # Handle European decimal format
    if ',' in val_str and val_str.count(',') == 1:
        parts = val_str.split(',')
        if len(parts) == 2 and len(parts[1]) <= 3:
            # Likely decimal format
            try:
                return float(parts[0] + '.' + parts[1])
            except ValueError:
                pass

    # Remove any remaining non-numeric except decimal point and minus
    cleaned = re.sub(r'[^\d.-]', '', val_str)

    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None

def clean_location(location: str) -> str:
    """Clean and standardize location formatting."""
    if pd.isna(location) or not isinstance(location, str):
        return location

    # Fix encoding first
    location = fix_encoding(location)

    # Standardize separators - replace semicolons with commars for consistency
    # But be careful not to split within city names that might have commas
    # For now, let's just fix obvious semicolon usage between distinct locations
    location = location.replace('; ', ', ').replace(';', ',')

    # Clean up extra spaces
    location = re.sub(r'\s+', ' ', location).strip()

    return location

def extract_skills_from_description(description: str) -> str:
    """Extract skills from job description if skills field is empty."""
    if pd.isna(description) or not isinstance(description, str):
        return ""

    # Common skill indicators in job descriptions
    skill_patterns = [
        r'(?:knowledge|experience|skills?|proficiency|familiarity)\s+(?:in|with|of)\s+([^,\.;]+)',
        r'(?:proficient|experienced|skilled)\s+(?:in|with)\s+([^,\.;]+)',
        r'(?:working\s+knowledge|hands-on\s+experience)\s+(?:in|with)\s+([^,\.;]+)',
    ]

    skills_found = []
    description_lower = description.lower()

    # Also look for common tech skills directly
    tech_skills = [
        'python', 'python', 'java', 'javascript', 'typescript', 'c#', 'c++', 'ruby', 'php', 'swift', 'kotlin',
        'sql', 'nosql', 'mongodb', 'postgresql', 'mysql', 'oracle',
        'html', 'css', 'react', 'angular', 'vue', 'nodejs', 'express',
        'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'git',
        'agile', 'scrum', 'kanban', 'devops', 'ci/cd',
        'machine learning', 'deep learning', 'ai', 'data science', 'analytics',
        'excel', 'powerbi', 'tableau', 'sap', 'oracle', 'salesforce'
    ]

    for skill in tech_skills:
        if re.search(r'\b' + re.escape(skill) + r'\b', description_lower):
            skills_found.append(skill)

    # Remove duplicates and return as semicolon-separated string
    skills_found = list(dict.fromkeys(skills_found))  # Preserves order while removing dups
    return '; '.join(skills_found)

def standardize_experience(exp_str: str) -> Optional[float]:
    """Convert experience string to numeric years."""
    if pd.isna(exp_str) or not isinstance(exp_str, str):
        return None

    exp_str = exp_str.strip().lower()

    # Handle "X years" format
    year_match = re.search(r'(\d+(?:\.\d+)?)\s*years?', exp_str)
    if year_match:
        try:
            return float(year_match.group(1))
        except ValueError:
            pass

    # Handle "X-Jahre" (German)
    jahre_match = re.search(r'(\d+(?:\.\d+)?)\s*jahre?', exp_str)
    if jahre_match:
        try:
            return float(jahre_match.group(1))
        except ValueError:
            pass

    # Handle ranges like "2-4 years" or "3-5 Jahre"
    range_match = re.search(r'(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*(?:years?|jahre?)', exp_str)
    if range_match:
        try:
            min_val = float(range_match.group(1))
            max_val = float(range_match.group(2))
            return (min_val + max_val) / 2  # Return average
        except ValueError:
            pass

    # Handle entry level, senior level, etc.
    if any(term in exp_str for term in ['entry', 'einsteiger', 'junior', 'trainee']):
        return 1.0  # Assume 1 year for entry level
    elif any(term in exp_str for term in ['senior', 'lead', 'principal', 'architect']):
        return 7.0  # Assume 7+ years for senior
    elif any(term in exp_str for term in ['manager', 'director', 'head', 'leiter']):
        return 5.0  # Assume 5 years for management

    return None

def process_csv(input_path: str, output_path: str, report_path: str):
    """Main processing function."""
    logger.info(f"Reading CSV file from {input_path}")

    # Read the CSV file
    df = pd.read_csv(input_path)
    logger.info(f"Loaded {len(df)} rows and {len(df.columns)} columns")

    # Create a copy for processing
    df_clean = df.copy()

    # Track changes for reporting
    changes = {
        'total_rows': len(df),
        'columns_processed': [],
        'encoding_fixes': 0,
        'salary_parsing': 0,
        'location_cleaning': 0,
        'skills_extracted': 0,
        'experience_standardized': 0,
        'status_cleaning': 0
    }

    # 1. Fix column name: years_of_expereince -> years_of_experience
    if 'years_of_expereince' in df_clean.columns:
        df_clean = df_clean.rename(columns={'years_of_expereince': 'years_of_experience'})
        changes['columns_processed'].append('renamed years_of_expereince to years_of_experience')

    # 2. Fix encoding in text fields
    text_columns = ['company_name', 'job_title', 'job_category', 'job_location',
                   'job_description', 'skills', 'description_language', 'source']

    for col in text_columns:
        if col in df_clean.columns:
            original_values = df_clean[col].copy()
            df_clean[col] = df_clean[col].apply(fix_encoding)
            # Count changes
            changes['encoding_fixes'] += (original_values != df_clean[col]).sum()
            changes['columns_processed'].append(f'fixed encoding in {col}')

    # 3. Clean location field
    if 'job_location' in df_clean.columns:
        original_values = df_clean['job_location'].copy()
        df_clean['job_location'] = df_clean['job_location'].apply(clean_location)
        changes['location_cleaning'] += (original_values != df_clean['job_location']).sum()
        changes['columns_processed'].append('cleaned location formatting')

    # 4. Standardize salary data
    salary_cols = ['salary', 'min_salary', 'max_salary']
    salary_processed = False

    # First, parse salary column into min and max if they're empty
    if 'salary' in df_clean.columns:
        # Only process rows where min_salary and max_salary are both empty/null
        mask = (df_clean['min_salary'].isna() & df_clean['max_salary'].isna()) | \
               ((df_clean['min_salary'] == '') & (df_clean['max_salary'] == ''))

        if mask.any():
            logger.info(f"Parsing salary column for {mask.sum()} rows with empty min/max")
            salary_parsed = df_clean.loc[mask, 'salary'].apply(parse_salary)
            df_clean.loc[mask, 'min_salary'] = [x[0] for x in salary_parsed]
            df_clean.loc[mask, 'max_salary'] = [x[1] for x in salary_parsed]
            changes['salary_parsing'] += mask.sum()
            salary_processed = True

    # Also process any remaining salary values in min_salary/max_salary columns
    for col in ['min_salary', 'max_salary']:
        if col in df_clean.columns:
            original_values = df_clean[col].copy()
            # Convert string values to numeric where possible
            def clean_salary_val(val):
                if pd.isna(val) or val == '':
                    return None
                if isinstance(val, (int, float)):
                    return float(val)
                # Try to parse as string
                parsed_min, parsed_max = parse_salary(str(val))
                return parsed_min if col == 'min_salary' else parsed_max

            df_clean[col] = df_clean[col].apply(clean_salary_val)
            changes['salary_parsing'] += (~df_clean[col].isna() & original_values.isna()).sum()
            changes['columns_processed'].append(f'standardized {col}')

    # 5. Extract skills from description where skills is empty
    if 'skills' in df_clean.columns and 'job_description' in df_clean.columns:
        mask = df_clean['skills'].isna() | (df_clean['skills'] == '')
        if mask.any():
            logger.info(f"Extracting skills from description for {mask.sum()} rows")
            df_clean.loc[mask, 'skills'] = df_clean.loc[mask, 'job_description'].apply(
                extract_skills_from_description
            )
            changes['skills_extracted'] += mask.sum()
            changes['columns_processed'].append('extracted skills from description')

    # 6. Standardize experience
    if 'years_of_experience' in df_clean.columns:
        original_values = df_clean['years_of_experience'].copy()
        # Convert string experience to numeric
        def clean_experience(val):
            if pd.isna(val):
                return None
            if isinstance(val, (int, float)):
                return float(val)
            return standardize_experience(str(val))

        df_clean['years_of_experience'] = df_clean['years_of_experience'].apply(clean_experience)
        changes['experience_standardized'] += (~df_clean['years_of_experience'].isna() & original_values.isna()).sum()
        changes['columns_processed'].append('standardized experience')

    # 7. Clean status field - keep only Validated and Active, move others to processing_status
    if 'status' in df_clean.columns:
        original_values = df_clean['status'].copy()
        # Define valid job statuses
        valid_statuses = ['Validated', 'Active']

        # Create processing_status column for system statuses
        df_clean['processing_status'] = df_clean['status'].where(
            ~df_clean['status'].isin(valid_statuses),
            None
        )

        # Keep only valid statuses in status column
        df_clean['status'] = df_clean['status'].where(
            df_clean['status'].isin(valid_statuses),
            None  # or we could drop these rows, but let's keep them with null status
        )

        changes['status_cleaning'] = (~df_clean['processing_status'].isna() & original_values.isna()).sum() + \
                                   (df_clean['status'].isna() & ~original_values.isin(valid_statuses)).sum()
        changes['columns_processed'].append('cleaned status field (added processing_status)')

    # 8. Ensure numeric columns are actually numeric
    numeric_columns = ['min_salary', 'max_salary', 'years_of_experience']
    for col in numeric_columns:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')

    # Save the cleaned CSV
    logger.info(f"Saving cleaned CSV to {output_path}")
    df_clean.to_csv(output_path, index=False)

    # Generate report
    report = {
        'input_file': input_path,
        'output_file': output_path,
        'original_rows': changes['total_rows'],
        'cleaned_rows': len(df_clean),
        'processing_summary': changes,
        'data_quality_metrics': {
            'missing_salary_before': df['salary'].isna().sum() if 'salary' in df.columns else 0,
            'missing_salary_after': df_clean['min_salary'].isna().sum() + df_clean['max_salary'].isna().sum(),
            'missing_experience_before': df['years_of_expereince'].isna().sum() if 'years_of_expereince' in df.columns else 0,
            'missing_experience_after': df_clean['years_of_experience'].isna().sum(),
            'missing_skills_before': df['skills'].isna().sum() if 'skills' in df.columns else 0,
            'missing_skills_after': df_clean['skills'].isna().sum(),
            'encoding_artifacts_fixed': changes['encoding_fixes']
        }
    }

    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, default=str)

    logger.info(f"Processing complete. Report saved to {report_path}")
    logger.info(f"Original rows: {changes['total_rows']}, Cleaned rows: {len(df_clean)}")

    return df_clean, report

if __name__ == "__main__":
    input_file = r"D:\data_companies\job_data_cleaner\output\merged_vms_all_cleaned_final.csv"
    output_file = r"D:\data_companies\job_data_cleaner\output\merged_vms_all_cleaned_fixed_proper.csv"
    report_file = r"D:\data_companies\job_data_cleaner\output\cleaning_report.json"

    try:
        df_clean, report = process_csv(input_file, output_file, report_file)
        print("Data cleaning completed successfully!")
        print(f"Processed {len(df_clean)} rows")
        print(f"Report saved to {report_file}")
    except Exception as e:
        logger.error(f"Error during processing: {str(e)}", exc_info=True)
        raise