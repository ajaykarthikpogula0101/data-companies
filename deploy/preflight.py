"""Preflight doctor: confirm a VM can actually run the scraper.

    python preflight.py            # checks + a live 1-company probe
    python preflight.py --no-net   # skip anything that touches the network

Exit code 0 = ready, 1 = something is broken. Designed to be the last step of
provisioning and the first step of debugging.
"""

import argparse
import importlib
import os
import shutil
import socket
import subprocess
import sys
import time

def _find_project_root():
    """Locate the directory that contains the job_scraper package.

    preflight.py is useful from the project root, from deploy/, or from
    anywhere else, so search upward from this file and from the working
    directory rather than assuming a layout.
    """
    candidates = []
    here = os.path.dirname(os.path.abspath(__file__))
    cwd = os.path.abspath(os.getcwd())
    for start in (here, cwd):
        path = start
        for _ in range(4):
            candidates.append(path)
            parent = os.path.dirname(path)
            if parent == path:
                break
            path = parent
    for path in candidates:
        if os.path.isfile(os.path.join(path, "job_scraper", "__init__.py")):
            return path
    return here


ROOT = _find_project_root()
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

OK, BAD, WARN = [], [], []


def _text(value):
    """Coerce anything to a short string.

    `camoufox.__version__` is a submodule, not a string; concatenating it blew
    up this script and reported an installed package as missing.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(getattr(value, "__version__", value))[:200].strip()


def ok(label, detail=""):
    OK.append(label)
    detail = _text(detail)
    print("  [ ok ] %s%s" % (label, (" - " + detail) if detail else ""))


def bad(label, detail=""):
    BAD.append(label)
    detail = _text(detail)
    print("  [FAIL] %s%s" % (label, (" - " + detail) if detail else ""))


def warn(label, detail=""):
    WARN.append(label)
    detail = _text(detail)
    print("  [warn] %s%s" % (label, (" - " + detail) if detail else ""))


def _version(module):
    """Best-effort version string for a module.

    Handles packages (camoufox among them) that expose `__version__` as a
    submodule rather than a string.
    """
    import types

    for attr in ("__version__", "version", "VERSION"):
        value = getattr(module, attr, None)
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, types.ModuleType):
            for inner in ("__version__", "version", "VERSION"):
                nested = getattr(value, inner, None)
                if isinstance(nested, str):
                    return nested.strip()
            continue
        if value is not None:
            return str(value)[:60]
    try:
        from importlib.metadata import version
        return version(getattr(module, "__name__", ""))
    except Exception:
        return ""


def section(title):
    print("\n%s\n%s" % (title, "-" * len(title)))


parser = argparse.ArgumentParser()
parser.add_argument("--no-net", action="store_true")
args = parser.parse_args()

# ---------------------------------------------------------------- environment
section("1. Interpreter and environment")
print("  python  : %s" % sys.version.split()[0])
print("  venv    : %s" % (sys.prefix if sys.prefix != sys.base_prefix else "NOT in a venv"))
print("  platform: %s" % sys.platform)
if sys.version_info >= (3, 9):
    ok("python >= 3.9")
else:
    bad("python >= 3.9", sys.version.split()[0])
if sys.prefix == sys.base_prefix:
    warn("not running inside a virtualenv")

for var in ("JOB_SCRAPER_BASE_DIR", "JOB_SCRAPER_INPUT", "JOB_SCRAPER_OUTPUT",
            "JOB_SCRAPER_WORKERS", "JOB_SCRAPER_BROWSER_WORKERS",
            "CAMOUFOX_HEADLESS", "CAMOUFOX_PROXY"):
    value = os.environ.get(var)
    print("  %-28s = %s" % (var, value if value else "(unset, using default)"))

# ------------------------------------------------------------ python packages
section("2. Python packages")
REQUIRED = ["requests", "bs4", "openpyxl", "urllib3"]
OPTIONAL = {
    "langdetect": "description_language column falls back to blank",
    "pandas": "only used by helper scripts",
    "dns": "dnspython: public-resolver DNS fallback disabled",
    "googlesearch": "Google fallback engine disabled",
    "lxml": "slower HTML parsing (html.parser only)",
    "pyvirtualdisplay": "CAMOUFOX_HEADLESS=virtual will not work",
}
for name in REQUIRED:
    try:
        module = importlib.import_module(name)
        ok(name, _version(module))
    except Exception as exc:
        bad(name, str(exc))
for name, consequence in OPTIONAL.items():
    try:
        importlib.import_module(name)
        ok(name + " (optional)")
    except Exception:
        warn(name + " (optional) missing", consequence)

# -------------------------------------------------------------------- camoufox
section("3. Camoufox")
camoufox_ready = False
try:
    from camoufox.sync_api import Camoufox  # noqa: F401
    import camoufox
    camoufox_ready = True
except Exception as exc:
    bad("camoufox python package",
        '%s -- run: pip install "camoufox[geoip]"' % exc)

if camoufox_ready:
    try:
        ok("camoufox python package", _version(camoufox))
    except Exception:
        ok("camoufox python package", "installed")

    # The browser build is downloaded separately by `python -m camoufox fetch`.
    binary_found = False
    try:
        from camoufox.pkgman import installed_verstr
        ok("camoufox browser binary", installed_verstr())
        binary_found = True
    except Exception as exc:
        first_error = str(exc)[:150]
        try:
            from camoufox.locale import get_path as _gp  # noqa: F401
        except Exception:
            pass
        # Fall back to looking for the extracted browser on disk.
        candidates = []
        if sys.platform == "win32":
            base = os.environ.get("LOCALAPPDATA", "")
            if base:
                candidates.append(os.path.join(base, "camoufox", "camoufox"))
                candidates.append(os.path.join(base, "camoufox"))
        else:
            candidates.append(os.path.expanduser("~/.cache/camoufox"))
            candidates.append("/usr/local/share/camoufox")
        for path in candidates:
            if os.path.isdir(path) and os.listdir(path):
                ok("camoufox browser binary", "found at %s" % path)
                binary_found = True
                break
        if not binary_found:
            bad("camoufox browser binary",
                "%s -- run: python -m camoufox fetch" % first_error)

if sys.platform.startswith("linux"):
    if shutil.which("Xvfb"):
        ok("Xvfb present (needed for CAMOUFOX_HEADLESS=virtual)")
    else:
        warn("Xvfb missing", "apt-get install xvfb, or set CAMOUFOX_HEADLESS=true")
    if not os.environ.get("DISPLAY") and os.environ.get("CAMOUFOX_HEADLESS", "true") == "false":
        bad("CAMOUFOX_HEADLESS=false with no DISPLAY")

# ------------------------------------------------------------ scraper modules
section("4. Scraper modules")
try:
    from job_scraper import config, netcache, pipeline, websearch  # noqa: F401
    from job_scraper.browser_fetch import _headless_value, fetch_rendered_html
    ok("job_scraper imports")
    print("  BASE_DIR          = %s" % config.BASE_DIR)
    print("  INPUT_FILE        = %s" % config.INPUT_FILE)
    print("  OUTPUT_FILE       = %s" % config.OUTPUT_FILE)
    print("  LOG_FILE          = %s" % config.LOG_FILE)
    print("  workers           = %s http / %s browser"
          % (config.DEFAULT_WORKERS, config.BROWSER_WORKERS))
    print("  camoufox headless = %r" % _headless_value())
    if "num_positions" in config.OUTPUT_COLUMNS:
        ok("num_positions in OUTPUT_COLUMNS")
    else:
        bad("num_positions missing from OUTPUT_COLUMNS")
    for path, label in ((config.INPUT_FILE, "input file"),
                        (os.path.dirname(config.OUTPUT_FILE) or ".", "output dir"),
                        (os.path.dirname(config.LOG_FILE) or ".", "log dir")):
        if os.path.exists(path):
            ok("%s exists" % label, path)
        else:
            bad("%s missing" % label, path)
    if os.access(os.path.dirname(config.OUTPUT_FILE) or ".", os.W_OK):
        ok("output dir writable")
    else:
        bad("output dir not writable")
except Exception as exc:
    bad("job_scraper imports", str(exc))
    config = None

# ------------------------------------------------------------------- resources
section("5. Host resources")


def _total_ram_gb():
    """Total physical RAM, on Linux, Windows and macOS."""
    try:
        with open("/proc/meminfo") as handle:
            for line in handle:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) / 1024 / 1024
    except Exception:
        pass
    if sys.platform == "win32":
        try:
            import ctypes

            class MemoryStatusEx(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong),
                            ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong),
                            ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong),
                            ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong),
                            ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

            status = MemoryStatusEx()
            status.dwLength = ctypes.sizeof(MemoryStatusEx)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return status.ullTotalPhys / 1024 ** 3
        except Exception:
            pass
    try:
        return (os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")) / 1024 ** 3
    except Exception:
        return 0.0


cpus = os.cpu_count() or 1
print("  vCPUs: %d" % cpus)
total_gb = _total_ram_gb()
if total_gb:
    print("  RAM  : %.1f GB" % total_gb)
    if config is not None:
        need = config.BROWSER_WORKERS * 0.7 + config.DEFAULT_WORKERS * 0.05 + 1.0
        if total_gb < need:
            warn("RAM may be tight",
                 "%d browser + %d http workers want ~%.1f GB"
                 % (config.BROWSER_WORKERS, config.DEFAULT_WORKERS, need))
        else:
            ok("RAM sufficient", "%.1f GB for %d browser + %d http workers"
               % (total_gb, config.BROWSER_WORKERS, config.DEFAULT_WORKERS))
else:
    warn("could not determine RAM")

try:
    usage = shutil.disk_usage(ROOT)
    free_gb = usage.free / 1024 ** 3
    print("  free disk on %s: %.1f GB" % (ROOT, free_gb))
    if free_gb < 5:
        warn("less than 5 GB free", "browser cache and CSV output grow fast")
    else:
        ok("disk space")
except Exception as exc:
    warn("disk probe failed", exc)

try:
    import resource
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    print("  open files: soft=%s hard=%s" % (soft, hard))
    (ok if soft >= 8192 else warn)("file descriptor limit", "soft=%s" % soft)
except ImportError:
    print("  open files: n/a on Windows")

if config is not None and cpus and config.DEFAULT_WORKERS > cpus * 8:
    warn("JOB_SCRAPER_WORKERS is high for %d vCPUs" % cpus,
         "%d threads" % config.DEFAULT_WORKERS)

# ------------------------------------------------------------------- network
if not args.no_net:
    section("6. Network and DNS")
    for host in ("pypi.org", "html.duckduckgo.com", "www.bing.com",
                 "boards-api.greenhouse.io"):
        try:
            start = time.time()
            addr = socket.gethostbyname(host)
            ok("DNS %s" % host, "%s in %.0fms" % (addr, (time.time() - start) * 1000))
        except Exception as exc:
            bad("DNS %s" % host, str(exc))

    # A single dead search engine is not a blocker -- the chain in
    # websearch.py has seven, and DuckDuckGo in particular is commonly
    # blocked or rate-limited. Only "no engine reachable at all" matters.
    ENDPOINTS = [
        ("https://boards-api.greenhouse.io/v1/boards/stripe/jobs", "ats", True),
        ("https://www.bing.com/search?q=test&format=rss", "search", False),
        ("https://html.duckduckgo.com/html/?q=test", "search", False),
        ("https://lite.duckduckgo.com/lite/?q=test", "search", False),
        ("https://www.mojeek.com/search?q=test", "search", False),
    ]
    reachable_search = 0
    try:
        import requests
        for url, kind, critical in ENDPOINTS:
            label = "HTTPS %s" % url.split("/")[2]
            try:
                start = time.time()
                r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
                elapsed = (time.time() - start) * 1000
                detail = "HTTP %d in %.0fms" % (r.status_code, elapsed)
                if r.status_code < 400:
                    ok(label, detail)
                    if kind == "search":
                        reachable_search += 1
                elif critical:
                    bad(label, detail)
                else:
                    warn(label, detail)
            except Exception as exc:
                detail = str(exc)[:120]
                if critical:
                    bad(label, detail)
                else:
                    warn(label + " unreachable", detail + " (chain will skip it)")
        if reachable_search:
            ok("search engines reachable", "%d of %d"
               % (reachable_search, sum(1 for _, k, _ in ENDPOINTS if k == "search")))
        else:
            bad("no search engine reachable",
                "career-page discovery by name will fail; check egress/proxy")
    except Exception as exc:
        bad("requests unusable", str(exc))

    if config is not None:
        section("7. Search-engine chain (live)")
        try:
            from job_scraper.session import ScrapeSession
            from job_scraper.websearch import web_search, engine_status
            results = web_search(ScrapeSession(), "greenhouse careers")
            (ok if results else bad)("web_search returned results", "%d urls" % len(results))
            for name, state in engine_status().items():
                flag = "benched" if state.get("benched_until") else "healthy"
                print("    %-18s %s (failures=%s)" % (name, flag,
                                                      state.get("consecutive_failures")))
        except Exception as exc:
            bad("web_search", str(exc)[:200])

    if camoufox_ready:
        section("8. Camoufox live render")
        try:
            start = time.time()
            html = fetch_rendered_html("https://example.com", timeout_ms=60000,
                                       settle_ms=1500)
            if html and "Example Domain" in html:
                ok("rendered example.com", "%d bytes in %.1fs"
                   % (len(html), time.time() - start))
            elif html:
                warn("render returned unexpected content", "%d bytes" % len(html))
            else:
                bad("render returned nothing", "check logs; try CAMOUFOX_HEADLESS=true")
        except Exception as exc:
            bad("camoufox render", str(exc)[:200])

# --------------------------------------------------------------------- summary
print("\n" + "=" * 60)
print("%d ok, %d warnings, %d failures" % (len(OK), len(WARN), len(BAD)))
if WARN:
    print("warnings: " + ", ".join(WARN))
if BAD:
    print("FAILURES: " + ", ".join(BAD))
    print("=> not ready")
    sys.exit(1)
print("=> ready")
