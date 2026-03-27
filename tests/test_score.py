from __future__ import annotations

import json
from pathlib import Path

from pipeline.score import (
    anchored_excerpt,
    keyword_hits,
    low_value_section_penalties,
    marketing_rule_keyword_hits,
    select_evidence_sections,
    score_firm_delta,
)


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


def test_anchored_excerpt_avoids_word_split_aum_line_when_narrative_exists() -> None:
    text = """
Business

Description

Bell

City

Wealth

provides

financial planning and consulting services to individuals, retirement plan sponsors,
and trust clients.

Discretionary assets: $145,000,000
Non-discretionary assets: $0
"""

    excerpt, focus_term, excerpt_hits = anchored_excerpt(
        text,
        ["performance", "consulting", "retirement", "trust", "non-discretionary", "discretionary"],
    )

    lowered = excerpt.lower()
    assert focus_term in {"consulting", "retirement", "trust"}
    assert any(hit in {"consulting", "retirement", "trust"} for hit in excerpt_hits)
    assert "financial planning and consulting services" in lowered
    assert "non-discretionary assets" not in lowered


def test_keyword_hits_uses_phrase_boundaries_instead_of_substrings() -> None:
    text = "BCW began operating as a registered investment advisor in 2023."

    hits = keyword_hits(text, ["rating", "review", "registered investment advisor"])

    assert "rating" not in hits
    assert "review" not in hits
    assert "registered investment advisor" in hits


def test_marketing_rule_keyword_hits_require_marketing_context() -> None:
    innocuous_text = (
        "The lower the credit rating of a security, the greater the risk. "
        "We also rely on third-party service providers for cybersecurity support, conduct a review of accounts, "
        "and remind clients that past performance is not indicative of future returns."
    )
    signal_text = (
        "The brochure discusses client reviews, third-party ratings, compensated testimonials, "
        "and gross performance results used in advertising."
    )

    innocuous_hits = marketing_rule_keyword_hits(
        innocuous_text,
        ["rating", "third-party", "review", "compensated", "advertising", "performance"],
    )
    signal_hits = marketing_rule_keyword_hits(
        signal_text,
        ["rating", "third-party", "review", "compensated", "advertising", "performance"],
    )

    assert innocuous_hits == []
    assert signal_hits == ["rating", "third-party", "review", "compensated", "advertising", "performance"]


def test_marketing_rule_keyword_hits_ignore_generic_account_review_language() -> None:
    text = (
        "Accounts are reviewed typically each quarter in the context of each client's stated investment objectives. "
        "More frequent reviews may be triggered by material changes, and clients are urged to compare reports from custodians."
    )

    hits = marketing_rule_keyword_hits(text, ["review"])

    assert hits == []


def test_marketing_rule_keyword_hits_ignore_sponsor_reimbursement_boilerplate() -> None:
    text = (
        "The incentives likely include gifts, meals, or entertainment of reasonable value, participation in bonus programs, "
        "reimbursement for training, marketing, educational efforts, advertising, or travel expenses to conferences or events "
        "sponsored by third parties or life insurance carriers."
    )

    hits = marketing_rule_keyword_hits(text, ["advertising", "third-party"])

    assert hits == []


def test_low_value_section_penalties_flag_custodian_platform_boilerplate() -> None:
    text = (
        "Schwab also offers other services intended to help us manage and further develop our business enterprise. "
        "These services include educational conferences and events, publications and conferences on practice management, "
        "marketing consulting and support, and recruiting and custodial search consulting."
    )

    penalties = low_value_section_penalties(text)

    assert penalties["marketing_rule_relevance"] == 0.0
    assert penalties["client_service_mix_change"] > 0.0
    assert penalties["operational_complexity_change"] > 0.0


def test_low_value_section_penalties_flag_generic_risk_boilerplate() -> None:
    text = (
        "Investment Strategies and Risk of Loss. Methods of Analysis include fundamental analysis and long-term "
        "purchases. Clients may suffer loss of all or part of principal investment."
    )

    penalties = low_value_section_penalties(text)

    assert penalties["client_service_mix_change"] > 0.0
    assert penalties["operational_complexity_change"] > 0.0


def test_score_firm_delta_does_not_promote_rating_from_operating_fragment() -> None:
    firm_context = {
        "firm_id": "326354",
        "firm_name": "Bell City Wealth, Inc.",
        "state": "AL",
        "sec_number": "801-326354",
        "current_snapshot": {"submitted_at": "20260220", "file_name": "current.pdf"},
        "prior_snapshot": {"submitted_at": "20260115", "file_name": "prior.pdf"},
        "filing_context": {"raum_current": "145000000", "raum_prior": "0"},
    }
    section_deltas = [
        {
            "section_key": "item_4",
            "section_title": "Advisory",
            "change_type": "added",
            "similarity": 0.0,
            "previous_text": "",
            "current_text": (
                "Business\n\nFirm\n\nDescription\n\nBell\n\nCity\n\nWealth\n\n(\"BCW\") is an SEC-registered "
                "investment advisor. BCW began operating as a Registered Investment Advisor in 2023.\n\n"
                "Types of Advisory Services\n\nBCW provides financial planning and consulting services to "
                "individuals, retirement plan sponsors, and trust clients.\n\n"
                "Discretionary assets: $145,000,000\nNon-discretionary assets: $0\n"
            ),
            "previous_word_count": 0,
            "current_word_count": 39,
            "word_delta": 39,
            "added_terms": ["bell", "city", "wealth", "financial", "planning", "consulting", "retirement", "trust"],
            "removed_terms": [],
            "is_material": True,
            "change_summary": "added; added terms: bell, city, wealth, financial, planning, consulting, retirement, trust",
        }
    ]

    scored = score_firm_delta(firm_context, section_deltas, RUBRIC, THEMES)
    evidence = scored["evidence"][0]

    assert evidence["focus_term"] in {"consulting", "financial planning", "retirement", "trust"}
    assert "rating" not in evidence["score_rationale"].lower()
    assert "financial planning and consulting services" in evidence["current_excerpt"].lower()


def test_score_firm_delta_does_not_treat_credit_ratings_as_marketing_rule_signal() -> None:
    firm_context = {
        "firm_id": "317916",
        "firm_name": "25 Financial",
        "state": "TX",
        "sec_number": "801-317916",
        "current_snapshot": {"submitted_at": "20260227", "file_name": "current.pdf"},
        "prior_snapshot": {"submitted_at": "20260131", "file_name": "prior.pdf"},
        "filing_context": {"raum_current": "210000000", "raum_prior": "198000000"},
    }
    section_deltas = [
        {
            "section_key": "item_8",
            "section_title": "Methods",
            "change_type": "modified",
            "similarity": 0.73,
            "previous_text": "The firm discusses investment risks.",
            "current_text": (
                "Generally, the lower the credit rating of a security, the greater the risk that the issuer will default "
                "on its obligation. If a rating agency gives a debt security a lower rating, the value of the position may decline."
            ),
            "previous_word_count": 5,
            "current_word_count": 35,
            "word_delta": 30,
            "added_terms": ["credit", "rating", "security", "issuer", "debt"],
            "removed_terms": [],
            "is_material": True,
            "change_summary": "modified; added terms: credit, rating, security, issuer, debt",
        }
    ]

    scored = score_firm_delta(firm_context, section_deltas, RUBRIC, THEMES)
    evidence = scored["evidence"][0]

    assert evidence["focus_term"] != "rating"
    assert "marketing-rule signal" not in evidence["score_rationale"].lower()
    assert evidence["matched_themes"] == []


def test_score_firm_delta_does_not_treat_account_review_cycles_as_marketing_signal() -> None:
    firm_context = {
        "firm_id": "312325",
        "firm_name": "Edgerock Wealth Management",
        "state": "KS",
        "sec_number": "801-312325",
        "current_snapshot": {"submitted_at": "20260218", "file_name": "current.pdf"},
        "prior_snapshot": {"submitted_at": "20260121", "file_name": "prior.pdf"},
        "filing_context": {"raum_current": "315000000", "raum_prior": "302000000"},
    }
    section_deltas = [
        {
            "section_key": "item_13",
            "section_title": "Review of Accounts",
            "change_type": "modified",
            "similarity": 0.58,
            "previous_text": "Accounts were reviewed periodically.",
            "current_text": (
                "Accounts are reviewed typically each quarter in the context of each client's stated investment objectives "
                "and guidelines. More frequent reviews may be triggered by material changes, and clients are urged to compare "
                "reports from custodians."
            ),
            "previous_word_count": 5,
            "current_word_count": 31,
            "word_delta": 26,
            "added_terms": ["quarter", "objectives", "guidelines", "custodians"],
            "removed_terms": [],
            "is_material": True,
            "change_summary": "modified; expanded account review cadence disclosure",
        }
    ]

    scored = score_firm_delta(firm_context, section_deltas, RUBRIC, THEMES)
    section = scored["section_deltas"][0]

    assert section["matched_keywords"]["marketing_rule_relevance"] == []
    assert "marketing-rule signal" not in section["score_rationale"].lower()


def test_score_firm_delta_prefers_service_change_over_risk_and_support_boilerplate() -> None:
    firm_context = {
        "firm_id": "326354",
        "firm_name": "Bell City Wealth, Inc.",
        "state": "AL",
        "sec_number": "801-326354",
        "current_snapshot": {"submitted_at": "20260220", "file_name": "current.pdf"},
        "prior_snapshot": {"submitted_at": "20260115", "file_name": "prior.pdf"},
        "filing_context": {"raum_current": "145000000", "raum_prior": "0"},
    }
    section_deltas = [
        {
            "section_key": "item_4",
            "section_title": "Advisory",
            "change_type": "added",
            "similarity": 0.0,
            "previous_text": "",
            "current_text": (
                "Types of Advisory Services\n"
                "BCW offers portfolio management, investment analysis, financial planning, retirement planning, "
                "and estate planning for individuals and high net worth families."
            ),
            "previous_word_count": 0,
            "current_word_count": 23,
            "word_delta": 23,
            "added_terms": ["portfolio management", "financial planning", "retirement", "high net worth"],
            "removed_terms": [],
            "is_material": True,
            "change_summary": "added advisory services for portfolio management and planning",
        },
        {
            "section_key": "item_8",
            "section_title": "Methods",
            "change_type": "modified",
            "similarity": 0.42,
            "previous_text": "The firm discusses investment risks.",
            "current_text": (
                "Investment Strategies and Risk of Loss. Methods of Analysis include fundamental analysis, long-term "
                "purchases, and strategic asset allocation. Clients may suffer loss of all or part of principal investment."
            ),
            "previous_word_count": 5,
            "current_word_count": 28,
            "word_delta": 23,
            "added_terms": ["analysis", "strategies", "risk", "clients"],
            "removed_terms": [],
            "is_material": True,
            "change_summary": "expanded generic methods and risk disclosure",
        },
        {
            "section_key": "item_12",
            "section_title": "Brokerage Practices",
            "change_type": "modified",
            "similarity": 0.51,
            "previous_text": "The firm describes brokerage relationships.",
            "current_text": (
                "Soft dollar practices are arrangements where an investment adviser directs transactions to a broker-dealer "
                "for brokerage and research services. Section 28(e) provides a safe harbor when paying more than the lowest "
                "commission rate available. The brochure also discusses directed brokerage, order aggregation, and trade error policy."
            ),
            "previous_word_count": 6,
            "current_word_count": 46,
            "word_delta": 40,
            "added_terms": ["brokerage", "research", "commission", "client"],
            "removed_terms": [],
            "is_material": True,
            "change_summary": "expanded brokerage support disclosure",
        },
        {
            "section_key": "item_13",
            "section_title": "Review of Accounts",
            "change_type": "modified",
            "similarity": 0.48,
            "previous_text": "Accounts were reviewed periodically.",
            "current_text": (
                "Periodic Reviews are conducted at least annually. Intermittent review factors include market changes "
                "or client life events. Reports clients may receive include confirmations and statements, and financial "
                "planning accounts are reviewed upon plan delivery."
            ),
            "previous_word_count": 4,
            "current_word_count": 36,
            "word_delta": 32,
            "added_terms": ["reviews", "clients", "financial planning", "reports"],
            "removed_terms": [],
            "is_material": True,
            "change_summary": "expanded routine account review disclosure",
        },
    ]

    scored = score_firm_delta(firm_context, section_deltas, RUBRIC, THEMES)
    section_scores = {section["section_key"]: section["scores"]["composite"] for section in scored["section_deltas"]}

    assert scored["evidence"][0]["section_key"] == "item_4"
    assert section_scores["item_4"] > section_scores["item_8"]
    assert section_scores["item_4"] > section_scores["item_12"]
    assert section_scores["item_4"] > section_scores["item_13"]


def test_score_firm_delta_prefers_retirement_plan_consulting_over_platform_support_boilerplate() -> None:
    firm_context = {
        "firm_id": "310682",
        "firm_name": "BLVD Private Wealth, LLC",
        "state": "TX",
        "sec_number": "801-310682",
        "current_snapshot": {"submitted_at": "20260226", "file_name": "current.pdf"},
        "prior_snapshot": {"submitted_at": "20260129", "file_name": "prior.pdf"},
        "filing_context": {"raum_current": "220351220", "raum_prior": "207441113"},
    }
    section_deltas = [
        {
            "section_key": "item_14",
            "section_title": "Economic Benefits",
            "change_type": "modified",
            "similarity": 0.39,
            "previous_text": "The firm described third-party benefits.",
            "current_text": (
                "Schwab makes available educational events, business entertainment, sporting events, golf tournaments, "
                "back-office training and support, record keeping, and services to help BLVD manage and further develop its "
                "business enterprise. These services include compliance, legal and business consulting, business succession, "
                "human capital consultants, insurance and marketing support."
            ),
            "previous_word_count": 6,
            "current_word_count": 52,
            "word_delta": 46,
            "added_terms": ["consulting", "compliance", "vendor", "clients"],
            "removed_terms": [],
            "is_material": True,
            "change_summary": "expanded Schwab support disclosure",
        },
        {
            "section_key": "item_5",
            "section_title": "Fees",
            "change_type": "modified",
            "similarity": 0.33,
            "previous_text": "The firm listed advisory fees.",
            "current_text": (
                "Financial Planning Fees are negotiated based on complexity. Retirement Plan Consulting services are billed "
                "based on plan assets, and portfolio management fees may be billed directly or through the client's account."
            ),
            "previous_word_count": 5,
            "current_word_count": 30,
            "word_delta": 25,
            "added_terms": ["financial planning", "retirement", "consulting", "portfolio management", "billing"],
            "removed_terms": [],
            "is_material": True,
            "change_summary": "expanded retirement plan consulting and billing disclosure",
        },
    ]

    scored = score_firm_delta(firm_context, section_deltas, RUBRIC, THEMES)
    section_scores = {section["section_key"]: section["scores"]["composite"] for section in scored["section_deltas"]}

    assert scored["evidence"][0]["section_key"] == "item_5"
    assert section_scores["item_5"] > section_scores["item_14"]


def test_select_evidence_sections_prefers_explainable_third_slot_over_empty_fee_table() -> None:
    scored_sections = [
        {
            "section_key": "item_2",
            "scores": {"composite": 7.97},
            "evidence_focus_term": "financial planning",
            "score_rationale": "service-mix signal: financial planning, consulting",
            "matched_themes": [{"theme_name": "theme"}],
            "evidence_excerpt": "Financial planning services include retirement planning and portfolio management.",
        },
        {
            "section_key": "item_15",
            "scores": {"composite": 7.34},
            "evidence_focus_term": "custody",
            "score_rationale": "ops-complexity signal: custody",
            "matched_themes": [],
            "evidence_excerpt": "The firm is deemed to have limited custody of client funds.",
        },
        {
            "section_key": "item_5",
            "scores": {"composite": 6.47},
            "evidence_focus_term": "",
            "score_rationale": "",
            "matched_themes": [],
            "evidence_excerpt": (
                "Fee schedule. Less than $500,000 1.50%. $500,000 to $999,999 1.35%. "
                "$1,000,000 to $2,999,999 1.20%."
            ),
        },
        {
            "section_key": "item_13",
            "scores": {"composite": 6.08},
            "evidence_focus_term": "edgerock",
            "score_rationale": "service-mix signal: advisory, client, clients",
            "matched_themes": [],
            "evidence_excerpt": "EdgeRock has an arrangement with Fidelity that provides platform services and research support.",
        },
        {
            "section_key": "item_3",
            "scores": {"composite": 5.84},
            "evidence_focus_term": "retirement",
            "score_rationale": "service-mix signal: retirement",
            "matched_themes": [],
            "evidence_excerpt": "Retirement planning, insurance planning, and education planning are included in the written plan.",
        },
    ]

    selected = select_evidence_sections(scored_sections, "EDGEROCK WEALTH MANAGEMENT", limit=3)

    assert [section["section_key"] for section in selected] == ["item_2", "item_15", "item_3"]
