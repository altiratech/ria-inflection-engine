# RIA Inflection Engine First Slice

Status: locked kickoff slice

## Goal

Ship one evidence-backed, table-first shortlist for a national starter cohort of RIAs with recent brochure updates and both a current plus prior snapshot available.

## Locked Decisions

- First cohort: national adviser cohort, constrained to firms with a recent update and a consecutive brochure pair.
- First UI mode: table-first plus diff drill-down.
- First score dimensions:
  - marketing-rule relevance
  - client or service-mix change
  - operational complexity change
  - confidence
- First output artifact: one ranked JSON payload plus one CSV export.

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
- the repo can publish one shortlist payload without requiring a live API

## Not Yet

- CRM workflows
- outreach sequencing
- merger scoring
- broad benchmarking
