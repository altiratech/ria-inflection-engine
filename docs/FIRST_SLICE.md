# RIA Inflection Engine First Slice

Status: locked kickoff slice

## Goal

Ship one evidence-backed, table-first review queue for a national starter cohort of RIAs with recent brochure updates and both a current plus prior snapshot available.

## Locked Decisions

- First cohort: national adviser cohort, constrained to firms with a recent update and a consecutive brochure pair.
- First UI mode: table-first plus diff drill-down.
- First primary lens: supervisory triage.
- Supported adjacent lenses:
  - firm self-surveillance
  - peer-relative context where coverage allows
  - hidden-signal discovery across filings and themes
- Current implemented base score dimensions:
  - marketing-rule relevance
  - client or service-mix change
  - operational complexity change
  - confidence
- Next supervisory overlay dimensions:
  - exam-priority relevance
  - disclosure / materiality severity
  - likely policy / procedure impact
  - urgency
  - evidence quality
- First output artifact: one ranked JSON payload plus one CSV export that read as a review queue with visible evidence.

## First Source Set

- SEC adviser metadata
- current brochure files
- one recent prior brochure snapshot
- SEC examination priorities
- SEC risk alerts

## First Files To Touch

- `configs/`
- `pipeline/`
- `artifacts/`
- `tests/`

## Done When

- one starter cohort can be fetched and cached
- brochure sections can be paired across two snapshots
- material deltas can be scored with visible evidence
- output can answer `which firms look newly worth reviewing, and why?`
- the repo can publish one review-oriented shortlist payload without requiring a live API

## Not Yet

- CRM workflows
- task management / attestation
- policy-library software
- predicting who the SEC will audit
- full peer benchmarking at national coverage scale
