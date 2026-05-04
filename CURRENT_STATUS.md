# Current Status

Product: public-disclosure intelligence engine intended to feed Altira Trace.

Current state:
- The repo kernel stays intact: SEC/IAPD ingest, brochure snapshot pairing, section-level diffs, visible evidence scoring, and table-first local artifacts.
- The architecture decision is now separate repos, one product strategy: Trace is the customer-facing RIA compliance product; this repo is the source-backed data engine.
- The current executable slice still uses the original base score dimensions. The next material build step is adding a supervisory overlay and peer-relative context without replacing the existing kernel.

Working bias:
- Keep this repo focused on versioned intelligence artifacts that Trace can consume.
- Do not expand this repo into workflow, evidence management, or a second customer-facing app.
