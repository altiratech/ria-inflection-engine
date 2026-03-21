# RIA Inflection Engine Implementation Entry Brief

Purpose: keep the first engineering passes aligned with the founding inflection loop.

## Current Product Center

Build the smallest serious loop:

1. ingest recent adviser snapshots
2. normalize brochure sections
3. compute meaningful diffs
4. score likely buying moments
5. let the user inspect evidence and shortlist firms

## First Build Blocks

### 1. Data model foundation

Lock schemas for:
- firms
- filing snapshots
- brochure documents
- brochure sections
- delta events
- scores
- evidence snippets

### 2. Core APIs or payloads

Initial product access should support:
- ranked adviser list
- filterable segment views
- firm detail
- evidence-backed diff retrieval

### 3. Web surfaces

Initial web surfaces should support:
- ranked table
- filter panel
- firm detail page
- diff view

## Explicit Defers

Do not treat these as founding blockers:
- CRM workflow
- outreach sequencing
- merger scoring
- broad benchmarking

## Design Guardrail

This product should feel like serious operating intelligence, not like a flashy sales tool.
