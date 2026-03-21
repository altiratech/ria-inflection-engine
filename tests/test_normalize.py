from __future__ import annotations

from pipeline.normalize import build_section_deltas, sectionize_brochure


PREVIOUS_TEXT = """
ITEM 4 Advisory Business
We provide investment management and financial planning services for individuals and retirement plans.
Our advisory team focuses on long-term allocation, retirement readiness, and household balance sheet planning.

ITEM 5 Fees and Compensation
Clients pay an asset-based fee billed quarterly in arrears. We do not receive compensation for testimonials or endorsements.

ITEM 8 Methods of Analysis, Investment Strategies and Risk of Loss
We primarily allocate client assets across diversified exchange-traded funds and mutual funds.
"""


CURRENT_TEXT = """
ITEM 4 Advisory Business
We provide investment management, financial planning, and outsourced chief investment officer services for individuals,
family offices, retirement plans, and business owners. Our advisory team added model portfolio reviews and consulting support
for held-away accounts as part of our expanded service mix.

ITEM 5 Fees and Compensation
Clients pay an asset-based fee billed quarterly in arrears. We may feature client testimonials and third-party ratings in our advertising.

ITEM 8 Methods of Analysis, Investment Strategies and Risk of Loss
We primarily allocate client assets across diversified exchange-traded funds and mutual funds, and we added alternative income sleeves.
"""


PAGE_MARKER_TEXT = """
Item 3: Table of Contents
Item 4: Advisory Business .....................................................................................................5
Item 18: Financial Information ..........................................................................................17
- 5-  Item  4: Advisory  Business
We provide investment management and financial planning services for households, foundations,
and retirement plans. We also coordinate estate planning and tax planning discussions with outside professionals.
- 6- necessary coverage and reporting follow-up are included in our standard process.

Item 5: Fees and Compensation
Clients pay an asset-based advisory fee billed quarterly in arrears. We may waive or negotiate fees in limited cases.

Item 18: Financial Information
Balance Sheet
A balance sheet is not required because we do not custody client assets or require prepaid fees of more than $1,200 six months in advance.
Financial Conditions Reasonably Likely to Impair Advisory Firm's Ability to Meet Commitments to Clients
20 We have no condition reasonably likely to impair our ability to meet contractual commitments to clients.
"""


UNICODE_DASH_TITLE_TEXT = """
Item 8 – Methods of Analysis, Investment Strategies and Risk of Loss
We primarily rely on fundamental analysis, third-party research, and periodic allocation reviews.
These methods are paired with household-level planning assumptions and ongoing risk monitoring.
"""


def test_sectionize_brochure_extracts_item_sections() -> None:
    sections = sectionize_brochure(CURRENT_TEXT)

    assert [section["section_key"] for section in sections] == ["item_4", "item_5", "item_8"]
    assert sections[0]["section_title"] == "Advisory Business"


def test_build_section_deltas_marks_material_changes() -> None:
    previous_sections = sectionize_brochure(PREVIOUS_TEXT)
    current_sections = sectionize_brochure(CURRENT_TEXT)
    deltas = build_section_deltas(
        previous_sections,
        current_sections,
        cosmetic_similarity_floor=0.985,
        minimum_word_delta=20,
        maximum_terms_per_excerpt=8,
    )

    advisory_delta = next(delta for delta in deltas if delta["section_key"] == "item_4")
    fee_delta = next(delta for delta in deltas if delta["section_key"] == "item_5")

    assert advisory_delta["is_material"] is True
    assert fee_delta["is_material"] is True
    assert "family" in advisory_delta["added_terms"]
    assert "third-party" in fee_delta["added_terms"]


def test_sectionize_brochure_handles_page_marker_item_headers() -> None:
    sections = sectionize_brochure(PAGE_MARKER_TEXT)

    assert [section["section_key"] for section in sections] == ["item_4", "item_5", "item_18"]
    financial_information = next(section for section in sections if section["section_key"] == "item_18")
    advisory_business = next(section for section in sections if section["section_key"] == "item_4")

    assert "Advisory Business" not in financial_information["text"]
    assert "coordinate estate planning" not in financial_information["text"]
    assert "- 6-" not in advisory_business["text"]
    assert "20 We have no condition" not in financial_information["text"]
    assert "balance sheet is not required" in financial_information["normalized_text"]


def test_sectionize_brochure_strips_unicode_dash_prefix_from_title() -> None:
    sections = sectionize_brochure(UNICODE_DASH_TITLE_TEXT)

    assert sections[0]["section_title"] == "Methods of Analysis, Investment Strategies and Risk of Loss"
