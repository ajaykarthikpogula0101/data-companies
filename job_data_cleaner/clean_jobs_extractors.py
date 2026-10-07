"""Conservative extractors for non-education fields.

Every function abstains with an empty string when explicit evidence is absent.
"""

from __future__ import annotations

import re

EMPLOYMENT_PATTERNS = [
    ("Internship", r"\b(?:internship|intern|praktikum|stagiaire)\b"),
    ("Contract", r"\b(?:fixed[- ]term|contract(?:or)?|temporary|befristet|freelance)\b"),
    ("Part-time", r"\b(?:part[- ]time|teilzeit|temps partiel)\b"),
    ("Full-time", r"\b(?:full[- ]time|vollzeit|temps plein)\b"),
    ("Apprenticeship", r"\b(?:apprentice(?:ship)?|ausbildung|trainee program)\b"),
]

SENIORITY_PATTERNS = [
    ("Executive", r"\b(?:chief|c[etf]o|president|executive)\b"),
    ("Director", r"\b(?:director|vice president|vp)\b"),
    ("Manager", r"\b(?:manager|management)\b"),
    ("Lead", r"\b(?:team lead|tech lead|lead|head of)\b"),
    ("Senior", r"\b(?:senior|sr\.?|principal|staff)\b"),
    ("Entry", r"\b(?:junior|jr\.?|entry[- ]level|graduate|trainee|intern)\b"),
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
    # ENHANCED: German experience patterns - ranges first (more specific)
    re.compile(r'(\d+(?:[.,]\d+)?)\s*(?:-|–|—|to)\s*(\d+(?:[.,]\d+)?)\s*(?:jahre?|j\.?)\s*(?:berufserfahrung|erfahrung|praxis|erfaring)', re.I),  # X-Y Jahre Berufserfahrung
    re.compile(r'(?:mindestens|min\.?|at least)\s*(\d+(?:[.,]\d+)?)\s*(?:-|–|—|to)\s*(\d+(?:[.,]\d+)?)\s*(?:jahre?|j\.?)', re.I),  # mindestens X-Y Jahre
    # Standard experience patterns
    re.compile(r"\b(?:minimum|min\.?|at least|mindestens)\s*(\d{1,2})(?:\s*(?:-|–|—|to)\s*(\d{1,2}))?\+?\s*(?:years?|yrs?|jahre[n]?)", re.I),
    re.compile(r"\b(\d{1,2})\s*(?:-|–|—|to)\s*(\d{1,2})\s*(?:years?|yrs?|jahre[n]?)", re.I),
    re.compile(r"\b(\d{1,2})\+?\s*(?:years?|yrs?|jahre[n]?)\s+(?:of\s+)?(?:professional\s+|relevant\s+|work\s+|berufs)?experience", re.I),
    re.compile(r"\b(?:experience|berufserfahrung)\s*(?:of|:)?\s*(\d{1,2})(?:\s*(?:-|–|—|to)\s*(\d{1,2}))?\+?\s*(?:years?|yrs?|jahre[n]?)", re.I),
    # ENHANCED: German experience patterns - single values
    re.compile(r'(\d+(?:[.,]\d+)?)\s*(?:jahre?|j\.?)\s*(?:berufserfahrung|erfahrung|praxis|erfaring)', re.I),  # X Jahre Berufserfahrung
    re.compile(r'(?:mindestens|min\.?|at least)\s*(\d+(?:[.,]\d+)?)\s*(?:jahre?|j\.?)', re.I),  # mindestens X Jahre
    re.compile(r'(\d+(?:[.,]\d+)?)\s*\+\s*(?:jahre?|j\.?)', re.I),  # X+ Jahre
    re.compile(r'(?:einige|mehrere|zahlreiche|several|various)\s*(\d+(?:[.,]\d+)?)\s*(?:jahre?|j\.?)', re.I),  # mehrere X Jahre
    re.compile(r'(\d+(?:[.,]\d+)?)\s*(?:jahre?|j\.?)\s*(?:\+|and above|and more|oder mehr|etc)', re.I),  # X Jahre und above
    re.compile(r'(\d+(?:[.,]\d+)?)\s*(?:jahre?|j\.?)\s*(?:und\s+above|und\s+mehr)', re.I),  # X Jahre und mehr
    re.compile(r'(\d+(?:[.,]\d+)?)\s*(?:monate?|mt\.?)\s*(?:mindestens|min\.?|at least)', re.I),  # X Monate mindestens
    # Handle implicit experience like "mehrjährige Erfahrung" - assign a default value
    re.compile(r'(?:mehrjährige|mehrjähre|langjährige)\s*erfahrung', re.I),  # mehrjährige Erfahrung
]

SALARY_RE = re.compile(
    r"(?P<currency>USD|EUR|GBP|INR|AUD|CAD|CHF|JPY|CNY|[$€£₹¥])\s*"
    r"(?P<min>\d[\d,.]*\s*[kKmM]?)"
    r"(?:\s*(?:-|–|—|to)\s*(?:(?:USD|EUR|GBP|INR|AUD|CAD|CHF|JPY|CNY|[$€£₹¥])\s*)?"
    r"(?P<max>\d[\d,.]*\s*[kKmM]?))?",
    re.I,
)

# ENHANCED: German salary patterns
GERMAN_SALARY_PATTERNS = [
    # Handle salary ranges first (more specific)
    re.compile(r'(?P<min>\d{1,3}(?:[.]\d{3})*(?:[,]\d+)?)\s*(?:-|–|—|to)\s*(?P<max>\d{1,3}(?:[.]\d{3})*(?:[,]\d+)?)\s*(?:€|eur|euro)', re.I),  # 60.000-112.000€
    re.compile(r'(?P<min>\d+(?:[,]\d+)?)\s*(?:-|–|—|to)\s*(?P<max>\d+(?:[,]\d+)?)\s*(?:k|tausend)\s*(?:eur|euro)', re.I),      # 60k-100k euro
    # Handle salary with qualifiers
    re.compile(r'(?:je\s+nach\s+qualifikation\s+und\s+erfahrung\s*,?\s*)(?:bietet|zahlen?)\s*(?P<min>\d{1,3}(?:[.]\d{3})*(?:[,]\d+)?)\s*(?:-|–|—|to)?\s*(?P<max>\d{1,3}(?:[.]\d{3})*(?:[,]\d+)?)\s*(?:€|eur|euro)', re.I),  # "Je nach Qualifikation und Erfahrung bieten wir X-XXX.XXX€"
    # Handle German number formatting (dots as thousands, comma as decimal) - single values
    re.compile(r'(?:ab\s*|von\s*)(?P<min>\d{1,3}(?:[.]\d{3})*(?:[,]\d+)?)\s*(?:€|eur|euro)', re.I),  # ab 31.640 €
    re.compile(r'(?P<min>\d{1,3}(?:[.]\d{3})*(?:[,]\d+)?)\s*(?:€|eur|euro)\s*(?:brutto|p\.?a\.?\.?|mtl\.)', re.I),  # 60.000€ brutto/Jahr
    re.compile(r'(?P<min>\d+(?:[,]\d+)?)\s*(?:k€|td|tausend\s*€)', re.I),             # 60k€
    re.compile(r'(?P<min>\d+(?:[,]\d+)?)\s*(?:k|tausend)\s*(?:eur|euro)', re.I),      # 60k euro
    re.compile(r'(?P<min>\d+)\s*tausend\s*€', re.I),                                 # 60 Tausend €
    # Handle general patterns (less specific) - PUT THESE LAST to avoid matching ranges incorrectly
    re.compile(r'(?P<min>\d{1,3}(?:[.]\d{3})*(?:[,]\d+)?)\s*(?:€|eur|euro)', re.I),  # 60.000€ or 60.000,50€
]

DEADLINE_RE = re.compile(
    r"\b(?:application deadline|apply by|closing date|bewerbungsschluss)\s*[:\-]?\s*"
    r"((?:\d{4}-\d{2}-\d{2})|(?:\d{1,2}[./-]\d{1,2}[./-]\d{2,4})|"
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4})",
    re.I,
)


def first_match(text: str, patterns: list[tuple[str, str]]) -> str:
    for value, pattern in patterns:
        if re.search(pattern, text, re.I):
            return value
    return ""


def experience(text: str) -> tuple[str, str, str]:
    for pattern in EXPERIENCE_PATTERNS:
        match = pattern.search(text)
        if match:
            # Handle patterns with different numbers of capture groups
            if match.lastindex and match.lastindex >= 1:
                low = int(float(match.group(1)))  # Handle decimal numbers
            else:
                # No capture groups found (like "mehrjährige Erfahrung")
                # Assign a default value for implicit experience
                # Based on context, "mehrjährige" typically means 2+ years
                low = 2

            high_group = match.group(2) if (match.lastindex or 0) >= 2 else None
            high = int(float(high_group)) if high_group else low

            # Validate reasonable ranges (0-80 years)
            if 0 <= low <= high <= 80:
                display = f"{low}-{high} years" if low != high else f"{low} years"
                return display, str(low), str(high)
    return "", "", ""


def salary(text: str) -> tuple[str, str, str]:
    # First try the original salary pattern
    match = SALARY_RE.search(text)
    if match:
        whole = re.sub(r"\s+", " ", match.group(0)).strip()
        return whole, match.group("min").strip(), (match.group("max") or "").strip()

    # If no match, try German-specific patterns
    for pattern in GERMAN_SALARY_PATTERNS:
        match = pattern.search(text)
        if match:
            whole = re.sub(r"\s+", " ", match.group(0)).strip()
            min_val = match.group("min").strip() if match.group("min") else ""
            # Safely get max group - some patterns don't have it
            max_val = ""
            if match.lastindex and match.lastindex >= 2:  # Check if there are at least 2 groups
                try:
                    max_val = match.group("max").strip() if match.group("max") else ""
                except IndexError:
                    # No max group in this pattern
                    max_val = ""
            return whole, min_val, max_val

    return "", "", ""


def skills(text: str) -> str:
    found = []
    for skill_name in SKILL_VOCABULARY:
        if re.search(r"(?<![\w+#.])" + re.escape(skill_name) + r"(?![\w+#.])", text, re.I):
            found.append(skill_name)
    return "; ".join(found)