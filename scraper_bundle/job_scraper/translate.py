"""Offline translation to English via Argos Translate (local models).

Free online translators (Google, Microsoft Edge, Lingva) are blocked on the
work networks this scraper runs on, so non-English job postings are translated
with Argos Translate's local ONNX models (see the argos-translate package:
https://github.com/argosopentech/argos-translate).  Models for the languages
this dataset actually hits (de, fr, es, pt, it, nl, ru, ja, sv, da, vi, no,
ko, cs, id -> en) are installed under ~/.local/share/argos-translate.

Only text detected as non-English is sent to the models; already-English text
is returned untouched.  Results are cached on disk (keyed by text hash) so an
interrupted run never re-translates the same text.
"""
import hashlib
import json
import logging
import os
import re
import sys
import threading
import time

log = logging.getLogger("job_scraper")

# The repo's profile.py shadows the stdlib cProfile module when the scraper
# runs from the repository root, and torch (a transitive dependency of
# argos-translate via spacy) imports cProfile at startup.  Drop any sys.path
# entry that would resolve cProfile to the repo file before importing argos,
# then restore them so later imports of repo modules keep working.
_removed_entries = []
for _entry in list(sys.path):
    try:
        _dir = _entry if _entry else os.getcwd()
        if os.path.isfile(os.path.join(_dir, "profile.py")) \
                and not os.path.isfile(os.path.join(_dir, "cProfile.py")):
            sys.path.remove(_entry)
            _removed_entries.append(_entry)
    except OSError:
        pass

from argostranslate import package, translate  # noqa: E402

for _entry in reversed(_removed_entries):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

try:
    package.update_package_index()
except Exception as exc:  # offline is fine; installed models are used directly
    log.debug("argos package index refresh failed: %s", str(exc)[:120])

_ENGINES = {}
_ENGINE_LOCK = threading.Lock()
_PER_LANG_LOCKS = {}
_PROCESS_LOCK = threading.Lock()

# Detectors return region codes (zh-cn, zh-tw, pt-br ...) while the installed
# Argos models are keyed by base language (zh, pt ...).
_LANG_CODE_ALIASES = {
    "zh-cn": "zh", "zh-tw": "zh", "zh-hk": "zh", "zh-cn": "zh",
    "pt-br": "pt", "pt-pt": "pt", "es-mx": "es", "es-es": "es",
    "en-us": "en", "en-gb": "en", "de-de": "de", "fr-fr": "fr",
}


def _normalize_code(code):
    base = (code or "").strip().lower()
    return _LANG_CODE_ALIASES.get(base, base)

_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), ".translation_cache")
_CACHE_PATH = os.path.join(_CACHE_DIR, "translations.jsonl")
_MEMO = {}
_MEMO_LOCK = threading.Lock()

# Argos quality degrades beyond ~500 chars per call; split on sentence ends.
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?。！？؟])\s+|\n+", re.UNICODE)
_CHUNK_MAX = 450


def _load_memo():
    if not os.path.exists(_CACHE_PATH):
        return
    try:
        with open(_CACHE_PATH, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                _MEMO[record["key"]] = record["value"]
    except Exception as exc:
        log.warning("Could not load translation cache: %s", str(exc)[:120])


def _save_memo(key, value):
    os.makedirs(_CACHE_DIR, exist_ok=True)
    with open(_CACHE_PATH, "a", encoding="utf-8") as handle:
        handle.write(json.dumps({"key": key, "value": value},
                                ensure_ascii=False) + "\n")


def _engine(from_code):
    with _ENGINE_LOCK:
        engine = _ENGINES.get(from_code)
        if engine is None:
            try:
                engine = translate.get_translation_from_codes(
                    _normalize_code(from_code), "en")
            except Exception as exc:
                log.warning("No argos model for %s->en: %s",
                            from_code, str(exc)[:120])
                engine = None
            if engine is None:
                _ENGINES[from_code] = None
                return None
            _ENGINES[from_code] = engine
            _PER_LANG_LOCKS[from_code] = threading.Lock()
        return engine


def _translate_chunk(engine, text, lang_lock):
    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]
    if not sentences:
        return text
    # CachedTranslation (used when a model already translated the text once)
    # has only translate(); the raw engine also offers translate_sentences().
    batch_translate = getattr(engine, "translate_sentences", None)
    single_translate = engine.translate
    batches = []
    current = []
    size = 0
    for sentence in sentences:
        if size + len(sentence) > _CHUNK_MAX and current:
            batches.append(current)
            current = []
            size = 0
        current.append(sentence)
        size += len(sentence)
    if current:
        batches.append(current)
    with lang_lock:
        pieces = []
        for batch in batches:
            with _PROCESS_LOCK:  # argos ONNX session is not thread-safe
                if batch_translate is not None:
                    pieces.append(" ".join(batch_translate(batch)))
                else:
                    pieces.append(" ".join(single_translate(s)
                                           for s in batch))
    return " ".join(p for p in pieces if p).strip()


def translate_text(text, from_code="auto"):
    """Translate ``text`` to English.  English input is returned unchanged."""
    text = str(text or "")
    if not text.strip():
        return text
    from_code = _normalize_code(from_code)
    if from_code in ("", "auto", "en", "en-US", "en-GB", "EN"):
        return text
    key = hashlib.sha256(("%s\x1f%s" % (from_code, text)).encode("utf-8")) \
        .hexdigest()
    with _MEMO_LOCK:
        cached = _MEMO.get(key)
    if cached is not None:
        return cached
    engine = _engine(from_code)
    if engine is None:
        return text
    lang_lock = _PER_LANG_LOCKS[from_code]
    try:
        translated = _translate_chunk(engine, text, lang_lock)
    except Exception as exc:
        log.warning("argos translation %s->en failed: %s",
                    from_code, str(exc)[:150])
        return text
    with _MEMO_LOCK:
        if key not in _MEMO:
            _MEMO[key] = translated
    _save_memo(key, translated)
    return translated


def translate_job(job, description_language="", title="", description="",
                  skills=""):
    """Return (title, description, skills) translated to English when the
    source language is not English."""
    lang = (description_language or "").strip().lower()
    if lang in ("", "en", "en-us", "en-gb"):
        return title, description, skills
    return (translate_text(title, lang),
            translate_text(description, lang),
            translate_text(skills, lang))


_load_memo()