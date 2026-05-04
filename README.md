# RIA Inflection Engine

RIA Inflection Engine is the public-disclosure intelligence engine intended to feed Altira Trace.

It uses public adviser filings, brochure snapshots, section-level disclosure changes, and visible evidence scoring to produce source-backed intelligence artifacts that Trace can consume in compliance workflows.

## Product Center

Primary lenses:
- supervisory triage
- firm self-surveillance
- peer benchmarking and self-benchmarking
- hidden review-signal discovery across fragmented adviser disclosures

The founding loop is:
1. ingest adviser data and brochure snapshots
2. detect meaningful section-level disclosure changes
3. score which firms or changes warrant closer review
4. show evidence-backed ranked output and diff drill-down

## Status

First executable local slice implemented.

Current capabilities:
- cache SEC brochure and filing archives plus IAPD firm-detail inputs locally
- pair consecutive brochure snapshots for a starter national cohort
- normalize brochure sections into deterministic deltas
- score filing deltas against the current base rubric and SEC themes
- publish ranked JSON/CSV artifacts with focus terms, anchored excerpts, and concise rationales
- run cache-only reruns against existing raw and snapshot data

The next material build step is a supervisory overlay and peer-relative context layered on top of the current scoring kernel.

## Key Docs

- `docs/TRACE_INTEGRATION.md`
- `docs/FOUNDING_PACKET.md`
- `docs/FIRST_SLICE.md`
- `docs/REGTECH_PIVOT_MEMO.md`
- `docs/POSITIONING_PACK.md`

## Quick Start

```bash
git clone https://github.com/altiratech/ria-inflection-engine.git
cd ria-inflection-engine
python3 -m pipeline.run_first_slice
```

For fully local reruns against the existing raw/snapshot cache:

```bash
python3 -m pipeline.run_first_slice --cache-only
```

Preview the recache queue without fetching:

```bash
python3 -m pipeline.refresh_queue --limit 5
```

Hydrate queued targets:

```bash
python3 -m pipeline.refresh_queue --apply --limit 5
```

Run tests:

```bash
python3 -m unittest discover -s tests
```

## Outputs

The first-slice command:
- caches raw SEC/IAPD pulls under `data/raw/`
- stores extracted brochure text under `data/snapshots/`
- writes committed shortlist and delta outputs under `data/canonical/first_slice/`
- mirrors JSON/CSV artifacts under `artifacts/first_slice/`
- writes cache and selection-window reports that explain skip reasons and deferred candidates

Fresh uncached runs may require PDF extraction dependencies. Cache-only reruns reuse existing brochure text snapshots when available.

## Scoring Direction

Current base dimensions:
- marketing-rule relevance
- client / service-mix change
- operational complexity change
- confidence

Next supervisory dimensions:
- exam-priority relevance
- disclosure / materiality severity
- likely policy / procedure impact
- urgency
- evidence quality

The preferred shape is not an opaque risk score. It should remain an observed filing-delta profile, supervisory review profile, peer-relative context, and clear evidence packet behind every ranked firm.

## Repo Shape

```text
configs/   source definitions and rubric versions
data/      raw pulls, snapshots, staging, and canonical data layers
pipeline/  ingest, normalize, extract, score, and publish logic
artifacts/ scored payloads and site outputs
docs/      build truth and guardrails
scripts/   local dev, ingest, and publish helpers
tests/     parser, diff, score, and integration coverage
```

## Product Boundary

RIA Inflection Engine is a data and analytics engine, not the customer-facing workflow product. Trace owns workflow, evidence capture, annual review, exam room, marketing review, vendor oversight, and operator-facing interpretation.

This repo should stay focused on source-backed artifacts such as `firm_delta`, `review_signal`, `evidence_packet`, `theme_mapping`, `peer_context`, and `source_provenance`.

## License

No open-source license has been selected yet. Public source visibility does not grant reuse rights until a license file is added.
