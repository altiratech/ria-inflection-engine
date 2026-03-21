from __future__ import annotations

from typing import Any


def keyword_hits(text: str, keywords: list[str]) -> list[str]:
    lowered = text.lower()
    return [keyword for keyword in keywords if keyword in lowered]


def preview(text: str, *, limit: int = 240) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return f"{collapsed[: limit - 3]}..."


def score_dimension(
    delta: dict[str, Any],
    *,
    keywords: list[str],
    preferred_sections: list[str],
) -> tuple[float, list[str]]:
    search_text = " ".join(
        [
            str(delta.get("current_text", "")),
            " ".join(delta.get("added_terms", [])),
            " ".join(delta.get("removed_terms", [])),
        ]
    )
    hits = keyword_hits(search_text, keywords)
    hit_factor = min(1.0, len(hits) / 4)
    similarity_factor = min(1.0, max(0.0, 1.0 - float(delta["similarity"])) / 0.4)
    word_factor = min(1.0, abs(int(delta["word_delta"])) / 120)
    section_bonus = 0.15 if delta["section_key"] in preferred_sections else 0.0
    score = min(10.0, round(10 * (0.45 * hit_factor + 0.35 * similarity_factor + 0.2 * word_factor + section_bonus), 2))
    return score, hits


def score_confidence(delta: dict[str, Any]) -> float:
    score = 2.0
    if delta["previous_word_count"] > 80 and delta["current_word_count"] > 80:
        score += 2.5
    if delta["change_type"] == "modified":
        score += 2.0
    if delta["is_material"]:
        score += 2.0
    if abs(int(delta["word_delta"])) >= 20:
        score += 1.5
    return min(10.0, round(score, 2))


def matched_themes(delta: dict[str, Any], themes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    search_text = " ".join(
        [
            str(delta.get("current_text", "")),
            " ".join(delta.get("added_terms", [])),
            " ".join(delta.get("removed_terms", [])),
        ]
    )
    matches = []
    for theme in themes:
        hits = keyword_hits(search_text, theme["keywords"])
        if hits:
            matches.append(
                {
                    "theme_id": theme["theme_id"],
                    "theme_name": theme["name"],
                    "source_url": theme["source_url"],
                    "source_date": theme["source_date"],
                    "keyword_hits": hits,
                }
            )
    return matches


def score_firm_delta(
    firm_context: dict[str, Any],
    section_deltas: list[dict[str, Any]],
    rubric: dict[str, Any],
    themes: list[dict[str, Any]],
) -> dict[str, Any]:
    dimensions = rubric["dimensions"]
    scored_sections = []
    for delta in section_deltas:
        if not delta["is_material"]:
            continue
        marketing_score, marketing_hits = score_dimension(
            delta,
            keywords=dimensions["marketing_rule_relevance"]["keywords"],
            preferred_sections=dimensions["marketing_rule_relevance"]["preferred_sections"],
        )
        client_score, client_hits = score_dimension(
            delta,
            keywords=dimensions["client_service_mix_change"]["keywords"],
            preferred_sections=dimensions["client_service_mix_change"]["preferred_sections"],
        )
        ops_score, ops_hits = score_dimension(
            delta,
            keywords=dimensions["operational_complexity_change"]["keywords"],
            preferred_sections=dimensions["operational_complexity_change"]["preferred_sections"],
        )
        confidence = score_confidence(delta)
        composite = round(
            marketing_score * dimensions["marketing_rule_relevance"]["weight"]
            + client_score * dimensions["client_service_mix_change"]["weight"]
            + ops_score * dimensions["operational_complexity_change"]["weight"]
            + confidence * dimensions["confidence"]["weight"],
            2,
        )
        scored_sections.append(
            {
                **delta,
                "scores": {
                    "marketing_rule_relevance": marketing_score,
                    "client_service_mix_change": client_score,
                    "operational_complexity_change": ops_score,
                    "confidence": confidence,
                    "composite": composite,
                },
                "matched_keywords": {
                    "marketing_rule_relevance": marketing_hits,
                    "client_service_mix_change": client_hits,
                    "operational_complexity_change": ops_hits,
                },
                "matched_themes": matched_themes(delta, themes),
                "evidence_excerpt": preview(delta["current_text"] or delta["previous_text"]),
            }
        )

    scored_sections.sort(key=lambda item: item["scores"]["composite"], reverse=True)
    if not scored_sections:
        raise ValueError(f"No material section deltas available for firm {firm_context['firm_id']}.")

    aggregate = {
        "marketing_rule_relevance": round(max(item["scores"]["marketing_rule_relevance"] for item in scored_sections), 2),
        "client_service_mix_change": round(max(item["scores"]["client_service_mix_change"] for item in scored_sections), 2),
        "operational_complexity_change": round(max(item["scores"]["operational_complexity_change"] for item in scored_sections), 2),
        "confidence": round(sum(item["scores"]["confidence"] for item in scored_sections) / len(scored_sections), 2),
    }
    aggregate["overall_score"] = round(
        aggregate["marketing_rule_relevance"] * dimensions["marketing_rule_relevance"]["weight"]
        + aggregate["client_service_mix_change"] * dimensions["client_service_mix_change"]["weight"]
        + aggregate["operational_complexity_change"] * dimensions["operational_complexity_change"]["weight"]
        + aggregate["confidence"] * dimensions["confidence"]["weight"],
        2,
    )

    theme_lookup: dict[str, dict[str, Any]] = {}
    for section in scored_sections:
        for theme in section["matched_themes"]:
            theme_lookup[theme["theme_id"]] = theme

    evidence = [
        {
            "section_key": section["section_key"],
            "section_title": section["section_title"],
            "change_summary": section["change_summary"],
            "current_excerpt": section["evidence_excerpt"],
            "composite": section["scores"]["composite"],
            "matched_themes": [theme["theme_name"] for theme in section["matched_themes"]],
        }
        for section in scored_sections[:3]
    ]

    return {
        "firm_id": firm_context["firm_id"],
        "firm_name": firm_context["firm_name"],
        "state": firm_context.get("state", ""),
        "sec_number": firm_context.get("sec_number", ""),
        "current_snapshot": firm_context["current_snapshot"],
        "prior_snapshot": firm_context["prior_snapshot"],
        "filing_context": firm_context.get("filing_context", {}),
        "score": aggregate,
        "themes": list(theme_lookup.values()),
        "evidence": evidence,
        "section_deltas": scored_sections,
    }
