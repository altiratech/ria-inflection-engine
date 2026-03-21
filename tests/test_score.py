from __future__ import annotations

import json
from pathlib import Path

from pipeline.score import anchored_excerpt, score_firm_delta


REPO_ROOT = Path(__file__).resolve().parents[1]
RUBRIC = json.loads((REPO_ROOT / "configs" / "rubrics" / "first_slice_rubric_v1.json").read_text())
THEMES = json.loads((REPO_ROOT / "configs" / "themes" / "sec_regulatory_themes_v1.json").read_text())["themes"]


def test_score_firm_delta_emits_evidence_and_theme_links() -> None:
    firm_context = {
        "firm_id": "105849",
        "firm_name": "Saperston Legacy Advisors, Inc.",
        "state": "NY",
        "sec_number": "801-123456",
        "current_snapshot": {"submitted_at": "20260228", "file_name": "current.pdf"},
        "prior_snapshot": {"submitted_at": "20260130", "file_name": "prior.pdf"},
        "filing_context": {"raum_current": "125000000", "raum_prior": "119000000"},
    }
    section_deltas = [
        {
            "section_key": "item_5",
            "section_title": "Fees and Compensation",
            "change_type": "modified",
            "similarity": 0.61,
            "previous_text": "Clients pay an asset-based fee. The brochure did not discuss advertising, endorsements, or testimonials.",
            "current_text": "Clients pay an asset-based fee. The brochure now discusses testimonials, endorsements, and third-party ratings in advertising.",
            "previous_word_count": 14,
            "current_word_count": 18,
            "word_delta": 4,
            "added_terms": ["testimonial", "endorsement", "third-party", "advertising"],
            "removed_terms": [],
            "is_material": True,
            "change_summary": "modified; added terms: testimonial, endorsement, third-party, advertising",
        }
    ]

    scored = score_firm_delta(firm_context, section_deltas, RUBRIC, THEMES)

    assert scored["score"]["overall_score"] > 0
    assert scored["evidence"][0]["section_key"] == "item_5"
    assert scored["themes"][0]["theme_id"] == "marketing_rule_2025_12_16"
    assert "third-party ratings" in scored["evidence"][0]["current_excerpt"].lower()
    assert scored["evidence"][0]["focus_term"] in {"third-party", "rating", "testimonial", "advertising", "endorsement"}
    assert "marketing-rule signal" in scored["evidence"][0]["score_rationale"]


def test_anchored_excerpt_prefers_service_subsection_over_aum_table() -> None:
    text = """
Held Away Assets – Pontera
We may leverage the Pontera Order Management System to implement investment selection and rebalancing
strategies on behalf of clients for their held away accounts.

Financial Planning
Financial plans and financial planning may include retirement planning, insurance planning, education planning,
and charitable planning.

Retirement Plan Consulting
Our firm provides retirement plan consulting services to employer plan sponsors on an ongoing basis.

BLVD has the following assets under management:
Discretionary Amounts: Non-discretionary Amounts: Date Calculated:
$220,351,220.00 $0.00 December 2025

Portfolio Management and Held Away Assets – Pontera Fees
Total Assets Under Management Annual Fees
$0 - $1,000,000 1.00%
$1,000,001 - $5,000,000 0.90%
"""

    excerpt, focus_term, excerpt_hits = anchored_excerpt(
        text,
        ["consulting", "financial planning", "portfolio management"],
    )

    lowered = excerpt.lower()
    assert focus_term in {"consulting", "financial planning"}
    assert any(hit in {"consulting", "financial planning"} for hit in excerpt_hits)
    assert "retirement plan consulting" in lowered or "financial plans and financial planning" in lowered
    assert "annual fees" not in lowered
