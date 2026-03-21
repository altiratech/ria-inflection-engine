# RIA Inflection Engine Founding Packet

Status: canonical current-scope document

## 1. Project

- Project name: RIA Inflection Engine
- Owner: Ryan Jameson
- Date opened: 2026-03-20
- Status: scaffolded

## 2. One-Sentence Product Definition

`This product helps outsourced compliance providers and RIA-focused GTM teams find advisers with fresh buying-moment signals using public filing deltas and current SEC themes, without becoming a generic compliance operating system.`

## 3. First User

- Primary user: outsourced compliance provider serving RIAs
- What they are trying to get done: find firms worth contacting now
- What they do today instead: manual search, intuition, and broad list-building
- Why they would switch: ranked evidence-backed targets are faster and more legible

## 4. First Workflow

1. user opens a ranked list of recently changed advisers
2. user filters by segment and recency
3. user inspects the evidence behind high-scoring firms
4. user exports or records a shortlist to contact or monitor

## 5. Canonical Object

- Canonical object: `firm_delta`
- Why this is the product center: the product is about meaningful adviser change over time
- What is explicitly not the canonical object: CRM record, full firm dossier, or generalized compliance task

## 6. Current Scope

- In scope:
  - adviser metadata ingest
  - brochure snapshot normalization
  - section-level diffing
  - buying-moment scoring
  - ranked evidence-backed UI

## 7. Explicit Non-Goals

- Not in scope now:
  - outreach automation
  - workflow/task management
  - pairwise merger compatibility
  - full RIA operating system scope

## 8. Do-Not-Drift-Into

- Drift risks to avoid:
  - generic lead scoring
  - broad enterprise compliance platform
  - M&A product before the core loop works

## 9. Approved Terminology

| Use | Avoid | Why |
|---|---|---|
| `buying moment` | `hot lead` | keeps the product grounded in evidence rather than sales hype |
| `firm delta` | `signal` alone | forces the product to stay tied to observed change |
| `regulatory theme` | `warning` | avoids overclaiming certainty |

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
- What is observed vs inferred: filings/deltas are observed, scores are inferred
- What can be missing: historical coverage and confidence
- What must never be faked: adviser records, filing text, or source timestamps
- How uncertainty should be shown: confidence plus evidence snippets

## 12. Quality Gates

- Required validation:
  - parser works on representative brochures
  - diffing suppresses cosmetic noise
  - no score without evidence

## 13. First 2-4 Week Build Sequence

| Order | Build block | Why now |
|---|---|---|
| 1 | schema and ingest | foundation for everything else |
| 2 | brochure normalization and diffs | core product truth |
| 3 | scoring and evidence storage | creates decision value |
| 4 | ranked UI and shortlist workflow | proves usability |

## 14. Open Questions That Do Not Block Start

- Open but non-blocking:
  - kickoff decisions are now locked in `docs/FIRST_SLICE.md`
  - whether export should be CSV only in v1 or wait until after the first trusted shortlist loop

## 15. Go / No-Go Check Before Real Code

- [x] one-sentence product definition is stable
- [x] first user is specific
- [x] first workflow is specific
- [x] canonical object is clear
- [x] non-goals are written down
- [x] terminology is coherent
- [x] repo pattern is chosen
- [x] data truth rules are defined
