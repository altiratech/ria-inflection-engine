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

This repo is a fresh scaffold.

The current goal is to establish:
- the founding docs
- implementation guardrails
- a stable repo shape

before major code expands.

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
