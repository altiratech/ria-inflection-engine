from __future__ import annotations

import json
from pathlib import Path

from pipeline.normalize import build_section_deltas, sectionize_brochure
from pipeline.remote_zip import ZipMember
from pipeline.run_first_slice import load_brochure_text, shortlist_row
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


def test_load_brochure_text_prefers_snapshot_cache(tmp_path, monkeypatch) -> None:
    snapshot_path = tmp_path / "brochure.txt"
    snapshot_path.write_text("cached snapshot text")
    seen = {}

    def fake_ensure_text_snapshot(member, pdf_path, seen_snapshot_path, *, user_agent: str, allow_download: bool):
        seen["member"] = member.file_name
        seen["pdf_path"] = pdf_path
        seen["snapshot_path"] = seen_snapshot_path
        seen["user_agent"] = user_agent
        seen["allow_download"] = allow_download
        assert seen_snapshot_path.exists()
        return False

    monkeypatch.setattr("pipeline.run_first_slice.ensure_text_snapshot", fake_ensure_text_snapshot)

    member = ZipMember(
        archive_url="https://example.com/archive.zip",
        file_name="123456_1_1_20260228.pdf",
        compressed_size=10,
        uncompressed_size=10,
        compression_method=0,
        crc32=0,
        local_header_offset=0,
    )

    text = load_brochure_text(member, tmp_path / "brochure.pdf", snapshot_path, user_agent="test-agent")

    assert text == "cached snapshot text"
    assert seen["member"] == "123456_1_1_20260228.pdf"
    assert seen["snapshot_path"] == snapshot_path
    assert seen["user_agent"] == "test-agent"
    assert seen["allow_download"] is True
