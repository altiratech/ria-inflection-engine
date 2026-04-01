# RIA Inflection Engine Regtech Pivot Memo

Status: framing and scoring memo for the supervisory-intelligence pivot

## Strategy Memo

RIA Inflection Engine should keep its current kernel intact and change the primary framing around that kernel. The product already does the hard upstream work that most compliance tooling does not: it ingests public adviser disclosures, pairs brochure snapshots, detects section-level deltas, scores firms with visible evidence, and publishes table-first, diff-first outputs. The pivot is to position that same engine as a serious filing-delta intelligence system for supervisory review, self-surveillance, and peer benchmarking rather than as a GTM-first buying-moment tool.

The new primary claim should be modest and credible: the product helps identify firms or disclosure changes that may warrant closer review under current SEC themes. It should not claim to predict who the SEC will examine or audit. Its value is upstream intelligence that flags meaningful disclosure change before that change gets buried inside downstream workflow systems.

That framing supports three credible lenses at once:
- supervisory triage: which firms look newly worth reviewing, and why
- firm self-surveillance: if I were this firm, where do my recent disclosure changes increase potential review burden
- peer benchmarking: how unusual is this firm’s recent disclosure-change and risk posture versus similar firms

The GTM / buying-moment read still survives, but as a secondary interpretation of the same evidence rather than the lead product story.

## Revised Product Definition

RIA Inflection Engine is an evidence-backed filing-delta intelligence system that helps compliance teams and RIAs identify adviser disclosure changes that may warrant closer review under current SEC themes, with visible evidence and peer context.

## Revised First User

First user:
- an outsourced compliance provider serving RIAs that needs a defensible way to prioritize which recent adviser disclosure changes deserve human review now

## Revised First Workflow

First workflow:
1. open a ranked review table of recent adviser filing deltas
2. filter by recency, firm type, service mix, client mix, and relevant SEC theme
3. inspect the evidence packet for a firm:
   - changed sections
   - visible before/after excerpts
   - exam-theme mapping
   - score profile
   - peer-relative context when available
4. decide whether the firm belongs in:
   - review now
   - monitor
   - compare to peers

## Proposed Scoring Framework

Keep the current base dimensions:
- marketing-rule relevance
- client / service-mix change
- operational complexity change
- confidence

Add the supervisory overlay:
- exam-priority relevance
- disclosure / materiality severity
- likely policy / procedure impact
- urgency
- evidence quality

Add the peer-relative layer when cohort coverage is credible:
- peer-relative percentile
- outlier status
- trend over time

Recommended score shape:
- observed filing-delta profile
- supervisory review profile
- peer-relative context
- evidence packet

Recommended rule:
- do not collapse all of this into a single opaque black-box risk score

## How Peer Benchmarking Should Work

Peer benchmarking should compare a firm against a cohort that is plausible from public disclosure data, not a vague national average. A credible peer group should be defined primarily by:
- registration type
- RAUM / AUM band
- service mix
- client mix
- discretionary versus non-discretionary posture
- custody-related posture where inferable
- fee model / wrap-fee status
- firm complexity markers visible in ADV or brochure text

Geography can be a secondary filter, not the core cohort definition.

Recommended peer outputs:
- percentile by key scoring dimension
- outlier flag when a firm sits materially above cohort norms
- recent trend versus the firm’s own prior disclosures
- cohort median / percentile context beside the firm’s current delta profile

## Terminology Changes

Prefer:
- review priority
- supervisory triage
- filing-delta intelligence
- evidence packet
- exam-theme mapping
- self-surveillance
- peer-relative context
- review queue

Avoid:
- lead score
- hot lead
- firms to contact
- likely buyer
- audit prediction
- warning engine
- compliance OS

## Minimum UI / Output Changes

Keep the product table-first and diff-first, but change the reading posture:
- rename the top table conceptually from contact shortlist to review queue
- show “why this firm is worth review now” before any commercial interpretation
- display the evidence packet more explicitly:
  - changed section
  - before / after excerpt
  - mapped SEC theme
  - score breakdown
  - confidence / evidence-quality cue
- add a peer-relative context column or drawer when available
- keep GTM / buying-moment interpretation behind a secondary label or export path, not the primary UI language

## What The Current Repo Already Supports

Already supported:
- SEC / IAPD source ingestion and cache
- brochure snapshot pairing
- section-level normalized deltas
- visible evidence excerpts and rationale
- current SEC-theme mapping hooks
- table-first, diff-first canonical artifacts
- shortlist / comparison / cohort artifacts that can be reframed as review outputs

Still missing:
- supervisory overlay dimensions in code and config
- evidence-quality as an explicit scored field
- policy / procedure impact taxonomy
- urgency logic tuned for supervisory use
- peer-group construction rules in code
- percentile / outlier / trend calculations
- supervisory-first terminology throughout output artifacts
- explicit review-queue and evidence-packet presentation in the product surface

## Recommended Next Implementation Steps

1. Add a supervisory overlay rubric to config while preserving the current base dimensions.
2. Split current output language into:
   - observed change
   - supervisory interpretation
   - peer-relative context
3. Add an explicit `evidence_quality` dimension driven by excerpt quality, section specificity, and source clarity.
4. Add a first peer-group builder using public variables already available in adviser detail and brochure snapshots.
5. Compute peer-relative percentile and outlier status for the current first-slice cohort.
6. Reframe canonical artifacts and CSV headings from shortlist/contact language to review-queue language.
7. Add visible exam-theme mapping to every top-ranked firm packet where that mapping affects rank.
8. Preserve GTM as a secondary export or interpretation path after the supervisory framing is stable.
