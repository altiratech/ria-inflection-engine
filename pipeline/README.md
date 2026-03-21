# Pipeline

Use this folder for the evidence-producing build pipeline.

Recommended subfolders:
- `ingest/`
- `normalize/`
- `extract/`
- `score/`
- `publish/`

Current first-slice entrypoint:
- `/Users/ryanjameson/Desktop/Lifehub/.venv-fastlane/bin/python -m pipeline.run_first_slice`
- `python3 -m pipeline.run_first_slice --cache-only` for snapshot- and raw-cache-only reruns

Current first-slice modules:
- `remote_zip.py` for byte-range ZIP indexing and member extraction
- `iapd.py` for reports metadata, filing ZIPs, firm-detail pulls, and cache-only guardrails
- `brochures.py` for snapshot-first brochure text reuse, PDF extraction, and brochure-type checks
- `normalize.py` for section extraction and deterministic deltas
- `score.py` for rubric scoring, subsection-aware excerpt selection, and rationale packaging

Current first-slice outputs:
- `shortlist_v1.json` and `shortlist_v1.csv`
- `top_delta_<firm_id>.json`
- `cohort_v1.json`
- `cache_report_v1.json` with skip reasons, cache-gap counts, selection-window leftovers, and a compact `next_refresh_targets` recache queue
