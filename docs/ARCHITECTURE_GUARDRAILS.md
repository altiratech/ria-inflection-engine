# RIA Inflection Engine Architecture Guardrails

## Scope Guardrails

- Build the ranked filing-delta intelligence loop first.
- Keep the first user and workflow fixed.
- Keep supervisory triage, compliance intelligence, and hidden-signal discovery as the sole framing.
- Do not add merger, CRM, task-management, or policy-library layers before the core loop is working.

## Data Guardrails

- Core objects:
  - `firm`
  - `snapshot`
  - `section`
  - `firm_delta`
  - `score`
  - `evidence`
- Keep raw, normalized, observed, inferred, and peer-relative layers separate.
- Synthetic data is prohibited.
- No score without visible evidence.
- Do not imply the system predicts who the SEC will audit.
- If supervisory or exam language appears, it must be framed as closer-review relevance under current SEC themes, not enforcement prediction.

## Product Guardrails

- ranked review queue first
- evidence before explanation flourish
- table and diff views before ornamental overview screens
- preserve the canonical object: `firm_delta`
- preserve visible exam-theme mapping when it affects ranking
- do not collapse the output into a black-box risk score with no reasoning

## Repo Guardrails

- Keep repo standalone.
- Prefer explicit contracts and docs before infra sprawl.
- Keep the MVP deployable without a heavy multi-service platform.
- Do not let downstream compliance workflow ideas redefine the upstream intelligence kernel.
