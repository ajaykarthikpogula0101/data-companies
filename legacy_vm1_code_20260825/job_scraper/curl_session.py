"""curl_cffi transport mirroring ScrapeSession's interface.

Used when TRANSPORT=curl_cffi. Impersonates a real Chrome TLS
fingerprint to reduce blocks, with the same JS-shell / blocked-response
fallback to browser rendering as the requests-based session.
"""

import threading
import time

from curl_cffi import requests as cffi_requests

from .config import DEFAULT_TIMEOUT, REQUEST_HEADERS
from .session import _looks_like_javascript_shell


class CurlCffiScrapeSession:
    """Thread-safe curl_cffi session with retries and browser fallback."""

    def __init__(self, timeout=DEFAULT_TIMEOUT, max_retries=2, impersonate="chrome"):
        self.timeout = timeout
        self.max_retries = max_retries
        self.impersonate = impersonate
        self.backoff = 0.6
        self._local = threading.local()

    def _get_session(self):
        s = getattr(self._local, "session", None)
        if s is None:
            s = cffi_requests.Session(impersonate=self.impersonate)
            s.headers.update(REQUEST_HEADERS)
            self._local.session = s
        return s

    def fetch(self, url, timeout=None, method="GET", **kwargs):
        s = self._get_session()
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                if method.upper() == "POST":
                    r = s.post(url, timeout=timeout or self.timeout, **kwargs)
                else:
                    r = s.get(url, timeout=timeout or self.timeout, **kwargs)
                if r.status_code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                    time.sleep(self.backoff * (attempt + 1))
                    continue
                return r
            except Exception as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(self.backoff * (attempt + 1))
                    continue
        if last_error is not None:
            return None
        return None

    def fetch_text(self, url, timeout=None, **kwargs):
        r = self.fetch(url, timeout=timeout, **kwargs)
        if r is None:
            return None
        if r.status_code not in (200, 201, 203):
            if r.status_code in (403, 405, 406, 423, 429, 451, 455):
                from .browser_fetch import fetch_rendered_html
                return fetch_rendered_html(url)
            return None
        ctype = r.headers.get("Content-Type", "").lower()
        if "json" in ctype:
            return r.text
        if "html" in ctype and _looks_like_javascript_shell(r.text):
            from .browser_fetch import fetch_rendered_html
            rendered = fetch_rendered_html(r.url or url)
            if rendered:
                return rendered
        return r.text

    def fetch_json(self, url, timeout=None, **kwargs):
        r = self.fetch(url, timeout=timeout, **kwargs)
        if r is None:
            return None
        try:
            return r.json()
        except Exception:
            return None

    def post_json(self, url, payload, timeout=None):
        r = self.fetch(url, timeout=timeout, method="POST", json=payload)
        if r is None:
            return None
        try:
            return r.json()
        except Exception:
            return None

    def head_ok(self, url, timeout=8):
        r = self.fetch(url, timeout=timeout, method="HEAD", allow_redirects=True)
        if r is None:
            return False
        return r.status_code < 400
