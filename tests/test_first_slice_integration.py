from __future__ import annotations

import json
from pathlib import Path

from pipeline.normalize import build_section_deltas, sectionize_brochure
from pipeline.run_first_slice import shortlist_row
from pipeline.score import score_firm_delta


REPO_ROOT = Path(__file__).resolve().parents[1]
RUBRIC = json.loads((REPO_ROOT / "configs" / "rubrics" / "first_slice_rubric_v1.json").read_text())
THEMES = json.loads((REPO_ROOT / "configs" / "themes" / "sec_regulatory_themes_v1.json").read_text())["themes"]


PREVIOUS_BROCHURE = """
ITEM 4 Advisory Business
We provide portfolio management and financial planning services for individuals and small retirement plans.
Our practice does not provide consulting services to family offices or institutional clients.

ITEM 5 Fees and Compensation
Clients pay an annual fee billed quarterly in arrears. We do not use testimonials in advertising.

ITEM 8 Methods of Analysis, Investment Strategies and Risk of Loss
We focus on diversified mutual funds and exchange-traded funds for client portfolios.
"""


CURRENT_BROCHURE = """
ITEM 4 Advisory Business
We provide portfolio management, financial planning, outsourced chief investment officer support, and consulting services
for individuals, family offices, retirement plans, and select institutional clients. We added held-away account oversight
and model portfolio reviews for business owner households.

ITEM 5 Fees and Compensation
Clients pay an annual fee billed quarterly in arrears. We may use testimonials, endorsements, and third-party ratings in advertising.

ITEM 8 Methods of Analysis, Investment Strategies and Risk of Loss
We focus on diversified mutual funds, exchange-traded funds, and alternative income sleeves for client portfolios.
"""


def test_text_to_shortlist_row_flow() -> None:
    previous_sections = sectionize_brochure(PREVIOUS_BROCHURE)
    current_sections = sectionize_brochure(CURRENT_BROCHURE)
    section_deltas = build_section_deltas(
        previous_sections,
        current_sections,
        cosmetic_similarity_floor=0.985,
        minimum_word_delta=20,
        maximum_terms_per_excerpt=8,
    )
    firm_context = {
        "firm_id": "131738",
        "firm_name": "Sierra Pacific Private Wealth, LLC",
        "state": "CA",
        "sec_number": "801-654321",
        "current_snapshot": {"submitted_at": "20260223", "file_name": "current.pdf"},
        "prior_snapshot": {"submitted_at": "20260128", "file_name": "prior.pdf"},
        "filing_context": {"raum_current": "210000000", "raum_prior": "198000000"},
    }

    scored = score_firm_delta(firm_context, section_deltas, RUBRIC, THEMES)
    row = shortlist_row(scored)

    assert row["firm_id"] == "131738"
    assert row["overall_score"] > 0
    assert row["top_section"] in {"Advisory Business", "Fees and Compensation"}
    assert row["top_rationale"]
    assert row["top_excerpt"]
