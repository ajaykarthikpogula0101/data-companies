# C/V/D Job Delivery Scraper

Scrapes C/V/D-level career postings for the C/V/D target departments
(Operations, Procurement, Finance, IT, Purchasing) from each company website,
and writes at most ONE job per department per company.

## Quick start

```bat
:: Windows
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium

python run_new_pages.py --input input.xlsx --output hiring_10Nov_CVD_delivery.csv --workers 25 --no-resume
```

Pause/resume at any time — progress is saved to `hiring_10Nov_CVD_delivery.csv.progress`.
Re-run the same command to continue; `--no-resume` starts over. On completion,
deliver the CSV (open it in Excel if preferred).

## Options

| Flag | Meaning |
| ---- | ------- |
| `--input FILE` | Input workbook (columns: Company/Name, Website, Country). |
| `--output FILE` | Output CSV to append to. |
| `--workers N` | Parallel workers (default 10; ~25 is a good sweet spot). |
| `--limit N` | Scrape only the first N companies. |
| `--no-resume` | Start from scratch (ignore saved progress). |
| `--no-search` | Disable web-search fallback (faster, fewer hits). |
| `--trend` | (if present) example of a passthrough flag — ignored otherwise. |

## Notes

- Non-English job postings are translated to English with the translation cache
  in `job_scraper/translate.py` (first run rebuilds the cache; the stderr line
  `Could not load translation cache` is harmless).
- Browser rendering of JS-heavy sites uses Playwright; install Chromium with
  `playwright install chromium` or set `JOB_SCRAPER_*` env vars / `--no-search`
  to reduce browser use.
- Timeouts, workers and budgets are all tunable via `job_scraper/config.py`.