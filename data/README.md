# Data

Use this folder for durable local data layers.

Recommended subfolders:
- `raw/`
- `snapshots/`
- `staging/`
- `canonical/`

Rules:
- keep raw source pulls immutable
- timestamp snapshots
- preserve hashes and source metadata

First-slice conventions:
- `raw/sec/reports_metadata/` stores the IAPD FOIA metadata manifest
- `raw/sec/adv_filing_data/` stores the current/prior monthly filing ZIPs
- `raw/sec/brochures/` stores the exact brochure PDFs fetched from monthly archives
- `raw/adviserinfo/firm_detail/` stores firm-detail JSON from the live IAPD endpoint
- `canonical/first_slice/` stores the publishable shortlist and normalized delta payloads
