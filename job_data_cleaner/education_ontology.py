"""Evidence-based, independently classified education fields."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Extraction:
    value: str = ""
    confidence: str = ""
    evidence: str = ""
    source: str = ""


STRONG_LEVELS = [
    ("Doctorate", r"\b(?:ph\.?\s?d\.?|doctorate|doctoral degree|dphil)\b"),
    ("Master's", r"\b(?:master'?s(?:\s+degree)?|m\.?\s?sc\.?|m\.?\s?tech\.?|m\.?\s?eng\.?|mba|m\.?\s?com\.?)\b"),
    ("Bachelor's", r"\b(?:bachelor'?s(?:\s+degree)?|b\.?\s?sc\.?|b\.?\s?tech\.?|b\.?\s?eng\.?|b\.?\s?com\.?|undergraduate degree|ll\.?\s?b\.?)\b|(?-i:\bB\.\s?E\.)"),
    ("Associate Degree", r"\b(?:associate'?s?\s+degree|associate\s+of\s+(?:arts|science))\b"),
    # ENHANCED: Traditional German degrees
    ("Master's Equivalent", r"\b(?:diplom-(?:ingenieur|architekt|wirt)|magister|magister\s+artium)\b"),
    ("Bachelor's Equivalent", r"\b(?:bakkalarius|diplom-(?:fh|fhs))\b"),
    ("State Examination", r"\b(?:staatsexamen|staatlich\s+geprüft)\b"),
    ("Master Craftsman", r"\b(?:meister(?:in)?|meisterbrief)\b"),
    ("Technician", r"\b(?:techniker|staatlich\s+geprüfter\s+techniker)\b"),
]

WEAK_LEVELS = [
    ("Professional Certification", r"\b(?:professional certification|industry certification|certified\s+\w+(?:\s+professional)?|certificate\s+(?:iv|iii|program)|licensure)\b"),
    # ADDED: Additional German vocational/education terms (more specific first)
    ("Vocational Certificate", r"\b(?:facharbeiter|gesellenbrief|ibb)\b"),
    ("Technical School", r"\b(?:technikerschule|fachschulreife|fachschulausbildung)\b"),
    ("College of Applied Sciences", r"\b(?:fachhochschule|fachhochschulabschluss|fh)\b"),
    ("Cooperative Education", r"\b(?:berufsakademie|duales\s+studium)\b"),
    ("Apprenticeship", r"\b(?:apprentice(?:ship)?|ausbildung|dual\s+study\s+program|traineeship|lehrabschluss|berufsausbildung)\b"),
    ("Vocational Training", r"\b(?:vocational (?:training|education|school|qualification)|trade school|technical (?:diploma|school)|berufsschule|tvet|berufsfachschule|fachschule|berufskolleg)\b"),
    ("Secondary / High School", r"\b(?:high school diploma|secondary school(?: certificate| diploma)?|ged|matriculation|10\+2|senior secondary|secondary education)\b"),
    ("Diploma", r"\b(?:post[- ]?secondary diploma|hnd|higher national diploma|diploma)\b"),
]

STREAMS = [
    ("Computer Science / IT", r"\b(?:computer science|software engineering|information technology|informatics|computer engineering|informatik|informationstechnologie|anwendungsentwicklung|systemintegration)\b"),
    ("Data Science / Statistics", r"\b(?:data science|statistics|applied mathematics|datenwissenschaft|statistik|angewandte\ mathematik)\b"),
    ("Business Administration", r"\b(?:business administration|business studies|mba|betriebswirtschaft|lwu|lw|wae|wirtschaftsingenieurwesen|handelswirtschaft|Betriebswirtschaftslehre|Wirtschaft)\b"),
    ("Finance / Accounting", r"\b(?:finance|accounting|controlling|economics|finanzwesen|rechnungswesen|controlling|kontrolling)\b"),
    ("Marketing", r"\b(?:marketing|communications|public relations|marketing|kommunikation|public relations)\b"),
    ("Human Resources", r"\b(?:human resources|hr|people management|Personalwesen|personalentwicklung)\b"),
    ("Law", r"\b(?:law|legal studies|juris doctor|rechtswissenschaften|jurist)\b"),
    ("Medicine / Healthcare", r"\b(?:medicine|medical|nursing|healthcare|pharmacy|medizin|medizinische|pharmazeutisch)\b"),
    ("Engineering (General)", r"\bengineering\b"),
    # ADDED: German-specific engineering streams
    ("Engineering (German)", r"\b(?:ingenieurwesen|maschinenbau|elektrotechnik|mechatronik|fahrzeugtechnik|verfahrenstechnik)\b"),
    ("Architecture", r"\b(?:architecture|architektur|stadtplanung|landschaftsarchitektur)\b"),
]

CUE = re.compile(
    r"\b(?:degree|education|qualification|academic|diploma|certificat\w*|stud(?:y|ies)|"
    r"graduate|abschluss|studium|ausbildung|beruf|lehre|fach|minimum education|required qualifications?)\b",
    re.I,
)

QUALIFICATION = re.compile(
    r"\b(?:bachelor'?s?(?: degree)?|master'?s?(?: degree)?|ph\.?\s?d\.?|doctorate|mba|"
    r"b\.?\s?tech\.?|m\.?\s?tech\.?|b\.?\s?sc\.?|m\.?\s?sc\.?|"
    r"associate'?s? degree|high school diploma|post[- ]secondary diploma|apprenticeship|"
    r"vocational (?:training|qualification)|(?-i:B\.\s?E\.))"
    r"(?:\s+(?:degree\s+)?(?:of|in)\s+[A-Za-z][A-Za-z &,/\-]{2,50})?",
    re.I,
)


def cue_windows(text: str) -> list[tuple[int, str]]:
    windows = []
    for m in CUE.finditer(text):
        # Increased window sizes to better capture German compound words and phrases
        # German often has longer compound words and more descriptive phrases
        start = max(0, m.start() - 100)  # Increased from 60
        end = min(len(text), m.end() + 300)  # Increased from 220
        windows.append((start, text[start:end]))
    return windows


def first_match_in_list_order(text: str, patterns: list[tuple[str, str]]):
    """Find the first matching pattern in list order (not text position order)."""
    for value, pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return (match.start(), value, match)
    return None


def earliest(text: str, patterns: list[tuple[str, str]]):
    """Find the earliest match in text position order (kept for backward compatibility)."""
    candidates = []
    for value, pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            candidates.append((match.start(), value, match))
    return min(candidates, default=None, key=lambda item: item[0])


def classify_type(text: str, labeled_value: str = "") -> Extraction:
    if labeled_value:
        hit = earliest(labeled_value, STRONG_LEVELS + WEAK_LEVELS)
        if hit:
            return Extraction(hit[1], "medium", labeled_value.strip()[:200], "llm_sidecar")
    hit = earliest(text, STRONG_LEVELS)
    if hit:
        _, value, match = hit
        evidence = text[max(0, match.start() - 30):match.end() + 30].strip()
        return Extraction(value, "high", evidence, "context_window")
    # First try WEAK_LEVELS within cue windows (priority-based matching)
    candidates = []
    for offset, window in cue_windows(text):
        hit = first_match_in_list_order(window, WEAK_LEVELS)
        if hit:
            candidates.append((offset + hit[0], hit[1], hit[2], window))
    if candidates:
        _, value, match, window = min(candidates, key=lambda item: item[0])
        evidence = window[max(0, match.start() - 20):match.end() + 20].strip()
        return Extraction(value, "medium", evidence, "context_window")
    # Fallback: try WEAK_LEVELS on whole text if no cue windows found (priority-based)
    hit = first_match_in_list_order(text, WEAK_LEVELS)
    if hit:
        _, value, match = hit
        evidence = text[max(0, match.start() - 20):match.end() + 20].strip()
        return Extraction(value, "medium", evidence, "context_window")
    return Extraction()


def classify_stream(text: str) -> Extraction:
    candidates = []
    for offset, window in cue_windows(text):
        hit = first_match_in_list_order(window, STREAMS)
        if hit:
            candidates.append((offset + hit[0], hit[1], hit[2], window))
    if not candidates:
        return Extraction()
    _, value, match, window = min(candidates, key=lambda item: item[0])
    evidence = window[max(0, match.start() - 15):match.end() + 15].strip()
    return Extraction(value, "medium", evidence, "context_window")


def classify_education(text: str, labeled_value: str = "") -> dict[str, Extraction]:
    edu_type = classify_type(text, labeled_value)
    stream = classify_stream(text)
    qualification = Extraction()
    for _, window in cue_windows(text):
        match = QUALIFICATION.search(window)
        if match:
            phrase = re.sub(r"\s+", " ", match.group(0)).strip().rstrip(",;:")
            qualification = Extraction(phrase[:160], "medium", phrase[:160], "context_window")
            break
    return {
        "education_type": edu_type,
        "education_stream": stream,
        "education_qualification": qualification,
    }
