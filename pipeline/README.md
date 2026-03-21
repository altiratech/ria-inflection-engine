# Pipeline

Use this folder for the evidence-producing build pipeline.

Recommended subfolders:
- `ingest/`
- `normalize/`
- `extract/`
- `score/`
- `publish/`

Current first-slice entrypoint:
- `python3 -m pipeline.run_first_slice`

Current first-slice modules:
- `remote_zip.py` for byte-range ZIP indexing and member extraction
- `iapd.py` for reports metadata, filing ZIPs, and firm-detail pulls
- `brochures.py` for PDF text extraction and brochure-type checks
- `normalize.py` for section extraction and deterministic deltas
- `score.py` for rubric scoring, anchored excerpt selection, and rationale packaging
