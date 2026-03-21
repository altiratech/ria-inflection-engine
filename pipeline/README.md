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
