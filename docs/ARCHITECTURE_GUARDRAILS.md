# RIA Inflection Engine Architecture Guardrails

## Scope Guardrails

- Build the ranked inflection loop first.
- Keep the first user and workflow fixed.
- Do not add merger or CRM layers before the core loop is working.

## Data Guardrails

- Core objects:
  - `firm`
  - `snapshot`
  - `section`
  - `firm_delta`
  - `score`
  - `evidence`
- Keep raw, normalized, and inferred layers separate.
- Synthetic data is prohibited.
- No score without visible evidence.

## Product Guardrails

- ranked move first
- evidence before explanation flourish
- table and diff views before ornamental overview screens

## Repo Guardrails

- Keep repo standalone.
- Prefer explicit contracts and docs before infra sprawl.
- Keep the MVP deployable without a heavy multi-service platform.
