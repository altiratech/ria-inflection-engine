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
- `python3 -m pipeline.refresh_queue --limit 5` to preview the recache queue
- `python3 -m pipeline.refresh_queue --apply --limit 5` to hydrate queued cache gaps

Current first-slice modules:
- `remote_zip.py` for byte-range ZIP indexing and member extraction
- `iapd.py` for reports metadata, filing ZIPs, firm-detail pulls, and cache-only guardrails
- `brochures.py` for snapshot-first brochure text reuse, PDF extraction, and brochure-type checks
- `normalize.py` for section extraction and deterministic deltas
- `score.py` for rubric scoring, subsection-aware excerpt selection, and rationale packaging
- `refresh_queue.py` for previewing and applying the `next_refresh_targets` recache queue

Current first-slice outputs:
- `shortlist_v1.json` and `shortlist_v1.csv`
- `top_delta_<firm_id>.json`
- `cohort_v1.json`
- `cache_report_v1.json` with skip reasons, cache-gap counts, selection-window leftovers, and a compact `next_refresh_targets` recache queue
- `cache_report_v1.json` now also includes a `snapshot_backfill` summary for the explicit brochure-text preflight stage
- `selection_window_v1.json` with deferred selection-window candidates and cached-detail enrichment when available
- `selection_window_comparison_v1.json` with shadow-scored comparisons between deferred fully cached firms and the shortlist floor

Selection behavior note:
- the `20`-pair evaluation window now prefers evaluation-ready pairs (detail + brochure cache available) before raw recency order
- every pair inside that evaluation window is scored before the live top `5` shortlist is finalized
- deferred fully cached firms can now be promoted into the shortlist when they outscore the current shortlist floor
