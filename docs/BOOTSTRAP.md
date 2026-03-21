# RIA Inflection Engine Bootstrap Contract

Status: locked for scaffold-phase kickoff

## Toolchain Decision

- Python work uses the shared fastlane environment at `/Users/ryanjameson/Desktop/Lifehub/.venv-fastlane`.
- JavaScript work uses `npm` only after real code lands in `apps/web` or `packages/shared`.
- Slice 1 is Python-first and local-only.
- Slice 1 does not require a database or deployment target.

## Start Rule

1. Start in `configs/`, `pipeline/`, and `artifacts/`.
2. Treat `apps/web` as deferred until one versioned payload exists.
3. Add `packages/shared` only when a contract is genuinely shared by pipeline and UI.

## First Executable Contract

Before any UI work, produce:
- source config for SEC and adviser inputs
- a starter raw cache layout under `data/`
- one normalized delta payload
- one scored artifact payload under `artifacts/`

## Explicit Defers

Do not start with:
- `npm install`
- auth
- background jobs
- a database
- deployment setup
