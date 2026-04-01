# RIA Inflection Engine

RIA Inflection Engine is a standalone repo scaffold hydrated from the KarpathyMerged materials.

## Product Center

Build an evidence-backed filing-delta intelligence system for RIAs using public filing deltas, current SEC themes, and visible evidence.

Primary product lenses:
- supervisory triage
- firm self-surveillance
- peer benchmarking
- hidden-signal discovery across fragmented adviser disclosures

The founding loop is:
1. ingest adviser data and brochure snapshots
2. detect meaningful section-level disclosure changes
3. score which firms or changes warrant closer review
4. show evidence-backed ranked output and diff drill-down

## Current Repo Status

This repo now has a first executable local slice.

Current shipped capabilities:
- cache the latest SEC brochure + filing archives and IAPD firm detail inputs locally
- pair consecutive brochure snapshots for a starter national cohort
- normalize brochure sections into deterministic deltas
- score filing deltas against the current base rubric and SEC themes
- publish ranked JSON/CSV artifacts with focus terms, anchored excerpts, and concise rationales

Current framing status:
- the repo kernel is unchanged
- the product framing is now compliance intelligence and supervisory analytics
- the current executable code still uses the original base score dimensions
- the next scoring expansion is a supervisory overlay plus peer-relative context layered on top of the current dimensions

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

Do not drift into a broad RIA operating system, task manager, policy library, or CRM before the filing-delta intelligence loop is trusted.

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
- writes `selection_window_v1.json` with deferred selection-window candidates enriched from any cached firm detail
- writes `selection_window_comparison_v1.json` with shadow-scored “why not shortlisted” comparisons against the shortlist floor
- mirrors the JSON/CSV artifacts under `artifacts/first_slice/`

Cache-only reruns now reuse existing brochure text snapshots before touching PDF extraction, run an explicit snapshot-backfill preflight for the selected window plus deferred comparison bench, and skip uncached firm-detail candidates instead of falling through to live IAPD fetches. The cache report now also includes a `snapshot_backfill` summary plus a compact `next_refresh_targets` queue so the slow path and the largest missing cache gaps are both explicit. Uncached runs still need `pypdf`, so the shared fastlane interpreter remains the supported default for fresh pulls.

The `20`-pair evaluation window now prioritizes firms that are already ready for a full local comparison (detail + brochure cache available) before falling back to raw recency order, which makes cache-only reruns less sensitive to archive arrival order. Every pair inside that window is then scored locally before the top `5` firms are chosen, and fully cached deferred firms can now displace the shortlist floor when the comparison artifact shows they truly beat it.

The scorer now also suppresses low-value evidence patterns that were making the shortlist harder to trust: generic account-review cadence no longer counts as marketing-rule signal, sponsor-reimbursement / conference boilerplate no longer reads as real advertising signal, custodial-platform support copy is downweighted so it is less likely to outrank actual service-change paragraphs, and generic methods/risk plus brokerage-support boilerplate now lose to real advisory-service sections when both appear in the same brochure slice.

The visible top-three evidence list now uses a lighter explainability pass on top of firm scoring: the first two evidence slots still follow the strongest scored sections, but the final slot now prefers sections with a real focus term and rationale over blank fee-table leftovers when a weaker-but-more-explainable section exists below them. Among those explainable leftovers, the selector now also prefers the most operator-useful section instead of generic custodian/support copy when a cleaner service-change paragraph exists lower in the same firm delta, and the rationale builder now backfills plain-language explanations for those selected sections when the old score threshold would have left the rationale thin or blank.

The excerpt builder now also prefers sentence-aligned focus hits over mid-chunk ellipses, and it joins short risk/heading labels with the explanatory sentence that follows so the visible evidence starts closer to the actual review-relevant language.

## Scoring Direction

Keep the current base dimensions:
- marketing-rule relevance
- client / service-mix change
- operational complexity change
- confidence

Layer the next supervisory dimensions on top:
- exam-priority relevance
- disclosure / materiality severity
- likely policy / procedure impact
- urgency
- evidence quality

Do not collapse this into an opaque risk score. The preferred shape is:
- observed filing-delta profile
- supervisory review profile
- peer-relative context
- clear evidence packet behind every ranked firm

## Category Position

Most regtech starts downstream with task management, attestation, policy storage, or workflow software.

RIA Inflection Engine starts upstream by identifying meaningful disclosure change in public filings before that change gets buried in workflow. That upstream intelligence can feed:
- outsourced compliance review queues
- annual review preparation
- targeted marketing-rule reviews
- surveillance programs
- exam readiness workflows
- peer benchmarking

The product should be understood as compliance intelligence and supervisory analytics for RIAs and their compliance partners.

To preview the recache queue without fetching anything:

`python3 -m pipeline.refresh_queue --limit 5`

To actually hydrate queued targets:

`python3 -m pipeline.refresh_queue --apply --limit 5`

Use `--action fetch_firm_detail` or `--action cache_current_brochure` to narrow the queue. Add `--generate-snapshots` when hydrating brochure PDFs if you also want text snapshots generated.
