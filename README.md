# RIA Inflection Engine

RIA Inflection Engine is a standalone repo scaffold hydrated from the KarpathyMerged materials.

## Product Center

Build a ranked buying-moment engine for RIAs using public filing deltas and current SEC regulatory themes.

The founding loop is:
1. ingest adviser data and brochure snapshots
2. detect meaningful changes
3. score likely buying moments
4. show evidence-backed ranked output

## Current Repo Status

This repo now has a first executable local slice.

Current shipped capabilities:
- cache the latest SEC brochure + filing archives and IAPD firm detail inputs locally
- pair consecutive brochure snapshots for a starter national cohort
- normalize brochure sections into deterministic deltas
- score buying-moment signals against the locked rubric and SEC themes
- publish ranked JSON/CSV shortlist artifacts with focus terms, anchored excerpts, and concise rationales

## Canonical Build Truth

Treat these docs as authoritative:
- `docs/FOUNDING_PACKET.md`
- `docs/DEVELOPMENT_PACKET.md`
- `docs/BOOTSTRAP.md`
- `docs/FIRST_SLICE.md`
- `docs/IMPLEMENTATION_ENTRY_BRIEF.md`
- `docs/ARCHITECTURE_GUARDRAILS.md`

## Planned Repo Shape

- `configs/`
  - source definitions and rubric versions
- `data/`
  - raw pulls, snapshots, staging, and canonical data layers
- `pipeline/`
  - ingest, normalize, extract, score, and publish logic
- `artifacts/`
  - scored payloads and site outputs
- `apps/api/`
  - ingest, parsing, diffing, scoring APIs if needed
- `apps/web/`
  - ranked list, filters, firm detail, and diff UI
- `packages/shared/`
  - shared contracts and schemas
- `docs/`
  - build truth and guardrails
- `scripts/`
  - local dev, ingest, and publish helpers
- `tests/`
  - parser, diff, score, and integration coverage

## Build Rule

Do not drift into a broad RIA operating system before the inflection loop works.

## First Slice CLI

Run the local-first first slice with:

`/Users/ryanjameson/Desktop/Lifehub/.venv-fastlane/bin/python -m pipeline.run_first_slice`

For fully local reruns against the existing raw/snapshot cache:

`python3 -m pipeline.run_first_slice --cache-only`

The command:
- caches raw SEC/IAPD pulls under `data/raw/`
- stores extracted brochure text under `data/snapshots/`
- writes committed shortlist + delta outputs under `data/canonical/first_slice/`
- writes `cache_report_v1.json` with explicit skip reasons and cache-gap counts
- mirrors the JSON/CSV artifacts under `artifacts/first_slice/`

Cache-only reruns now reuse existing brochure text snapshots before touching PDF extraction and skip uncached firm-detail candidates instead of falling through to live IAPD fetches. The cache report now also includes a compact `next_refresh_targets` queue so the largest missing cache gaps turn into an explicit local recache list. Uncached runs still need `pypdf`, so the shared fastlane interpreter remains the supported default for fresh pulls.

To preview the recache queue without fetching anything:

`python3 -m pipeline.refresh_queue --limit 5`

To actually hydrate queued targets:

`python3 -m pipeline.refresh_queue --apply --limit 5`

Use `--action fetch_firm_detail` or `--action cache_current_brochure` to narrow the queue. Add `--generate-snapshots` when hydrating brochure PDFs if you also want text snapshots generated.
