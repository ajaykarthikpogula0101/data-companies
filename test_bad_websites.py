"""Every way an input website can be useless, and the escalation for each."""
import json, sys
import os
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from job_scraper import company, websearch

PASS, FAIL = [], []
def check(label, cond, detail=""):
    (PASS if cond else FAIL).append(label)
    print("%s %s%s" % ("PASS" if cond else "FAIL", label, (" -- %s" % detail) if detail else ""))

REAL = "https://www.acme-eng.com"
JOBS_N = 8

def careers_html():
    ld = json.dumps([{"@type": "JobPosting", "title": "Engineer %d" % i,
                      "url": REAL + "/careers/j%d" % i, "description": "Apply."}
                     for i in range(JOBS_N)])
    return ('<html><head><title>Careers at ACME Engineering</title>'
            '<script type="application/ld+json">%s</script></head>'
            '<body><main><h1>Open positions</h1><p>Apply</p></main></body></html>' % ld)

REAL_HOME = ('<html><head><title>ACME Engineering Ltd</title></head><body>'
             '<h1>ACME Engineering</h1><a href="/careers">Careers</a></body></html>')
PARKED = ('<html><head><title>Domain for sale</title></head><body>'
          '<h1>This domain is for sale</h1><p>Buy this domain at Sedo.com</p></body></html>')
OTHER_CO = ('<html><head><title>Zenith Foods Inc</title></head><body>'
            '<h1>Zenith Foods</h1><p>We sell snacks.</p></body></html>')


class Base:
    """Serves the correct site; subclasses break the input website differently."""
    search_website = [REAL]
    ats_boards = []

    def __init__(self):
        self.calls = []

    def site(self, u):
        if u == REAL:
            return REAL_HOME
        if u.startswith(REAL + "/careers"):
            return careers_html()
        return None

    def _body(self, url):
        u = url.split("#")[0].rstrip("/")
        return self.site(u)

    def fetch(self, url, timeout=None, method="GET", retries=None, **kw):
        self.calls.append(url)
        body = self._body(url)
        if body is None:
            return None
        if isinstance(body, tuple):
            html, status = body
        else:
            html, status = body, 200
        class R:
            def __init__(s, u, t, st):
                s.url, s.text, s.status_code = u, t, st
                s.headers = {"Content-Type": "text/html"}
            def json(s): return {}
        return R(url, html, status)

    def fetch_text(self, url, timeout=None, **kw):
        r = self.fetch(url, timeout=timeout)
        return r.text if (r and r.status_code < 400) else None

    def fetch_json(self, url, timeout=None, **kw): return None
    def post_json(self, url, payload, timeout=None): return None
    def head_ok(self, url, timeout=12): return True


def run_case(label, session_cls, website, expect_positions=JOBS_N,
             expect_method=None, name="ACME Engineering Ltd"):
    sess = session_cls()
    websearch._QUERY_CACHE.clear(); websearch._ENGINE_STATE.clear()
    saved = websearch._ENGINES
    websearch._ENGINES = (("fake", lambda s, q: (
        sess.ats_boards if "site:" in q and "myworkdayjobs" in q else sess.search_website)),)
    try:
        d = company.process_company_details((name, website, "USA"), session=sess,
                                            enable_search=True)
    finally:
        websearch._ENGINES = saved
    print("\n--- %s" % label)
    print("    input website   : %r" % website)
    print("    resolved_website: %s" % d.get("resolved_website"))
    print("    website_discovery: %s" % d.get("website_discovery"))
    print("    status / positions: %s / %s" % (d["status"], d["num_positions"]))
    check(label, d["num_positions"] == expect_positions,
          "got %s, want %s" % (d["num_positions"], expect_positions))
    if expect_method:
        check(label + " [method]", d.get("website_discovery") == expect_method,
              d.get("website_discovery"))
    return d


# 1. website is simply wrong text (a company name)
run_case("garbage website value -> web search",
         Base, "ACME ENGINEERING LTD (PTY)", expect_method="web_search")

# 2. website empty
run_case("empty website -> web search", Base, "", expect_method="web_search")

# 3. website returns HTTP 404  (the branch that previously did nothing)
class NotFound(Base):
    def site(self, u):
        if u == "https://www.acme-old.com":
            return (PARKED, 404)
        return Base.site(self, u)
run_case("input website 404s -> web search", NotFound, "www.acme-old.com",
         expect_method="web_search")

# 4. website returns HTTP 500
class ServerError(Base):
    def site(self, u):
        if u == "https://www.acme-broken.com":
            return ("<html><body>error</body></html>", 500)
        return Base.site(self, u)
run_case("input website 500s -> web search", ServerError, "www.acme-broken.com",
         expect_method="web_search")

# 5. domain is parked / for sale
class Parked(Base):
    def site(self, u):
        if u == "https://www.acme-parked.com":
            return PARKED
        return Base.site(self, u)
run_case("parked domain rejected -> web search", Parked, "www.acme-parked.com",
         expect_method="web_search")

# 6. website belongs to a different company entirely
class WrongCompany(Base):
    def site(self, u):
        if u == "https://www.zenithfoods.com":
            return OTHER_CO
        return Base.site(self, u)
run_case("website is another company -> web search", WrongCompany,
         "www.zenithfoods.com", expect_method="web_search")

# 7. https dead but http works
class HttpOnly(Base):
    """https refuses connections; the whole site is only reachable over http."""
    def site(self, u):
        if u.startswith("https://www.acme-eng.com"):
            return None
        if u == "http://www.acme-eng.com":
            return REAL_HOME
        if u.startswith("http://www.acme-eng.com/careers"):
            return careers_html()
        return None
    search_website = []
run_case("https dead, http works", HttpOnly, "www.acme-eng.com",
         expect_method="input_website_http")

# 8. bare domain dead, www works
class WwwOnly(Base):
    def site(self, u):
        if u in ("https://acme-eng.com", "http://acme-eng.com"):
            return None
        if u == "https://www.acme-eng.com":
            return REAL_HOME
        return Base.site(self, u)
    search_website = []
run_case("bare domain dead, www works", WwwOnly, "acme-eng.com",
         expect_method="input_website_www")

# 9. no website anywhere, but an ATS board exists under the company name
class BoardOnly(Base):
    search_website = []
    ats_boards = ["https://boards.greenhouse.io/acmeengineering"]
    def site(self, u):
        if u.startswith("https://boards.greenhouse.io/acmeengineering"):
            return "<html><body>board</body></html>"
        return None
    def fetch_json(self, url, timeout=None, **kw):
        if "boards-api.greenhouse.io/v1/boards/acmeengineering/jobs" in url:
            return {"jobs": [{"id": i, "title": "Board Role %d" % i,
                              "absolute_url": "https://boards.greenhouse.io/acmeengineering/jobs/%d" % i,
                              "updated_at": "2026-08-01T00:00:00Z",
                              "location": {"name": "Remote"},
                              "content": "<p>Apply</p>"} for i in range(11)]}
        return None
run_case("no website at all -> ATS board found by name", BoardOnly, "",
         expect_positions=11)

print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
if FAIL:
    print("FAILED: " + ", ".join(FAIL))
sys.exit(1 if FAIL else 0)
