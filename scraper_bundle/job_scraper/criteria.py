"""C-level + department selection criteria for the Hiring_OCT2026 delivery.

The client's workbook has two sheets:

* ``careers_Link`` -- companies with the URL of their career page.
* ``Columns`` -- the output layout plus the *selection* rules:
    - column C lists C-level titles (GM / General Manager, MD / Managing
      Director, Chief, CEO, CTO, CIO, COO, Chairman, President, Owner,
      Partner, CFO, Founder, ...);
    - columns D-H list the keywords for the five departments we care about:
      Operations, Procurement, Finance, IT and Purchasing (Finance also has
      an extra block on row 40).

A posting is delivered only when its title is C-level **and** it belongs to
one of those five departments.  This module encodes that logic and can load
the exact keyword lists straight out of the workbook, so the rules always
match what the client put in the sheet.
"""
import re

import openpyxl

# ---------------------------------------------------------------------------
# Built-in defaults (mirror the Columns sheet).  load_criteria_from_excel()
# replaces these with the workbook's actual values when available.
# ---------------------------------------------------------------------------

# C-suite / owner abbreviations and the handful of non-"Chief" C-level words.
# "MD" is deliberately NOT matched as a bare abbreviation: in job titles it is
# usually a US state ("Suitland, MD") or a medical degree.  Managing Director
# is caught by its spelled-out pattern below.
_C_ABBR = re.compile(
    r"\b(?:ceo|cfo|coo|cto|cio|cmo|chro|ciso|cro|cpo|cdo|cso|clo|cao|csco"
    r"|gm)\b", re.I)
_CHIEF = re.compile(r"\bchief\b", re.I)
_GENERAL_MANAGER = re.compile(r"\bgeneral\s+manager\b", re.I)
_MANAGING_DIRECTOR = re.compile(r"\bmanaging\s+director\b", re.I)
# "Vice President", "VP", "SVP", "EVP" (and hyphenated "Vice-President")
# are V-level, not C-level, so president is matched only when it is not
# preceded by "vice" (space or hyphen).
_PRESIDENT = re.compile(
    r"(?<!vice[\s-])\bpresident\b|\b(?:chairman|chairwoman|chairperson|chair)\b",
    re.I)
_OWNER = re.compile(r"\bowner\b", re.I)
_PARTNER = re.compile(r"\bpartner\b", re.I)
_FOUNDER = re.compile(r"\b(?:founder|co-?founder)\b", re.I)

# "Product Owner", "Process Owner", "Data Owner" ... are individual-contributor
# roles, not C-level.  Strip them before testing for the bare word "owner".
_NOT_OWNER = re.compile(
    r"\b(?:process|product|service|data|risk|system|application|platform|"
    r"feature|epic|story|control|capability|workflow|business\s+process|"
    r"technical|solution)\s+owner\b", re.I)

# "People Business Partner", "HR Business Partner", "Finance Business
# Partner" ... are manager/individual-contributor roles, not C-level.  Strip
# these before testing for the bare word "partner" (which still catches a
# law/consulting "Partner" or "Managing Partner").
_NOT_PARTNER = re.compile(
    r"\b(?:people|hr|human\s+resources?|talent(?:\s+acquisition)?|"
    r"recruit\w*|client|account|channel|sales|business|strategic|technology|"
    r"it|finance|procurement|operations)\s+(?:business\s+)?partner\b", re.I)

# HR/talent partner titles are not IT (or another target department) merely
# because the title mentions "Technology".
_HR_PARTNER = re.compile(
    r"\b(?:people|hr|human\s+resources?|talent|recruit\w*)\b"
    r"(?:\s+\w+){0,4}\s+partner\b", re.I)

_C_LEVEL_PATTERNS = (
    _C_ABBR, _CHIEF, _GENERAL_MANAGER, _MANAGING_DIRECTOR, _PRESIDENT,
    _OWNER, _PARTNER, _FOUNDER,
)

# V-level: Vice President (space or hyphen), VP / SVP / EVP / AVP.
_VICE_PRESIDENT = re.compile(r"\bvice[\s-]?president\b|\b(?:vp|svp|evp|avp)\b",
                             re.I)

# D-level: Director / Directors ("Managing Director" stays C-level, checked
# first by is_c_level).
_DIRECTOR = re.compile(r"\bdirectors?\b", re.I)

# H-level: any "Head" role -- "Head of ...", "Head, ...", "Head - ...",
# "Head Office Manager", "Department Head", etc.  A bare "Head" word with a
# word boundary is enough; compounds like "Headquarters" do not match.
_HEAD = re.compile(r"\bhead\b", re.I)

# Department -> keyword list.  Order matters: the first department whose
# keyword matches wins, so Operations is checked before Procurement etc.
_DEPARTMENT_KEYWORDS = {
    "Operations": [
        "Operations", "Operation", "Operational", "Business Operations",
        "Business Operations Management", "Operational Management",
        "Operations Management", "Operations Manager", "Operations Director",
        "Operations Coordinator", "Operations Analyst", "Operations Specialist",
        "Operations Executive", "Operations Officer", "Process Management",
        "Process Improvement", "Process Excellence", "Business Process",
        "Workflow", "Service Operations", "Field Operations",
        "Manufacturing Operations", "Production", "Production Operations",
        "Production Manager", "Plant Operations", "Plant Manager",
        "Facility Operations", "Facilities", "Administration", "Administrator",
        "Administrative", "Office Administration", "Service Delivery",
        "Service Delivery Manager", "Delivery", "Delivery Operations",
        "Resource Management", "Workforce Management", "Capacity Planning",
        "Operational Excellence", "Continuous Improvement", "Quality Operations",
        "Logistics",
    ],
    "Procurement": [
        "Procurement", "Procurements", "Procurement Director",
        "Procurement Specialist", "Procurement Analyst", "Procurement Officer",
        "Procurement Coordinator", "Procurement Executive",
        "Strategic Procurement", "Procurement Operations",
        "Procurement Management", "Sourcing", "Strategic Sourcing",
        "Sourcing Manager", "Sourcing Director", "Sourcing Specialist",
        "Strategic Sourcing Manager", "Supplier Sourcing",
        "Supplier Management", "Supplier Relationship Management",
        "Vendor Management", "Vendor Manager", "Vendor Management Specialist",
        "Vendor Relations", "Supply Chain", "Purchasing", "Purchase",
        "Purchasing Manager", "Purchasing Director", "Purchasing Specialist",
        "Purchasing Agent", "Purchasing Officer", "Purchasing Coordinator",
        "Purchasing Analyst", "Purchasing Executive", "Purchase Manager",
        "Purchase Officer", "Purchase Coordinator", "Purchase Executive",
        "Purchase Order", "Order Management", "Buying", "Buyer Management",
        "Commodity Buyer", "Category Buyer", "Category Manager",
        "Merchandise Buyer", "Retail Buyer", "Procurement Buyer",
        "Vendor Buyer", "Supplier Buyer", "Material Buyer",
        "Raw Material Buyer", "Receivable",
    ],
    "Finance": [
        "Accounting", "Payable", "Receivable", "Controller", "Bookkeeper",
        "Treasurer", "Audit", "Banking", "Budget", "Actuarial", "Collections",
        "Loan", "Mortgage", "Risk", "Tax", "Compliance", "Payroll",
        "Receivabl", "Financial Planning", "FP&A",
        "Financial Planning & Analysis",
    ],
    "IT": [
        "Information Technology", "Technology", "Technical", "Application",
        "Applications", "System", "Systems", "Software", "Data",
        "Data Centre", "Data Center", "Analytics", "Platform", "Security",
        "Cyber", "Cybersecurity", "Privacy", "Infrastructure", "Cloud",
        "Network", "Database", "Architecture", "Developer", "Development",
        "Programming", "Engineering", "Automation", "Artificial Intelligence",
        "Machine Learning", "Technology Operations", "IT Operations",
        "Information",
    ],
    "Purchasing": [
        "Purchasing", "Purchase", "Purchaser", "Purchasing Agent",
        "Purchasing Buyer", "Buyer", "Senior Buyer", "Lead Buyer",
        "Junior Buyer", "Purchasing Manager", "Purchasing Director",
        "Purchasing Specialist", "Purchasing Officer", "Purchasing Coordinator",
        "Purchasing Analyst", "Purchasing Executive", "Purchase Manager",
        "Purchase Officer", "Purchase Coordinator", "Purchase Executive",
        "Purchase Order", "Order Management", "Buying", "Buyer Management",
        "Commodity Buyer", "Category Buyer", "Category Manager",
        "Merchandise Buyer", "Retail Buyer", "Procurement Buyer",
        "Vendor Buyer", "Supplier Buyer", "Material Buyer",
        "Raw Material Buyer",
    ],
}

# Inflection stems added on top of the exact keywords.  These are department
# specific so a stem can never leak into another department's matcher.
_DEPARTMENT_STEMS = {
    "Operations": [r"\boperat(?:e|es|ed|ing|ion|ions|ional|ive)\b"],
    "Procurement": [r"\bprocure\w*", r"\bsourc\w*", r"\bsupplier\w*",
                    r"\bvendor\w*"],
    "Finance": [r"\baccount\w*", r"\bfinanc\w*", r"\btreasur\w*",
                r"\baudit\w*", r"\bactuar\w*", r"\bcontroller\w*",
                r"\bpayroll\w*", r"\bcomplian\w*"],
    "IT": [r"\btechnolog\w*", r"\binformation\b"],
    "Purchasing": [r"\bpurchas\w*", r"\bbuyer\w*"],
}

# Unambiguous C-suite abbreviations -> department.  Used only when the title
# carries no department keyword (e.g. a bare "COO").
_ABBR_DEPARTMENT = {
    "coo": "Operations",
    "cfo": "Finance",
    "cto": "IT",
    "cio": "IT",
    "ciso": "IT",
    "cdo": "IT",
    "csco": "Procurement",
}

# Section headers in the Columns sheet's C column that are not titles.
_SECTION_HEADERS = {
    "PROCUREMENT / PURCHASING C-LEVEL", "OPERATIONS C-LEVEL",
    "ENGINEERING / PRODUCT", "LEGAL", "HEALTHCARE", "CUSTOMER / SALES",
    "ADMINISTRATION",
}

_TARGET_DEPARTMENTS = tuple(_DEPARTMENT_KEYWORDS.keys())


def _word_pattern(keyword):
    """Regex for one keyword: word-boundary phrase match, case-insensitive."""
    return r"\b" + re.escape(keyword) + r"\b"


def _compile_department(name, keywords):
    """Combine a department's keywords + stems into one alternation regex."""
    parts = [_word_pattern(k) for k in keywords]
    parts += _DEPARTMENT_STEMS.get(name, [])
    return re.compile("|".join(parts), re.I)


class Criteria:
    """C-level + department selection rules for a delivery run."""

    def __init__(self, c_level_patterns=_C_LEVEL_PATTERNS,
                 department_keywords=None, target_departments=None):
        self.c_level_patterns = tuple(c_level_patterns)
        self.department_keywords = dict(
            department_keywords or _DEPARTMENT_KEYWORDS)
        self.target_departments = tuple(
            target_departments or self.department_keywords.keys())
        self._department_re = {
            name: _compile_department(name, kws)
            for name, kws in self.department_keywords.items()
        }

    # -- C-level ---------------------------------------------------------
    def is_c_level(self, title):
        title = (title or "").strip()
        if not title:
            return False
        cleaned = _NOT_OWNER.sub(" ", title)
        cleaned = _NOT_PARTNER.sub(" ", cleaned)
        for pattern in self.c_level_patterns:
            if pattern.search(cleaned):
                return True
        return False

    # -- V / H / D level --------------------------------------------------
    def is_v_level(self, title):
        return bool(title) and bool(_VICE_PRESIDENT.search(title or ""))

    def is_h_level(self, title):
        return bool(title) and bool(_HEAD.search(title or ""))

    def is_d_level(self, title):
        return bool(title) and bool(_DIRECTOR.search(title or ""))

    def is_senior_level(self, title):
        """True for C-level, V-level (Vice President), H-level (Head of) or
        D-level (Director)."""
        return self.is_c_level(title) or self.is_v_level(title) or \
            self.is_h_level(title) or self.is_d_level(title)

    def seniority_label(self, title):
        """C-Level / V-Level / H-Level / D-Level for a title, or '' when
        below D."""
        if self.is_c_level(title):
            return "C-Level"
        if self.is_v_level(title):
            return "V-Level"
        if self.is_h_level(title):
            return "H-Level"
        if self.is_d_level(title):
            return "D-Level"
        return ""

    # -- department ------------------------------------------------------
    def classify_department(self, title, description=""):
        """Department name for a posting, or "" when none of the five match.

        Resolution order:
          1. department keywords in the title;
          2. an unambiguous C-suite abbreviation (COO -> Operations, ...);
          3. department keywords in the opening of the description (for
             generic C-level titles such as a bare "COO" whose posting is
             clearly an operations role).
        """
        title_text = title or ""
        # HR / talent partners are not IT just because "Technology" appears
        # in the title (e.g. "People Business Partner, Optum Technology").
        if _HR_PARTNER.search(title_text):
            return ""
        # "Chief IT Officer", "Head of IT", "IT Director" -- bare "IT" would
        # flood the keyword regex with the common word "it", so it is matched
        # case-sensitively here and only on the title.
        if re.search(r"\bIT\b", title_text) and "IT" in self.target_departments:
            return "IT"
        for name in self.target_departments:
            if self._department_re[name].search(title_text):
                return name

        abbr = re.search(r"\b([a-z]{2,4})\b", (title_text or "").lower())
        if abbr:
            mapped = _ABBR_DEPARTMENT.get(abbr.group(1))
            if mapped in self.target_departments:
                return mapped

        if description:
            for name in self.target_departments:
                if self._department_re[name].search(description[:3000]):
                    return name
        return ""

    def is_target_job(self, title, description=""):
        """True when a posting is C/V/D-level AND in a target department."""
        return self.is_senior_level(title) and bool(
            self.classify_department(title, description))

    def title_department(self, title):
        return self.seniority_label(title).replace("-", " ")


# ---------------------------------------------------------------------------
# Loading the rules from the client's workbook.
# ---------------------------------------------------------------------------

def load_criteria_from_excel(path, sheet="Columns"):
    """Build a Criteria from the 'Columns' sheet of the input workbook.

    Reads the C-level titles out of column C and the five department keyword
    lists out of columns D-H (plus Finance's extra row-40 block).  Falls back
    to the built-in defaults for anything the sheet does not provide.
    """
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    try:
        ws = wb[sheet]
    except KeyError:
        wb.close()
        return Criteria()

    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    c_level_titles = []
    departments = {name: [] for name in _DEPARTMENT_KEYWORDS}
    col_index = {"Operations": 3, "Procurement": 4, "Finance": 5,
                 "IT": 6, "Purchasing": 7}

    for r, row in enumerate(rows):
        def cell(idx):
            if idx < len(row) and row[idx] is not None:
                value = str(row[idx]).strip()
                return value if value else ""
            return ""

        # Rows 1-3 (0-based) are headers: the C-level description and the
        # department names / stray cells must not become keywords.
        c = cell(2)
        if r >= 3 and c and c not in _SECTION_HEADERS:
            c_level_titles.append(c)
        if r >= 4:
            for name, idx in col_index.items():
                value = cell(idx)
                if value:
                    departments[name].append(value)
        if r == 39:  # Finance extended block (Controller ... Receivabl)
            for idx in range(8, len(row)):
                value = cell(idx)
                if value:
                    departments["Finance"].append(value)

    # Merge with the built-in defaults so terms the sheet references only in
    # its C-level section (e.g. "Supply Chain", "Logistics") are never lost.
    for name, kws in departments.items():
        base = _DEPARTMENT_KEYWORDS[name]
        departments[name] = list(dict.fromkeys(kws + [k for k in base
                                                      if k not in kws]))

    patterns = list(_C_LEVEL_PATTERNS)
    # Extra abbreviations / exact titles from the sheet (e.g. CSCO, CAO, CLO).
    extra_abbr = [t for t in c_level_titles
                  if re.fullmatch(r"[A-Za-z]{2,5}", t)]
    if extra_abbr:
        patterns.insert(0, re.compile(
            r"\b(?:" + "|".join(re.escape(a.lower()) for a in extra_abbr)
            + r")\b", re.I))

    return Criteria(c_level_patterns=patterns,
                    department_keywords=departments)


_DEFAULT = Criteria()


def is_c_level(title):
    return _DEFAULT.is_c_level(title)


def is_v_level(title):
    return _DEFAULT.is_v_level(title)


def is_d_level(title):
    return _DEFAULT.is_d_level(title)


def is_senior_level(title):
    return _DEFAULT.is_senior_level(title)


def seniority_label(title):
    return _DEFAULT.seniority_label(title)


def classify_department(title, description=""):
    return _DEFAULT.classify_department(title, description)


def is_target_job(title, description=""):
    return _DEFAULT.is_target_job(title, description)


def title_department(title):
    return _DEFAULT.title_department(title)