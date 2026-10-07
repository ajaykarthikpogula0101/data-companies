"""Create a normalized job CSV without modifying the scraper's source file.

The extractor is deliberately conservative: existing non-empty values win and
description-derived values are only added when an explicit textual signal is
present.  Previously saved LLM sidecar results can be merged without making
any network request.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

try:
    from .mojibake_fix import clean_with_mojibake_fix
except ImportError:  # Fallback for direct execution
    from mojibake_fix import clean_with_mojibake_fix

try:
    from .clean_jobs_extractors import (
        DEADLINE_RE as SAFE_DEADLINE_RE,
        EMPLOYMENT_PATTERNS as SAFE_EMPLOYMENT_PATTERNS,
        SENIORITY_PATTERNS as SAFE_SENIORITY_PATTERNS,
        experience as extract_experience,
        first_match as extract_first_match,
        salary as extract_salary,
        skills as extract_skills,
    )
    from .education_ontology import classify_education
except ImportError:  # Direct execution: python job_data_cleaner/clean_jobs.py
    from clean_jobs_extractors import (
        DEADLINE_RE as SAFE_DEADLINE_RE,
        EMPLOYMENT_PATTERNS as SAFE_EMPLOYMENT_PATTERNS,
        SENIORITY_PATTERNS as SAFE_SENIORITY_PATTERNS,
        experience as extract_experience,
        first_match as extract_first_match,
        salary as extract_salary,
        skills as extract_skills,
    )
    from education_ontology import classify_education




def clean(value: object) -> str:
    return clean_with_mojibake_fix(value)


OUTPUT_COLUMNS = [
    "company_name", "country", "website", "career_page_url", "status",
    "job_title", "job_category", "job_location", "posted_date",
    "application_deadline", "closed_date", "job_Status",
    "education_stream", "education_type", "education_qualification",
    "years_of_expereince", "seniority_level", "employment_type", "skills",
    "description_language", "job_description", "job_url", "salary",
    "min_salary", "max_salary", "source",
]

EMPTY = {"", "none", "null", "nan", "n/a", "na", "not specified", "unknown"}

EMPLOYMENT_PATTERNS = [
    ("Internship", r"\b(?:internship|intern|praktikum|stagiaire)\b"),
    ("Contract", r"\b(?:fixed[- ]term|contract(?:or)?|temporary|befristet|freelance)\b"),
    ("Part-time", r"\b(?:part[- ]time|teilzeit|temps partiel)\b"),
    ("Full-time", r"\b(?:full[- ]time|vollzeit|temps plein)\b"),
    ("Apprenticeship", r"\b(?:apprentice(?:ship)?|ausbildung|trainee program)\b"),
]

SENIORITY_PATTERNS = [
    ("Executive", r"\b(?:chief|c[etf]o|president|executive)\b"),
    ("Director", r"\b(?:director|vice president|\bvp\b)\b"),
    ("Manager", r"\b(?:manager|management)\b"),
    ("Lead", r"\b(?:team lead|tech lead|lead|head of)\b"),
    ("Senior", r"\b(?:senior|sr\.?|principal|staff)\b"),
    ("Entry", r"\b(?:junior|jr\.?|entry[- ]level|graduate|trainee|intern)\b"),
]

EDUCATION_PATTERNS = [
    ("PhD", r"\b(?:ph\.?d\.?|doctorate|doctoral)\b"),
    ("Master's", r"\b(?:master(?:'s)?|m\.?sc\.?|m\.?tech\.?|mba)\b"),
    ("Bachelor's", r"\b(?:bachelor(?:'s)?|b\.?sc\.?|b\.?tech\.?|undergraduate degree)\b"),
    ("Vocational", r"\b(?:vocational|trade school|technical diploma|apprenticeship)\b"),
    ("Diploma", r"\b(?:high school diploma|secondary school|ged|diploma)\b"),
]

STREAM_PATTERNS = [
    ("Computer Science", r"\b(?:computer science|software engineering|information technology|informatics)\b"),
    ("Engineering", r"\b(?:engineering|ingenieurwesen)\b"),
    ("Business Administration", r"\b(?:business administration|business studies|betriebswirtschaft|\bbwl\b)\b"),
    ("Finance / Accounting", r"\b(?:finance|accounting|controlling|economics)\b"),
    ("Marketing", r"\b(?:marketing|communications|public relations)\b"),
    ("Human Resources", r"\b(?:human resources|\bhr\b|people management)\b"),
    ("Law", r"\b(?:law|legal studies|juris doctorate)\b"),
    ("Medicine / Healthcare", r"\b(?:medicine|medical|nursing|healthcare|pharmacy)\b"),
    ("Data Science / Statistics", r"\b(?:data science|statistics|mathematics)\b"),
]

SKILL_VOCABULARY = [
    "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "Go", "Ruby", "PHP",
    "SQL", "Excel", "Power BI", "Tableau", "AWS", "Azure", "GCP", "Docker",
    "Kubernetes", "Git", "Linux", "React", "Angular", "Vue", "Node.js", ".NET",
    "Spring", "Django", "Flask", "FastAPI", "REST", "GraphQL", "Spark", "Hadoop",
    "TensorFlow", "PyTorch", "Machine Learning", "Data Analysis", "Project Management",
    "Agile", "Scrum", "SAP", "Salesforce", "English", "German", "French",
]

EXPERIENCE_PATTERNS = [
    re.compile(r"\b(?:minimum|min\.?|at least|mindestens)\s*(\d{1,2})(?:\s*(?:-|–|—|to)\s*(\d{1,2}))?\+?\s*(?:years?|yrs?|jahre[n]?)", re.I),
    re.compile(r"\b(\d{1,2})\s*(?:-|–|—|to)\s*(\d{1,2})\s*(?:years?|yrs?|jahre[n]?)", re.I),
    re.compile(r"\b(\d{1,2})\+?\s*(?:years?|yrs?|jahre[n]?)\s+(?:of\s+)?(?:professional\s+|relevant\s+|work\s+|berufs)?experience", re.I),
    re.compile(r"\b(?:experience|berufserfahrung)\s*(?:of|:)?\s*(\d{1,2})(?:\s*(?:-|–|—|to)\s*(\d{1,2}))?\+?\s*(?:years?|yrs?|jahre[n]?)", re.I),
]

SALARY_RE = re.compile(
    r"(?P<currency>USD|EUR|GBP|INR|AUD|CAD|CHF|JPY|CNY|[$€£₹¥])\s*"
    r"(?P<min>\d[\d,.]*\s*[kKmM]?)"
    r"(?:\s*(?:-|–|—|to)\s*(?:(?:USD|EUR|GBP|INR|AUD|CAD|CHF|JPY|CNY|[$€£₹¥])\s*)?"
    r"(?P<max>\d[\d,.]*\s*[kKmM]?))?",
    re.I,
)

DEADLINE_RE = re.compile(
    r"\b(?:application deadline|apply by|closing date|bewerbungsschluss)\s*[:\-]?\s*"
    r"((?:\d{4}-\d{2}-\d{2})|(?:\d{1,2}[./-]\d{1,2}[./-]\d{2,4})|"
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4})",
    re.I,
)


def row_id(row: dict[str, str]) -> str:
    identity = "\x1f".join(row.get(k, "") for k in ("company_name", "job_title", "job_url"))
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def first_match(text: str, patterns: list[tuple[str, str]]) -> str:
    for value, pattern in patterns:
        if re.search(pattern, text, re.I):
            return value
    return ""


def education_stream(text: str, education_type: str) -> str:
    """Only classify a stream when it occurs near an education requirement."""
    cue = re.compile(
        r"\b(?:degree|bachelor|master|ph\.?d|doctorate|diploma|qualification|"
        r"stud(?:y|ies)|education|abschluss|studium)\b",
        re.I,
    )
    for match in cue.finditer(text):
        window = text[max(0, match.start() - 180):match.end() + 220]
        stream = first_match(window, STREAM_PATTERNS)
        if stream:
            return stream
    return "" if not education_type else first_match(text[:500], STREAM_PATTERNS)


def experience(text: str) -> tuple[str, str, str]:
    for pattern in EXPERIENCE_PATTERNS:
        match = pattern.search(text)
        if match:
            low = int(match.group(1))
            high_group = match.group(2) if (match.lastindex or 0) >= 2 else None
            high = int(high_group) if high_group else low
            if 0 <= low <= high <= 80:
                display = f"{low}-{high} years" if low != high else f"{low} years"
                return display, str(low), str(high)
    return "", "", ""


def salary(text: str) -> tuple[str, str, str]:
    match = SALARY_RE.search(text)
    if not match:
        return "", "", ""
    whole = re.sub(r"\s+", " ", match.group(0)).strip()
    return whole, match.group("min").strip(), (match.group("max") or "").strip()


def skills(text: str) -> str:
    found = []
    for skill in SKILL_VOCABULARY:
        if re.search(r"(?<![\w+#.])" + re.escape(skill) + r"(?![\w+#.])", text, re.I):
            found.append(skill)
    return "; ".join(found)


def load_llm_results(path: Path | None) -> dict[str, dict]:
    results: dict[str, dict] = {}
    if not path or not path.exists():
        return results
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                item = json.loads(line)
                if item.get("row_id") and isinstance(item.get("result"), dict):
                    results[item["row_id"]] = item["result"]
            except json.JSONDecodeError:
                continue
    return results


def prefer(row: dict[str, str], key: str, derived: str = "") -> str:
    return clean(row.get(key)) or clean(derived)


def normalize_row(
    row: dict[str, str], llm: dict[str, dict], stats: "Stats | None" = None
) -> dict[str, str]:
    description = clean(row.get("job_description")) or clean(row.get("job_description_clean"))
    title_and_description = f"{clean(row.get('job_title'))}\n{description}"
    saved = llm.get(row_id(row), {})

    exp_display, exp_min, exp_max = extract_experience(title_and_description)
    saved_min = clean(saved.get("years_of_experience_min"))
    saved_max = clean(saved.get("years_of_experience_max"))
    low = clean(row.get("years_of_experience_min")) or saved_min or exp_min
    high = clean(row.get("years_of_experience_max")) or saved_max or exp_max
    existing_experience = clean(row.get("years_of_expereince"))
    if existing_experience:
        exp_display = existing_experience
    elif low:
        exp_display = f"{low}-{high} years" if high and high != low else f"{low} years"

    pay, pay_min, pay_max = extract_salary(description)

    # Education fields are independent. A generic type is never composed into
    # a qualification because that would manufacture a credential phrase.
    edu = classify_education(description, clean(saved.get("education_type")))
    education_type = prefer(row, "education_type", edu["education_type"].value)
    education_stream_value = prefer(row, "education_stream", edu["education_stream"].value)
    qualification = prefer(
        row,
        "education_qualification",
        clean(saved.get("education_qualification")) or edu["education_qualification"].value,
    )

    existing_skills = clean(row.get("skills"))
    llm_skills = clean(saved.get("skills"))
    extracted_skills = extract_skills(description)
    combined_skills = []
    for group in (existing_skills, llm_skills, extracted_skills):
        for item in re.split(r"\s*[,;|]\s*", group):
            if item and item.casefold() not in {x.casefold() for x in combined_skills}:
                combined_skills.append(item)

    deadline = SAFE_DEADLINE_RE.search(description)
    result = {
        "company_name": clean(row.get("company_name")),
        "country": clean(row.get("country")),
        "website": clean(row.get("website")),
        "career_page_url": clean(row.get("career_page_url")),
        "status": clean(row.get("career_page_status")) or clean(row.get("status")),
        "job_title": clean(row.get("job_title")),
        "job_category": clean(row.get("job_category")),
        "job_location": clean(row.get("job_location")),
        "posted_date": clean(row.get("posted_date")),
        "application_deadline": clean(row.get("application_deadline")) or (deadline.group(1) if deadline else ""),
        "closed_date": clean(row.get("closed_date")),
        "job_Status": clean(row.get("job_status")) or clean(row.get("job_Status")),
        "education_stream": education_stream_value,
        "education_type": education_type,
        "education_qualification": qualification,
        "years_of_expereince": exp_display,
        "seniority_level": prefer(
            row, "seniority_level",
            clean(saved.get("seniority_level"))
            or extract_first_match(clean(row.get("job_title")), SAFE_SENIORITY_PATTERNS),
        ),
        "employment_type": prefer(
            row,
            "employment_type",
            extract_first_match(title_and_description, SAFE_EMPLOYMENT_PATTERNS),
        ),
        "skills": "; ".join(combined_skills),
        "description_language": clean(row.get("description_language")),
        "job_description": description,
        "job_url": clean(row.get("job_url")),
        "salary": clean(row.get("salary")) or pay,
        "min_salary": clean(row.get("min_salary")) or pay_min,
        "max_salary": clean(row.get("max_salary")) or pay_max,
        "source": clean(row.get("source")),
    }
    if stats:
        for field in BACKFILLED_FIELDS:
            if clean(row.get(field)):
                source = "existing_column"
            elif result[field]:
                source = "derived_or_sidecar"
            else:
                source = "abstain"
            stats.record(field, source)
        for field in ("education_type", "education_stream", "education_qualification"):
            extraction = edu[field]
            if not clean(row.get(field)) and extraction.value:
                stats.confidence_counts[field][extraction.confidence] += 1
                stats.evidence_examples[field].append(extraction.evidence)
    return result


BACKFILLED_FIELDS = [
    "education_type", "education_stream", "education_qualification",
    "years_of_expereince", "salary", "min_salary", "max_salary", "skills",
    "employment_type", "seniority_level", "application_deadline",
]


class Stats:
    def __init__(self) -> None:
        self.source_counts: dict[str, Counter] = defaultdict(Counter)
        self.confidence_counts: dict[str, Counter] = defaultdict(Counter)
        self.evidence_examples: dict[str, list[str]] = defaultdict(list)

    def record(self, field: str, source: str) -> None:
        self.source_counts[field][source] += 1

    def report(self, rows: int, duplicates: int) -> dict:
        coverage = {}
        for field in BACKFILLED_FIELDS:
            sources = self.source_counts[field]
            filled = rows - sources["abstain"]
            coverage[field] = {
                "filled": filled,
                "abstained": sources["abstain"],
                "coverage_pct": round(100 * filled / rows, 2) if rows else 0.0,
                "source_breakdown": dict(sources),
                "confidence_breakdown": dict(self.confidence_counts[field]),
                "evidence_examples": [x for x in self.evidence_examples[field][:5] if x],
            }
        return {
            "source_row_count": rows,
            "output_row_count": rows,
            "duplicate_row_count": duplicates,
            "schema_ok": True,
            "expected_columns": OUTPUT_COLUMNS,
            "field_coverage": coverage,
        }


def process(
    input_path: Path,
    output_path: Path,
    llm_path: Path | None,
    report_path: Path | None = None,
) -> tuple[int, int]:
    llm = load_llm_results(llm_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = 0
    jobs = 0
    duplicates = 0
    seen_ids: set[str] = set()
    stats = Stats()
    with input_path.open(encoding="utf-8-sig", newline="") as source, output_path.open(
        "w", encoding="utf-8-sig", newline=""
    ) as destination:
        reader = csv.DictReader(source)
        writer = csv.DictWriter(destination, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in reader:
            identity = row_id(row)
            if identity in seen_ids:
                duplicates += 1
            seen_ids.add(identity)
            writer.writerow(normalize_row(row, llm, stats))
            rows += 1
            jobs += bool(clean(row.get("job_title")))
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(stats.report(rows, duplicates), indent=2), encoding="utf-8")
    return rows, jobs


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize and backfill job data from descriptions")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--llm-results", type=Path, help="Existing JSONL sidecar to reuse; no API calls are made")
    parser.add_argument("--report", type=Path, help="Write a JSON validation report")
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        parser.error("output must differ from input; the source CSV is never overwritten")
    rows, jobs = process(args.input, args.output, args.llm_results, args.report)
    print(f"Wrote {rows:,} rows ({jobs:,} job rows) to {args.output}")
    if args.report:
        print(f"Validation report: {args.report}")


if __name__ == "__main__":
    main()