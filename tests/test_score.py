from __future__ import annotations

import json
from pathlib import Path

from pipeline.score import score_firm_delta


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
