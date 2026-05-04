# Trace Integration Doctrine

Status: architectural decision record

## Decision

Develop RIA Inflection Engine and Altira Trace separately for now, but under one product strategy.

Trace is the customer-facing RIA compliance product.
RIA Inflection Engine is the public-disclosure intelligence engine that feeds Trace.

Do not merge the repos yet.
Do not let RIA Inflection Engine become a second customer-facing product.

## Why This Decision

The two systems have different jobs and different maturity curves.

RIA Inflection Engine owns messy public-data work:
- SEC / IAPD source ingestion
- raw and normalized disclosure caches
- brochure snapshot pairing
- section-level filing deltas
- scoring and evidence quality
- peer-relative analytics
- versioned intelligence artifacts

Trace owns the operator product:
- users and roles
- firm profile
- obligations and workflows
- evidence capture
- annual review
- exam room
- marketing review
- vendor oversight
- dashboards and user-facing interpretation

Keeping them separate lets the data engine iterate quickly without pulling experimental parsing and scoring logic into the Trace app. Keeping them under one product strategy prevents duplicate product narratives and overlapping workflow surfaces.

## System Boundary

RIA Inflection Engine should answer:
- What changed in public adviser disclosures?
- Which changes appear review-worthy?
- What evidence supports the ranking?
- Which SEC themes does the change map to?
- How unusual is the pattern versus peers?

Trace should answer:
- What does the operator need to do?
- What is due or blocked?
- What evidence is missing?
- Which review workflow should consume this signal?
- How should the firm preserve proof and follow through?

## Contract Direction

The integration should revolve around versioned artifacts, not shared database tables at first.

Likely contract objects:
- `firm_delta`
- `review_signal`
- `evidence_packet`
- `theme_mapping`
- `peer_context`
- `source_provenance`

The first Trace integration should consume static canonical JSON artifacts before any live API, queue, or database integration.

## Near-Term Development Model

1. Keep RIA Inflection Engine as a local-first data engine.
2. Stabilize the artifact contract.
3. Produce Trace-facing sample payloads.
4. Add a static import or fixture path inside Trace.
5. Surface the imported intelligence in one bounded Trace workflow.
6. Revisit packaging or merging only after the contract and Trace consumer surface are stable.

## Merge Criteria

Do not merge while:
- source ingestion is still experimental
- scoring rubrics are changing frequently
- output schemas are unstable
- Trace has no stable consumer surface
- integration can work through versioned artifacts

Consider merging, packaging, or converting the engine into a service only when:
- the artifact contract is stable
- Trace has a stable consumer surface
- repo separation creates more friction than clarity
- deployment and operations needs make the current boundary expensive

## Non-Overlap Rules

RIA Inflection Engine should not own:
- user accounts
- workflow state
- assignments
- approvals
- evidence management
- annual review workflow
- exam room workflow
- marketing review workflow
- vendor oversight workflow
- customer-facing product positioning

Trace should not own:
- SEC / IAPD raw source ingestion
- brochure parsing experiments
- section-level delta scoring
- public-disclosure cache layout
- peer-relative scoring mechanics

## Current Implication

Existing RIA Inflection docs that sound like standalone external product positioning should be treated as module-level language until they are rewritten around Trace consumption.
