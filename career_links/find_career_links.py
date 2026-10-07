"""Career-page finder for a company list (no job scraping).

Reuses job_scraper's homepage resolution, career-link detection, ATS-board
detection and ownership gates, but stops as soon as the company's career page
(and, when there is one, the external ATS board it hands off to) is found.

    # pass 1: fast, plain HTTP only, no search engines
    python career_links\\find_career_links.py --no-render --no-search

    # pass 2: redo the misses with browser rendering + web search
    python career_links\\find_career_links.py --retry-misses

Resume is on by default: DUNS numbers already in the output are skipped.
"""
import argparse
import csv
import warnings
import logging
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from bs4 import BeautifulSoup  # noqa: E402

from job_scraper import netcache  # noqa: E402
from job_scraper import browser_fetch  # noqa: E402
from job_scraper import ats as ats_mod  # noqa: E402
from job_scraper import company as company_mod  # noqa: E402
from job_scraper.ats import (  # noqa: E402
    ats_urls_in_html, common_career_urls, detect_ats_in_url,
    find_career_links, registrable_domain, validate_career_page,
)
from job_scraper.company import (  # noqa: E402
    _candidate_ats, _resolve_homepage, _EXPLICIT_NO_JOBS_RE,
)
from job_scraper.ownership import board_belongs_to_company  # noqa: E402
from job_scraper.session import ScrapeSession, _looks_like_javascript_shell  # noqa: E402
from job_scraper.urlutils import hostname  # noqa: E402
from job_scraper.websearch import (  # noqa: E402
    raise_query_budget, search_ats_boards, search_company_career_pages,
    set_query_budget,
)

log = logging.getLogger("job_scraper")
warnings.filterwarnings("ignore", module="bs4")

DEFAULT_INPUT = os.path.join(HERE, "parent_input.csv")
DEFAULT_OUTPUT = os.path.join(HERE, "career_links.csv")

OUT_COLUMNS = [
    "DUNS_NUMBER", "COMPANY_NAME", "web_domain", "COUNTRY1", "EMPLOYEES_TOTAL",
    "career_page_url", "ats_board_url", "ats_vendor", "status",
    "discovery_method", "resolved_website", "website_discovery", "note",
    "checked_at", "seconds",
]

# Status values
FOUND = "Found"
NOT_FOUND = "Career Page Not Found"
UNREACHABLE = "Website Unreachable"
BLOCKED = "Blocked by Local Web Filter"
ERROR = "Error"
RETRYABLE = {NOT_FOUND, UNREACHABLE, ERROR}

# Career vocabulary the shared keyword list lacks.  The input is 6% Japanese
# and has sizeable Nordic, Dutch, Italian, Korean and CEE shares.
_EXTRA_CAREER_KEYWORDS = [
    r"æŽ¡ç”¨", r"æ±‚äºº", r"ãƒªã‚¯ãƒ«ãƒ¼ãƒˆ", r"ã‚­ãƒ£ãƒªã‚¢", r"ì±„ìš©", r"ì¸ìž¬", r"æ‹›å‹Ÿ", r"äººæ‰",
    r"rekry", r"ty[Ã¶o]paikat", r"avoimet", r"vacature", r"werken[-\s_]*bij",
    r"lavora[-\s_]*con[-\s_]*noi", r"carriere", r"posizioni[-\s_]*aperte",
    r"trabalhe", r"lediga[-\s_]*(?:jobb|tj[Ã¤a]nster)", r"ledige[-\s_]*stillinger",
    r"jobba", r"karri[Ã¤a]r", r"stillinger", r"kariyer", r"kari[Ã©e]ra",
    r"voln[Ã¡a][-\s_]*m[Ã­i]sta", r"[Ã¡a]ll[Ã¡a]s", r"karrier", r"vacantes",
    r"bolsa[-\s_]*de[-\s_]*trabajo", r"carri[Ã¨e]res?", r"nous[-\s_]*rejoindre",
    r"rejoignez", r"unisciti", r"arbeiten[-\s_]*bei", r"\bstellen\b", r"\bjobb\b",
    r"vakatur", r"Ñ€Ð°Ð±Ð¾Ñ‚Ð°", r"Ð²Ð°ÐºÐ°Ð½ÑÐ¸Ð¸", r"ÐºÐ°Ñ€ÑŒÐµÑ€Ð°", r"lowongan", r"karir",
    r"tuyá»ƒn[-\s_]*dá»¥ng", r"à¸ªà¸¡à¸±à¸„à¸£à¸‡à¸²à¸™", r"à¸£à¹ˆà¸§à¸¡à¸‡à¸²à¸™",
]
_RealSoup = BeautifulSoup


def _fast_soup(markup="", features=None, *args, **kwargs):
    """BeautifulSoup on lxml instead of html.parser: several times faster, and
    parsing, not the network, was what capped throughput with 40 threads."""
    if features in (None, "html.parser"):
        features = "lxml"
    try:
        return _RealSoup(markup, features, *args, **kwargs)
    except Exception:
        return _RealSoup(markup, "html.parser", *args, **kwargs)


BeautifulSoup = _fast_soup
from job_scraper import ownership as _own_mod, session as _sess_mod, websearch as _ws_mod  # noqa: E402
for _m in (ats_mod, company_mod, _own_mod, _sess_mod, _ws_mod):
    _m.BeautifulSoup = _fast_soup

# ATS detection runs ~250 regexes per URL, and ats_urls_in_html fed it every
# URL in every page (thousands in inline scripts) -- a quarter of all CPU.
# Memoize it, and skip URLs that cannot be a third-party board.
import functools  # noqa: E402

_real_detect = ats_mod.detect_ats_in_url


@functools.lru_cache(maxsize=200000)
def _detect_cached(url):
    return _real_detect(url)


def _fast_detect(url):
    return _detect_cached(url or "")


_JUNK_HOST_RE = re.compile(
    r"(?:^|\.)(?:google|googleapis|gstatic|googletagmanager|google-analytics|doubleclick|"
    r"facebook|fbcdn|twitter|x|linkedin|licdn|youtube|ytimg|instagram|pinterest|tiktok|"
    r"cloudflare|cloudfront|akamaihd|jsdelivr|unpkg|jquery|bootstrapcdn|fontawesome|"
    r"typekit|w3|schema|wp|wordpress|gravatar|hotjar|hubspot|hs-scripts|hsforms|"
    r"cookiebot|onetrust|cookielaw|vimeo|wistia|shopify|squarespace|wixstatic|wix|"
    r"parastorage|apple|microsoft|bing|yahoo|addthis|sharethis|recaptcha|newrelic|"
    r"sentry|segment|mailchimp|list-manage|trustpilot|tawk|zendesk|intercom)\.[a-z.]+$", re.I)
_URL_IN_TEXT_RE = re.compile(r"https?://[^\s\"'<>()\\]{6,300}")


def _fast_ats_urls_in_html(html, base_url):
    from job_scraper.ats import is_probable_board_url
    from job_scraper.urlutils import url_join
    if not html:
        return []
    own = registrable_domain(hostname(base_url))
    raw = set(_URL_IN_TEXT_RE.findall(html[:_MAX_BODY]))
    for m in re.finditer(r"""(?:href|src|action|data-[\w-]+)\s*=\s*["']([^"']{4,300})["']""",
                         html[:_MAX_BODY], re.I):
        v = m.group(1)
        if not v.startswith("http"):
            v = url_join(base_url, v)
        if v:
            raw.add(v)
    found, seen = [], set()
    for u in raw:
        u = u.replace("&amp;", "&").rstrip('\\"\'),;')
        h = hostname(u)
        if not h:
            continue
        if registrable_domain(h) == own or _JUNK_HOST_RE.search(h):
            continue
        name, cap = _fast_detect(u)
        if name and is_probable_board_url(u) and u not in seen:
            seen.add(u)
            found.append((name, cap, u))
    return found


ats_mod.detect_ats_in_url = _fast_detect
ats_mod.ats_urls_in_html = _fast_ats_urls_in_html
company_mod.detect_ats_in_url = _fast_detect
detect_ats_in_url = _fast_detect
ats_urls_in_html = _fast_ats_urls_in_html
for _m in ("ownership", "websearch", "parsers_ats"):
    _mod = sys.modules.get("job_scraper." + _m)
    if _mod is not None and hasattr(_mod, "detect_ats_in_url"):
        _mod.detect_ats_in_url = _fast_detect

for _kw in _EXTRA_CAREER_KEYWORDS:
    if _kw not in ats_mod.CAREER_KEYWORDS:
        ats_mod.CAREER_KEYWORDS.append(_kw)

# Every row has a client-supplied domain.  Guessing a replacement from the
# name when that domain is dead attached a Michigan school district to an
# unrelated French company (freeland.k12.mi.us -> freeland.com), so guessing
# is off; a dead domain is reported as such.
company_mod._guess_candidates = lambda name, country: []
company_mod.PROBE_TIMEOUT = 12

# Paths probed when the homepage exposes no career link: the most common
# first, so the probe budget is spent where the hits are.
_PROBE_PATHS = ["/careers", "/career", "/jobs", "/join-us", "/karriere",
                "/work-with-us", "/vacancies", "/careers/jobs", "/about/careers",
                "/stellenangebote", "/join-our-team", "/career-opportunities"]

_STRONG_RE = re.compile(r"career|karriere|karri[Ã¤a]r|jobs?\b|/jobs?/|jobb|vacanc|vacature|"
                        r"join[-_/ ]?(?:us|our)|work[-_/ ]?(?:with|for)[-_/ ]?us|stellen|"
                        r"empleo|emploi|vagas|trabaj|trabalhe|recrut|recruit|rekry|saiyo|"
                        r"é‡‡ç”¨|æŽ¡ç”¨|æ±‚äºº|ì±„ìš©|opportunit|kariyer|kariera|karrier|lavora", re.I)

# Student career services, not the employer's own vacancies.
_STUDENT_CAREER_RE = re.compile(r"career[-_ ]?(?:development|services?|center|centre|"
                                r"counsel|readiness|pathway|fair|exploration|learning|"
                                r"academ|tech|connection|guidance|advice)|"
                                r"college-and-career|\bcte\b|/ctae\b|job[-_ ]?training|"
                                r"learning[-_ ]opportunit|expanded[-_ ]learning", re.I)

# What a link TEXT must say for the homepage's own label to be trusted.
# "Opportunities" alone is not enough (investment, project, learning ...).
_ANCHOR_RE = re.compile(r"career|karriere|karri[äa]r|\bjobs?\b|jobb|vacanc|vacature|"
                        r"werken[-\s]*bij|join[-\s]*(?:us|our[-\s]*team|the[-\s]*team)|"
                        r"work[-\s]*(?:with|for|at)[-\s]*us|employment|stellen|empleo|"
                        r"emploi|vagas|trabaj|trabalhe|recrut|recruit|rekry|採用|求人|채용|"
                        r"kariyer|kariera|karrier|lavora|praca|работа|вакансии|ledige|"
                        r"lediga|avoimet|hiring|job[-\s]*openings?|open[-\s]*positions", re.I)

_LOGIN_RE = re.compile(r"(?:sign[-_]?in|log[-_]?in|authentication|/sso\b|/auth/|password)", re.I)

# Blog/news permalinks that a fuzzy CMS redirect lands on.
_ARTICLE_RE = re.compile(r"/(?:19|20)\d\d/|/[a-z]*(?:news|blog|press|article|event|post|"
                         r"stor(?:y|ies))[a-z]*/|/sys/content/", re.I)

# Vendor hosts that are not job boards (student information systems).
_NOT_A_BOARD_RE = re.compile(r"powerschool\.com/(?!.*(?:job|career|applicant|talent))", re.I)

_ERROR_PAGE_RE = re.compile(r"\b(?:page not found|404 not found|page does not exist|"
                            r"seite nicht gefunden|page introuvable|p[áa]gina no encontrada|"
                            r"p[áa]gina n[ãa]o encontrada|pagina non trovata|"
                            r"sidan hittades inte|siden finnes ikke|nothing was found)\b", re.I)


def _looks_like_error(html):
    soup = BeautifulSoup(html[:300000], "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    heads = " ".join(t.get_text(" ", strip=True) for t in soup.find_all(["h1", "h2"], limit=4))
    return bool(_ERROR_PAGE_RE.search(title + " " + heads) or re.search(r"\b404\b", title))

_FORTI_RE = re.compile(r"FortiGuard|Web Filter Violation|web page that is in violation "
                       r"of your Internet usage policy", re.I)


def _forti_category(text):
    if not text or not _FORTI_RE.search(text[:40000]):
        return ""
    plain = " ".join(re.sub(r"<[^>]+>", " ", text).split())
    m = re.search(r"Category\s+(.+?)\s+URL", plain)
    return (m.group(1) if m else "unknown")[:60]


_MAX_BODY = 1_500_000


class _Capped:
    """Read-only view of a response with the body truncated.  A few sites
    answer /careers with a multi-hundred-MB file; parsing it pinned a CPU for
    many minutes and stalled a whole shard."""

    def __init__(self, r, text):
        self.status_code = r.status_code
        self.url = str(r.url)
        self.headers = r.headers
        self.text = text
        self.content = text.encode("utf-8", "ignore")

    def json(self):
        import json
        return json.loads(self.text)


def _cap(r, url):
    if r is None:
        return r
    try:
        ctype = (r.headers.get("Content-Type") or "").lower()
        raw = r.content or b""
    except Exception:
        return r
    if len(raw) <= _MAX_BODY and ("pdf" not in ctype and "octet" not in ctype
                                  and "image" not in ctype and "video" not in ctype):
        return r
    log.info("Capped body of %s (%d bytes, %s)", url, len(raw), ctype)
    if any(k in ctype for k in ("pdf", "octet", "image", "video", "audio", "zip")):
        return _Capped(r, "")
    head = raw[:_MAX_BODY]
    enc = getattr(r, "encoding", None) or "utf-8"
    try:
        text = head.decode(enc, "ignore")
    except LookupError:
        text = head.decode("utf-8", "ignore")
    return _Capped(r, text)


class FilterAwareSession(ScrapeSession):
    """ScrapeSession that notices the local FortiGuard block page and retries
    genuine bot-blocks (403/429/503 from the site itself) with a browser TLS
    fingerprint via curl_cffi.

    The block page is the local network's policy, not the website answering;
    it is recorded per host and never retried around.
    """

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.blocked_hosts = {}
        self._tls = threading.local()

    def _curl(self):
        s = getattr(self._tls, "curl", None)
        if s is None:
            try:
                from curl_cffi import requests as curl_requests
                s = curl_requests.Session(impersonate="chrome")
            except Exception:
                s = False
            self._tls.curl = s
        return s

    def fetch(self, url, timeout=None, method="GET", retries=None, **kwargs):
        if method.upper() == "GET":
            kwargs.setdefault("stream", True)
        # One attempt per URL: a dead host otherwise costs 2 x timeout for each
        # of the four homepage variants.  Misses are retried in a later pass.
        retries = 0
        r = super().fetch(url, timeout=timeout, method=method, retries=retries, **kwargs)
        if r is not None and kwargs.get("stream") and not getattr(r, "_content_consumed", True):
            chunks, total, t0 = [], 0, time.time()
            try:
                for chunk in r.iter_content(65536):
                    chunks.append(chunk)
                    total += len(chunk)
                    if total > _MAX_BODY or time.time() - t0 > 40:
                        break
            except Exception:
                pass
            r._content = b"".join(chunks)[:_MAX_BODY]
            r._content_consumed = True
            r.close()
        r = _cap(r, url)
        if r is None or method.upper() != "GET" or r.status_code not in (403, 429, 503):
            return r
        text = r.text or ""
        category = _forti_category(text)
        if category:
            self.blocked_hosts[hostname(url)] = category
            return r
        curl = self._curl()
        if not curl:
            return r
        try:
            r2 = curl.get(url, timeout=timeout or 25, verify=False, allow_redirects=True)
        except Exception:
            return r
        if r2.status_code < 400:
            return _cap(r2, url)
        category = _forti_category(r2.text or "")
        if category:
            self.blocked_hosts[hostname(url)] = category
        return r


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _get(session, url, render, timeout=25):
    """(final_url, html) -- html is '' when the page is unusable."""
    response = session.fetch(url, timeout=timeout, retries=1)
    if response is None:
        return url, ""
    final = str(response.url or url)
    ctype = (response.headers.get("Content-Type") or "").lower()
    if response.status_code >= 400:
        if (render and response.status_code in (403, 405, 406, 429, 451)
                and hostname(url) not in session.blocked_hosts):
            html = browser_fetch.fetch_rendered_html(url) or ""
            return final, html
        return final, ""
    if "html" not in ctype and "xml" not in ctype and ctype:
        return final, ""
    html = response.text or ""
    if render and _looks_like_javascript_shell(html):
        html = browser_fetch.fetch_rendered_html(final) or html
    return final, html


def _is_root(url):
    return urlparse(url).path.strip("/") == "" and not urlparse(url).query


def _looks_like_article(url):
    path = urlparse(url).path
    last = path.rstrip("/").rsplit("/", 1)[-1]
    return bool(_ARTICLE_RE.search(path)) or last.count("-") >= 5


_CAREER_DOMAIN_RE = re.compile(r"career|karriere|karri[äa]r|kariera|karrier|jobs?|jobb|"
                               r"stellen|recrut|recruit|talent|vagas|empleo|emploi|rekry|"
                               r"saiyo|hiring|werkbij|werkenbij|vacature|trabalhe", re.I)


def _harvest(home_html, home_url, name):
    """Career candidates on a homepage -> ({url: method}, {url: anchor text}).

    Same-domain career links, recognised ATS boards, and off-domain career
    portals whose domain is itself a career domain or carries the company
    name (krankenhaus-waldfriede.de -> karriere-waldfriede.de).
    """
    from job_scraper.ats import EXCLUDE_PATH_RE, is_career_link, is_probable_board_url
    from job_scraper.ownership import domain_matches_company
    from job_scraper.urlutils import url_join

    methods, texts = {}, {}
    if not home_html:
        return methods, texts
    soup = BeautifulSoup(home_html, "html.parser")
    base_url = home_url
    base_tag = soup.find("base", href=True)
    if base_tag:
        base_url = url_join(home_url, base_tag["href"]) or home_url
    home_dom = registrable_domain(hostname(home_url))
    home_norm = home_url.split("#")[0].rstrip("/")

    for a in soup.find_all("a", href=True):
        text = " ".join(a.get_text(" ", strip=True).split())[:80]
        if not text:
            text = (a.get("title") or a.get("aria-label") or "")[:80]
        full = url_join(base_url, a["href"])
        if not full or not full.startswith("http"):
            continue
        key = full.split("#")[0].rstrip("/")
        if not key or key == home_norm or key in methods:
            continue
        ats, _cap = detect_ats_in_url(key)
        if ats and not is_probable_board_url(key):
            ats = None
        if not ats and not is_career_link(text, a["href"]):
            continue
        if EXCLUDE_PATH_RE.search(key) and not ats:
            continue
        dom = registrable_domain(hostname(key))
        if dom != home_dom and not ats:
            text_career = is_career_link(text, "")
            if not (text_career and (_CAREER_DOMAIN_RE.search(dom.split(".")[0])
                                     or domain_matches_company(dom, name))):
                continue
        methods[key] = "homepage_ats" if ats and dom != home_dom else "homepage_link"
        texts[key] = text
    for ats, _cap, u in ats_urls_in_html(home_html, base_url):
        key = u.split("#")[0].rstrip("/")
        if key not in methods and not _NOT_A_BOARD_RE.search(key):
            methods[key] = "homepage_ats"
            texts[key] = ""
    return methods, texts


def _priority(url, method, text=""):
    strong = bool(_STRONG_RE.search(url) or _STRONG_RE.search(text))
    ats, _ = detect_ats_in_url(url)
    path = urlparse(url).path.rstrip("/").lower()
    career_root = bool(re.search(r"/(?:[a-z]{2}(?:[-_][a-z]{2})?/)?(?:careers?|karriere|jobs)$", path))
    deep_posting = bool(re.search(r"/(?:careers?|jobs?)/.+/.+", path))
    score = {"homepage_link": 30 if strong else 12, "homepage_ats": 45,
             "common_path_probe": 10, "web_search": 20}.get(method, 0)
    if career_root:
        score += 50
    if ats and not _NOT_A_BOARD_RE.search(url):
        score += 30
    if deep_posting:
        score -= 25
    if _STUDENT_CAREER_RE.search(url):
        score -= 60
    if _looks_like_article(url):
        score -= 40
    return (-score, len(url))


class Finder:
    def __init__(self, render, search, max_candidates=8):
        self.render = render
        self.search = search
        self.max_candidates = max_candidates
        self.session = FilterAwareSession(timeout=25, max_retries=0)
        # Several rows share a web_domain: resolve each domain once.
        self._cache = {}
        self._inflight = {}
        self._lock = threading.Lock()

    def find(self, name, domain, country):
        key = (domain or "").strip().lower() or ("name:" + (name or "").lower())
        with self._lock:
            if key in self._cache:
                return dict(self._cache[key])
            event = self._inflight.get(key)
            owner = event is None
            if owner:
                event = self._inflight[key] = threading.Event()
        if not owner:
            event.wait(600)
            with self._lock:
                if key in self._cache:
                    return dict(self._cache[key])
        try:
            result = self._find(name, domain, country)
        except Exception as exc:  # never lose a row to one bad site
            log.exception("career finder failed for %s (%s)", name, domain)
            result = {"status": ERROR, "note": str(exc)[:200]}
        with self._lock:
            if result.get("status") != ERROR:
                self._cache[key] = result
                if len(self._cache) > 20000:
                    self._cache.pop(next(iter(self._cache)))
            ev = self._inflight.pop(key, None)
        if ev:
            ev.set()
        return dict(result)

    # ------------------------------------------------------------------
    def _find(self, name, domain, country):
        session = self.session
        set_query_budget()
        out = {"career_page_url": "", "ats_board_url": "", "ats_vendor": "",
               "status": NOT_FOUND, "discovery_method": "", "resolved_website": "",
               "website_discovery": "", "note": "",
               "_deadline": time.time() + 110}

        base, home_url, home_html, w_method, w_note = _resolve_homepage(
            name, domain, country, session, self.search)
        out["resolved_website"] = base
        out["website_discovery"] = w_method
        if not base:
            out["status"] = UNREACHABLE
            out["note"] = (w_note or "")[:200]
            host = (domain or "").strip().lower()
            for h in (host, "www." + host, host[4:] if host.startswith("www.") else ""):
                category = self.session.blocked_hosts.get(h)
                if category:
                    out["status"] = BLOCKED
                    out["note"] = "FortiGuard category: %s" % category
                    return out
            if self.search:
                raise_query_budget(8)
                if self._board_search(name, country, out):
                    return out
            return out

        if self.render and home_html and _looks_like_javascript_shell(home_html):
            home_html = browser_fetch.fetch_rendered_html(home_url) or home_html

        methods, texts = _harvest(home_html, home_url, name)
        ranked = sorted(methods, key=lambda u: _priority(u, methods[u], texts.get(u, "")))
        if self._try_candidates(name, home_url, ranked[:self.max_candidates], methods, out, texts=texts):
            return out

        # Nothing linked from the homepage: probe the usual paths.
        root = "%s://%s" % (urlparse(home_url).scheme or "https", urlparse(home_url).netloc)
        probes = [root + p for p in _PROBE_PATHS]
        probes = [p for p in probes if p.rstrip("/") not in methods]
        for p in probes:
            methods[p] = "common_path_probe"
        if self._try_candidates(name, home_url, probes, methods, out, stop_on_dead=True):
            return out

        if self.search:
            found = [u.split("#")[0].rstrip("/") for u in
                     search_company_career_pages(name, home_url, session, country=country)]
            for u in found:
                methods.setdefault(u, "web_search")
            if self._try_candidates(name, home_url, found[:6], methods, out):
                return out
            if self._board_search(name, country, out):
                return out

        # Last resort: the homepage itself carries postings or an ATS widget.
        if home_html and re.search(r'["\']@type["\']\s*:\s*["\']JobPosting', home_html):
            out.update(career_page_url=home_url, status=FOUND,
                       discovery_method="homepage_jobposting")
        return out

    def _try_candidates(self, name, home_url, candidates, methods, out, stop_on_dead=False,
                        texts=None):
        texts = texts or {}
        session = self.session
        home_dom = registrable_domain(hostname(home_url))
        misses = 0
        for cand in candidates:
            if time.time() > out.get("_deadline", float("inf")):
                out["note"] = (out.get("note") or "time budget reached")
                return False
            method = methods.get(cand, "homepage_link")
            ats, cap = detect_ats_in_url(cand)
            final, html = _get(session, cand, self.render)
            if not html and not ats:
                misses += 1
                # A site that answers none of the first probes will not
                # answer the rest either.
                if stop_on_dead and misses >= 4 and not out.get("_any_alive"):
                    return False
                continue
            out["_any_alive"] = True
            final_norm = final.split("#")[0].rstrip("/")
            # A probe that just bounced back to the homepage is not a career page.
            if method == "common_path_probe" and _is_root(final) and not ats:
                continue
            # A probe the CMS fuzzy-redirected somewhere else (a blog post
            # whose slug contains "jobs") is not a career page either.
            if (method == "common_path_probe" and not ats
                    and urlparse(final).path.rstrip("/").lower()
                    != urlparse(cand).path.rstrip("/").lower()
                    and not _STRONG_RE.search(urlparse(final).path)):
                continue
            # ...nor one that landed on another host (help.open.ac.uk/browse/careers
            # is student guidance, not the university's vacancies).
            if (method == "common_path_probe" and not ats
                    and hostname(final).removeprefix("www.")
                    != hostname(cand).removeprefix("www.")):
                continue
            if _NOT_A_BOARD_RE.search(final) or _STUDENT_CAREER_RE.search(final):
                continue
            if not ats and _looks_like_article(final):
                continue
            if _LOGIN_RE.search(urlparse(final).path):
                continue
            f_host = hostname(final)
            f_dom = registrable_domain(f_host)
            f_sub = f_host[:-len(f_dom)].rstrip(".") if f_dom and f_host.endswith(f_dom) else ""
            career_in_url = bool(_CAREER_DOMAIN_RE.search(f_host) or _STRONG_RE.search(
                urlparse(final).path))
            # A bare root is only a career page when its host says so
            # (jobs.acme.com, karriere.acme.de) or it is a vendor tenant
            # (acme.schoolspring.com) -- not app.frontlineeducation.com,
            # swipejobs.com, or a sister school's homepage.
            if _is_root(final):
                tenant = ats and f_sub not in ("", "www", "app", "apply", "my", "hcm")
                # "www" is not a label: www.karriere-waldfriede.de must be
                # judged on "karriere-waldfriede".
                if not (tenant or _CAREER_DOMAIN_RE.search(f_sub + " " + f_dom.split(".")[0])):
                    continue
            # Off the company's domain and not a recognised board: the URL
            # itself must be about careers.
            if f_dom != home_dom and not ats and not career_in_url:
                continue
            same_site = registrable_domain(hostname(final)) == home_dom
            final_ats, final_cap = detect_ats_in_url(final)
            ats = ats or final_ats
            cap = cap or final_cap
            if method == "web_search" and not same_site:
                owned, why = board_belongs_to_company(ats, cap, final, name, html)
                if not owned:
                    log.info("Rejected searched page for %s: %s (%s)", name, final, why)
                    continue
            # A link the homepage itself labels "Careers" / "Trabaja con
            # nosotros" is the company's own statement of where its career
            # page is; the page need only load and not be an error page.
            text = texts.get(cand, "")
            anchor_ok = bool(
                method == "homepage_link" and html and not _looks_like_error(html)
                and (_ANCHOR_RE.search(text) or _ANCHOR_RE.search(urlparse(final).path)
                     or _CAREER_DOMAIN_RE.search(hostname(final).split(".")[0])))
            if not (ats or anchor_ok or validate_career_page(final, html, home_url)):
                continue
            out.update(career_page_url=final_norm or cand, status=FOUND,
                       discovery_method=method)
            if ats:
                out.update(ats_board_url=final_norm or cand, ats_vendor=ats)
            else:
                b_ats, b_cap, b_url = _candidate_ats(session, final, html)
                if b_ats and b_url and not _NOT_A_BOARD_RE.search(b_url):
                    if method != "web_search" or board_belongs_to_company(
                            b_ats, b_cap, b_url, name)[0]:
                        out.update(ats_board_url=b_url.split("#")[0], ats_vendor=b_ats)
            if html and _EXPLICIT_NO_JOBS_RE.search(
                    BeautifulSoup(html, "html.parser").get_text(" ", strip=True)[:20000]):
                out["note"] = "page says no current openings"
            return True
        return False

    def _board_search(self, name, country, out):
        for board_url in search_ats_boards(name, self.session, country=country, groups=2):
            ats, cap = detect_ats_in_url(board_url)
            if not ats:
                continue
            owned, why = board_belongs_to_company(ats, cap, board_url, name)
            if not owned:
                html = self.session.fetch_text(board_url, timeout=25)
                owned, why = board_belongs_to_company(ats, cap, board_url, name, html)
            if owned:
                out.update(career_page_url=board_url, ats_board_url=board_url,
                           ats_vendor=ats, status=FOUND,
                           discovery_method="ats_board_name_search")
                return True
        return False


# ----------------------------------------------------------------------
def _setup_logging(path):
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    handler = RotatingFileHandler(path, maxBytes=50 * 1024 * 1024, backupCount=3,
                                  encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    for noisy in ("urllib3", "requests", "charset_normalizer"):
        logging.getLogger(noisy).setLevel(logging.ERROR)


def _read_rows(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", default=DEFAULT_INPUT)
    ap.add_argument("--output", default=DEFAULT_OUTPUT)
    ap.add_argument("--workers", type=int, default=40)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--no-render", dest="render", action="store_false")
    ap.add_argument("--no-search", dest="search", action="store_false")
    ap.add_argument("--retry-misses", action="store_true",
                    help="drop Not Found / Unreachable / Error rows, then redo them")
    ap.add_argument("--max-candidates", type=int, default=8)
    ap.add_argument("--shard-index", type=int, default=0)
    ap.add_argument("--shard-count", type=int, default=1,
                    help="split by domain so rows sharing a domain stay together")
    args = ap.parse_args()

    _setup_logging(os.path.splitext(args.output)[0] + ".log")
    netcache.install()
    if not args.render:
        browser_fetch._BROWSER_UNAVAILABLE.set()
        browser_fetch._BROWSER_UNAVAILABLE_REASON[:] = ["disabled by --no-render"]

    rows = _read_rows(args.input)
    if args.offset:
        rows = rows[args.offset:]
    if args.limit:
        rows = rows[:args.limit]
    if args.shard_count > 1:
        import zlib
        rows = [r for r in rows
                if zlib.crc32(r["web_domain"].strip().lower().encode("utf-8"))
                % args.shard_count == args.shard_index]

    done = {}
    if os.path.exists(args.output):
        for r in _read_rows(args.output):
            done[r["DUNS_NUMBER"]] = r
    if args.retry_misses and done:
        kept = {k: v for k, v in done.items() if v.get("status") not in RETRYABLE}
        print("retry-misses: keeping %d, redoing %d" % (len(kept), len(done) - len(kept)))
        tmp = args.output + ".tmp"
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=OUT_COLUMNS, extrasaction="ignore")
            w.writeheader()
            w.writerows(kept.values())
        os.replace(tmp, args.output)
        done = kept

    todo = [r for r in rows if r["DUNS_NUMBER"] not in done]
    print("input %d  already done %d  to do %d  workers %d  render=%s search=%s"
          % (len(rows), len(done), len(todo), args.workers, args.render, args.search),
          flush=True)
    if not todo:
        return 0

    new_file = not os.path.exists(args.output) or os.path.getsize(args.output) == 0
    fh = open(args.output, "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(fh, fieldnames=OUT_COLUMNS, extrasaction="ignore")
    if new_file:
        writer.writeheader()
    write_lock = threading.Lock()
    finder = Finder(args.render, args.search, args.max_candidates)
    counts = {}
    started = time.time()

    def work(row):
        t0 = time.time()
        res = finder.find(row["COMPANY_NAME"], row["web_domain"], row["COUNTRY1"])
        res.pop("_any_alive", None)
        res.pop("_deadline", None)
        rec = dict(row)
        rec.update(res)
        rec["checked_at"] = _now()
        rec["seconds"] = "%.0f" % (time.time() - t0)
        return rec

    n = 0
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(work, r) for r in todo]
            for fut in as_completed(futures):
                rec = fut.result()
                with write_lock:
                    writer.writerow(rec)
                    n += 1
                    counts[rec["status"]] = counts.get(rec["status"], 0) + 1
                    if n % 200 == 0:
                        fh.flush()
                        rate = n / max(1e-9, (time.time() - started) / 60)
                        eta = (len(todo) - n) / rate if rate else 0
                        print("%d/%d  %.0f/min  eta %.0fmin  %s"
                              % (n, len(todo), rate, eta, counts), flush=True)
    except KeyboardInterrupt:
        print("interrupted; progress saved, re-run to resume")
        os._exit(130)
    finally:
        fh.flush()
        fh.close()
    print("done %d in %.1f min  %s" % (n, (time.time() - started) / 60, counts), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
