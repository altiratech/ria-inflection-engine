# RIA Inflection Engine Implementation Entry Brief

Purpose: keep the first engineering passes aligned with the filing-delta intelligence loop.

## Current Product Center

Build the smallest serious loop:

1. ingest recent adviser snapshots
2. normalize brochure sections
3. compute meaningful diffs
4. score which firms or sections may warrant closer review
5. let the user inspect evidence, theme mapping, and ranked review priority

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
- ranked adviser review list
- filterable segment or peer views
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
- task management
- attestation or policy storage
- predicting who the SEC will audit
- broad peer benchmarking at national scale

## Design Guardrail

This product should feel like serious compliance intelligence and supervisory analytics, not like a flashy AI PDF reader or generic productivity app.
