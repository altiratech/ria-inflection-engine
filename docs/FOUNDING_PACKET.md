# RIA Inflection Engine Founding Packet

Status: canonical current-scope document

## 1. Project

- Project name: RIA Inflection Engine
- Owner: Ryan Jameson
- Date opened: 2026-03-20
- Status: scaffolded

## 2. One-Sentence Product Definition

`This product helps outsourced compliance teams and RIAs identify disclosure changes that may warrant closer review under current SEC themes by scoring public filing deltas with visible evidence and peer context, without turning into a generic compliance workflow system.`

## 3. First User

- Primary user: outsourced compliance provider serving RIAs
- What they are trying to get done: identify which firms or client relationships look newly worth reviewing now, and why
- What they do today instead: manual brochure review, annual review prep, ad hoc exam-theme checks, and spreadsheet watchlists
- Why they would switch: ranked evidence-backed review priority is faster, more legible, and easier to defend than intuition alone
- Adjacent users:
  - RIAs doing self-surveillance or exam-readiness review
  - RIAs and consultants doing peer benchmarking or self-benchmarking
  - compliance analytics teams building broader surveillance programs

## 4. First Workflow

1. user opens a ranked table of recently changed advisers prioritized for review
2. user filters by peer segment, recency, section, and exam-theme relevance
3. user inspects the evidence packet behind a high-priority firm delta
4. user decides whether to review now, monitor, or compare the firm against peers

## 5. Canonical Object

- Canonical object: `firm_delta`
- Why this is the product center: the product is about meaningful adviser disclosure change over time
- What is explicitly not the canonical object: CRM record, compliance task, policy document, or generic firm profile

## 6. Current Scope

- In scope:
  - adviser metadata ingest
  - brochure snapshot normalization
  - section-level diffing
  - evidence-backed scoring
  - exam-theme mapping
  - ranked table-first and diff-first review outputs

## 7. Explicit Non-Goals

- Not in scope now:
  - CRM workflow
  - task management or attestation
  - policy-library software
  - pairwise merger compatibility
  - predicting who the SEC will audit
  - full RIA operating system scope

## 8. Do-Not-Drift-Into

- Drift risks to avoid:
  - black-box risk scoring with no reasoning
  - broad enterprise compliance platform
  - audit prediction claims
  - M&A product before the core loop works
  - non-compliance product drift that weakens supervisory focus

## 9. Approved Terminology

| Use | Avoid | Why |
|---|---|---|
| `supervisory triage` | `generic signal ranking` | keeps the product review-oriented and grounded |
| `review priority` | `warning` | avoids overclaiming certainty |
| `firm_delta` | `signal` alone | forces the product to stay tied to observed change |
| `exam-theme mapping` | `risk score` alone | requires visible reasoning instead of opaque labels |
| `self-surveillance` | `self-audit prediction` | keeps the product focused on review burden, not forecasting enforcement |
| `peer-relative context` | `league table` | keeps benchmarking analytical rather than gamified |

## 10. Repo / Architecture Pattern

- Repo shape: standalone mono-repo scaffold
- Frontend stack: React + TypeScript
- Backend stack: Python-first ingest/scoring, thin API only when needed
- Shared contracts: `packages/shared`
- Deployment target: local-first scaffold, deployment target to be chosen after schema/API pass
- Explicitly rejected patterns:
  - heavy enterprise platform architecture before proof
  - monolithic backend-first build

## 11. Data Truth Rules

- Source of truth: official adviser and SEC sources
- What is observed vs inferred:
  - filings, snapshots, sections, and deltas are observed
  - scores, supervisory interpretations, and peer-relative context are inferred
- What can be missing: historical coverage, theme confidence, and peer coverage
- What must never be faked: adviser records, filing text, source timestamps, or evidence links
- How uncertainty should be shown: confidence plus evidence snippets plus explicit peer-coverage limits

## 12. Quality Gates

- Required validation:
  - parser works on representative brochures
  - diffing suppresses cosmetic noise
  - no score without evidence
  - current SEC-theme mapping is visible where it affects ranking

## 13. First 2-4 Week Build Sequence

| Order | Build block | Why now |
|---|---|---|
| 1 | schema and ingest | foundation for everything else |
| 2 | brochure normalization and diffs | core product truth |
| 3 | scoring and evidence storage | creates review value |
| 4 | ranked UI and review workflow | proves usability |

## 14. Open Questions That Do Not Block Start

- Open but non-blocking:
  - kickoff decisions are now locked in `docs/FIRST_SLICE.md`
  - when peer benchmarking should graduate from cohort-relative context to a first-class surface
  - which additional public regulatory data sources most improve hidden-signal detection after the first slice

## 15. Go / No-Go Check Before Real Code

- [x] one-sentence product definition is stable
- [x] first user is specific
- [x] first workflow is specific
- [x] canonical object is clear
- [x] non-goals are written down
- [x] terminology is coherent
- [x] repo pattern is chosen
- [x] data truth rules are defined
