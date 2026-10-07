# Job data cleaner v2

This is a post-processing tool. It does not import, edit, restart, or stop the
scraper, tmux sessions, or Azure VMs. It also refuses to overwrite its input.

It produces exactly the requested 26-column schema. Existing values are
preserved; missing values are extracted conservatively from the job title and
description. The current OpenRouter result sidecar can be reused offline.

Education level, stream, and literal qualification are classified independently.
Ambiguous language such as ordinary workplace `training` does not become
`Vocational Training` unless explicit education evidence is present.

Run from `D:\data_companies`:

```powershell
python .\job_data_cleaner\clean_jobs.py .\company_jobs_aligned.csv `
  --output .\job_data_cleaner\output\company_jobs_aligned_cleaned_v2.csv `
  --llm-results .\company_jobs_aligned.csv.llm_results.jsonl `
  --report .\job_data_cleaner\output\company_jobs_aligned_report_v2.json
```

Facts not present in the source remain blank. This is intentional: invented
salary, education, experience, or dates would make the dataset unreliable.
