# RIA Inflection Engine Development Packet

Status: hydrated repo-local build packet

## Purpose

This file pulls the detailed product, data, schema, workflow, and execution guidance for this repo into one local packet so development can proceed from inside the repo without reopening the Karpathy source folders.

## Source Materials Absorbed

- `Business Ideas/01_Karpathy/KarpathyMerged/app_ideas_catalog.md`
- `Business Ideas/01_Karpathy/KarpathyMerged` concept-specific implementation outputs for the RIA product
- `Business Ideas/01_Karpathy/KarpathyMerged/build_backlog.md`
- `Business Ideas/01_Karpathy/KarpathyMerged/assumption_risks.md`
- `Business Ideas/01_Karpathy/KarpathyMerged/evaluation_results.md`
- `Business Ideas/01_Karpathy/KarpathyMerged/merged_concepts.md`
- `Business Ideas/01_Karpathy/KarpathyMerged/implementation_blueprint.md`
- `Business Ideas/01_Karpathy/Karpathy1/03_top_candidates_mvp_specs.md`
- `Business Ideas/01_Karpathy/Karpathy1/05_assumption_risks.md`

## Product Thesis

Use time-series diffs across adviser filings and brochures to detect meaningful disclosure changes that may warrant closer review under current SEC themes.

This is not a static adviser atlas.
It is an evidence-backed filing-delta intelligence system with a strong "why now" drill-down.

## Why This Exists

- static firm directories do not answer who changed in a way that matters now
- outsourced compliance teams and RIAs need evidence-backed prioritization, not broad segmentation
- filing deltas plus current SEC themes create a more actionable review surface than downstream workflow systems alone
- fragmented public adviser disclosures contain non-obvious patterns that manual review often misses

## First Users

Primary first buyer:
- outsourced compliance providers serving RIAs

Strong secondary buyers:
- RIAs doing self-surveillance or annual review preparation
- consultants performing peer benchmarking or targeted thematic reviews
- compliance analytics teams building broader surveillance programs

## Job To Be Done

Identify advisers whose recent public disclosure changes signal new compliance review burden, supervisory relevance, or peer-relative outlier behavior.

## Canonical Units

Primary unit:
- adviser firm over time

Operational unit:
- `firm_delta`
- more explicitly: `firm x filing snapshot delta`

## Related And Absorbed Ideas

- `ria_succession_plus_operating_leverage_engine`
  - survives here as the broader intuition around operational complexity and modernization pressure
- `ria_launch_complexity_atlas`
  - contributes segmentation and workflow context, but is not the v1 product
- `ria_merger_breakage_map`
  - remains outside the current product direction
- `ai_automation_surface_map_regulated_workflows`
  - is a useful internal design layer, not the v1 user-facing surface
- `ria_operating_stress_os`
  - is the long-range expansion path after the ranked inflection loop works

## Data Source Inventory

First-tier v1 sources:
- SEC Form ADV data page
  - official current and historical adviser data path
- Investment Adviser Public Disclosure / data compilation
  - firm-level adviser metadata
- Form ADV Part 2 brochure data
  - brochure text for delta and section analysis
- SEC 2026 Examination Priorities
  - current thematic overlay
- SEC Risk Alerts
  - current thematic overlay
- December 16, 2025 Marketing Rule alert
  - concrete v1 theme for score relevance

Useful later overlays:
- Form D
- EDGAR
- additional SEC thematic guidance

## Data Truth Rules

- adviser records, filing text, source URLs, and source timestamps must never be fabricated
- filings and deltas are observed
- review-priority, supervisory, and peer-relative interpretations are inferred
- raw source artifacts, normalized text, observed deltas, scored outputs, and peer-relative outputs must remain separate layers
- no score should appear without visible evidence

## Canonical Schema

### `firms`
- `firm_id`
- `sec_number`
- `crd_number`
- `legal_name`
- `state`
- `aum_band`
- `employee_count_band`
- `client_mix_summary`
- `status`

### `filing_snapshots`
- `snapshot_id`
- `firm_id`
- `filing_date`
- `form_type`
- `source_url`
- `source_hash`
- `raw_path`

### `brochure_documents`
- `document_id`
- `snapshot_id`
- `document_type`
- `download_url`
- `raw_text_path`
- `normalized_markdown_path`

### `brochure_sections`
- `section_id`
- `document_id`
- `section_key`
- `section_title`
- `section_text`

### `delta_events`
- `delta_id`
- `firm_id`
- `old_snapshot_id`
- `new_snapshot_id`
- `section_key`
- `change_type`
- `old_text`
- `new_text`
- `diff_summary`

### `regulatory_themes`
- `theme_id`
- `theme_name`
- `source_url`
- `source_date`
- `theme_summary`
- `relevant_keywords`

### `scores`
- `score_id`
- `firm_id`
- `delta_id`
- `marketing_rule_relevance`
- `client_service_mix_change`
- `operational_complexity_change`
- `confidence`
- `exam_priority_relevance`
- `disclosure_materiality_severity`
- `policy_procedure_impact`
- `urgency`
- `evidence_quality`
- `peer_relative_percentile`
- `outlier_status`
- `trend_direction`
- `rationale`
- `model_name`
- `rubric_version`
- `scored_at`

### `evidence_snippets`
- `evidence_id`
- `score_id`
- `source_type`
- `source_url`
- `section_key`
- `snippet_text`
- `snippet_role`

## Scoring Model

Current implemented base dimensions:
- `marketing_rule_relevance`
- `client_service_mix_change`
- `operational_complexity_change`
- `confidence`

Supervisory overlay dimensions to add next:
- `exam_priority_relevance`
- `disclosure_materiality_severity`
- `policy_procedure_impact`
- `urgency`
- `evidence_quality`

Peer-relative dimensions to add when cohort coverage is credible:
- `peer_relative_percentile`
- `outlier_status`
- `trend_direction`

Scoring rules:
- first separate material from cosmetic deltas
- score section-delta units before any firm-level aggregation
- keep deterministic diff evidence visible beside any model scoring
- version rubrics and model outputs
- keep observed filing change, supervisory interpretation, and peer-relative context as separate readable layers
- do not collapse the output into a black-box enforcement or audit prediction score

## Evidence Standard

Every meaningful score should show:
- affected brochure section
- before text
- after text
- concise diff summary
- linked regulatory theme when applicable
- filing date and source metadata

Without this, the product collapses into vague compliance theater.

## Product Surfaces

Primary surface:
- ranked table of firms by review priority and visible evidence

Secondary surfaces:
- filter panel by state, AUM band, recency, and service/client mix
- firm detail view
- section-level diff viewer
- regulatory theme panel
- review queue export
- peer-relative context panel

UI choice:
- do not treat treemap as the primary v1 entry point
- the more useful expression is table-first with diff inspection

## Suggested First Segment

Start with:
- a constrained slice of advisers with recent updates
- one geography slice or one AUM slice
- current brochure files plus recent prior snapshots

Avoid:
- full-universe brochure ingestion on day one

## MVP Build Sequence

Phase 0:
- confirm first buyer
- confirm first segment
- define material delta rules
- define first 3-4 rubric dimensions

Phase 1:
- implement official adviser metadata pull and cache
- fetch brochure documents for the starter cohort
- snapshot and hash raw source artifacts

Phase 2:
- normalize brochure documents into stable sections
- map sections across consecutive snapshots
- compute deterministic deltas

Phase 3:
- extract reusable regulatory themes from SEC priorities and alerts
- run rubric scoring on material deltas
- save rationale, evidence, and confidence

Phase 4:
- publish ranked list payloads
- build firm detail and diff surfaces
- support review-queue export or monitoring

Phase 5:
- tune thresholds
- suppress obvious false positives
- validate buyer trust with evidence-first reviews

## Recommended First 10 Tasks

1. Create source-config files for SEC and adviser sources.
2. Implement raw adviser metadata download and cache.
3. Implement brochure fetch and text cache.
4. Normalize brochure documents into sectioned markdown or text.
5. Build section matching and diff logic across snapshots.
6. Create a small theme extractor for SEC priorities and risk alerts.
7. Write versioned rubrics for the four core scores.
8. Implement a score runner with strict JSON and evidence capture.
9. Publish frontend payloads for ranked list plus firm detail.
10. Build the table-first UI with filters and diff drill-down.

## Key Risks

Source and linkage risks:
- current adviser retrieval paths can be operationally awkward
- historical snapshots may be patchy
- brochure sectioning quality is a hard dependency

Scoring risks:
- cosmetic deltas may look material
- brochure tone can be over-interpreted
- review burden is not the same thing as enforcement risk
- peer-relative context can mislead if cohort quality is weak

Framing risks:
- avoid age-based or speculative succession claims
- avoid language that implies certain enforcement or audit prediction
- avoid fear-marketing posture
- avoid regtech drift into workflow software before the upstream intelligence layer is trusted

Safer framing:
- operational complexity
- service-model change
- compliance review burden
- closer-review signal under current SEC themes
- peer-relative outlier with visible confidence

## Validation Checklist

1. Confirm the official retrieval path for the first adviser slice.
2. Validate one recent-versus-prior snapshot pair end to end.
3. Test brochure section normalization on a mixed sample.
4. Build a manual material-versus-cosmetic review set.
5. Translate SEC overlays into 2-4 sharp rubric dimensions.
6. Show mocked ranked output to one likely review-oriented buyer type.

## Placeholder Rule

Use:
- explicit empty arrays
- explicit source-status notes
- `placeholder: true` where needed

Do not use:
- fabricated adviser records
- invented AUM values
- synthetic score rows

## Local Repo Translation

Current local scaffold:
- `apps/api/`
- `apps/web/`
- `packages/shared/`
- `docs/`
- `scripts/`
- `tests/`

Recommended implementation expansion inside this repo:
- `configs/`
  - source definitions and scoring rubrics
- `data/`
  - raw, snapshots, staging, canonical
- `pipeline/`
  - ingest, normalize, extract, score, publish
- `artifacts/`
  - site payloads and scored outputs

Working rule:
- `apps/api` should stay thin and orchestration-focused
- `apps/web` should hold the operator UI
- the real product truth should live in `configs/`, `data/`, `pipeline/`, and `artifacts/`
