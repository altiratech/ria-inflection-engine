from __future__ import annotations

import re
from typing import Any


DIMENSION_LABELS = {
    "marketing_rule_relevance": "marketing-rule signal",
    "client_service_mix_change": "service-mix signal",
    "operational_complexity_change": "ops-complexity signal",
}
GENERIC_FOCUS_TERMS = {
    "account",
    "accounts",
    "adviser",
    "advisers",
    "advisory",
    "advisor",
    "advisors",
    "business",
    "client",
    "clients",
    "fee",
    "fees",
    "firm",
    "firms",
    "individual",
    "individuals",
    "management",
    "review",
    "reviews",
    "service",
    "services",
}
HEADING_PREFIX_PATTERN = re.compile(r"^(?:[A-Z]\.|[IVX]+\.)\s+")
ITEM_PREFIX_PATTERN = re.compile(r"^item\s+\d+[a-z]?\s*[:.-]?\s*", re.IGNORECASE)
NUMERIC_TOKEN_PATTERN = re.compile(r"\b\$?\d[\d,]*(?:\.\d+)?%?\b")
TABLE_SIGNAL_PATTERN = re.compile(
    r"\b(?:annual fees|assets under management|date calculated|fee schedule|discretionary amounts|non-?discretionary amounts)\b",
    re.IGNORECASE,
)


def keyword_hits(text: str, keywords: list[str]) -> list[str]:
    lowered = text.lower()
    return [keyword for keyword in keywords if keyword in lowered]


def preview(text: str, *, limit: int = 240) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return f"{collapsed[: limit - 3]}..."


def preview_around(text: str, anchor: str, *, limit: int = 240) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit or not anchor:
        return collapsed

    anchor_index = collapsed.lower().find(anchor.lower())
    if anchor_index < 0 or anchor_index <= limit // 4:
        return preview(collapsed, limit=limit)

    start = max(0, anchor_index - limit // 3)
    end = min(len(collapsed), start + limit)
    snippet = collapsed[start:end].strip()
    if start > 0:
        snippet = f"...{snippet}"
    if end < len(collapsed):
        snippet = f"{snippet}..."
    return snippet


def is_specific_focus_term(term: str) -> bool:
    normalized = term.strip().lower()
    if not normalized:
        return False
    if normalized in GENERIC_FOCUS_TERMS:
        return False
    if " " not in normalized and len(normalized) < 5:
        return False
    return True


def unique_terms(terms: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for term in terms:
        normalized = term.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(term.strip())
    return ordered


def clean_line(line: str) -> str:
    return " ".join(line.split()).strip()


def heading_probe(line: str) -> str:
    probe = ITEM_PREFIX_PATTERN.sub("", line.strip())
    probe = HEADING_PREFIX_PATTERN.sub("", probe)
    return probe.strip(":-–— ")


def is_heading_line(line: str) -> bool:
    cleaned = clean_line(line)
    if not cleaned:
        return False

    probe = heading_probe(cleaned)
    words = probe.split()
    if not words or len(words) > 12 or len(probe) > 100:
        return False
    if len(NUMERIC_TOKEN_PATTERN.findall(cleaned)) >= 2:
        return False
    if cleaned.endswith((".", "?", "!")) and not (
        HEADING_PREFIX_PATTERN.match(cleaned) or ITEM_PREFIX_PATTERN.match(cleaned)
    ):
        return False

    alpha_words = [word for word in words if re.search(r"[A-Za-z]", word)]
    if not alpha_words:
        return False
    title_case_ratio = sum(word[:1].isupper() for word in alpha_words) / len(alpha_words)
    return (
        bool(HEADING_PREFIX_PATTERN.match(cleaned))
        or bool(ITEM_PREFIX_PATTERN.match(cleaned))
        or " – " in cleaned
        or " - " in cleaned
        or title_case_ratio >= 0.75
    )


def subsection_chunks(text: str) -> list[str]:
    lines = [clean_line(line) for line in text.splitlines()]
    chunks: list[list[str]] = []
    current: list[str] = []

    for line in lines:
        if not line:
            if current:
                chunks.append(current)
                current = []
            continue
        if is_heading_line(line):
            if current:
                chunks.append(current)
            current = [line]
            continue
        if not current:
            current = [line]
        else:
            current.append(line)

    if current:
        chunks.append(current)

    merged: list[list[str]] = []
    index = 0
    while index < len(chunks):
        current_chunk = chunks[index]
        next_chunk = chunks[index + 1] if index + 1 < len(chunks) else None
        if (
            len(current_chunk) == 1
            and is_heading_line(current_chunk[0])
            and next_chunk is not None
            and not (len(next_chunk) == 1 and is_heading_line(next_chunk[0]))
        ):
            merged.append(current_chunk + next_chunk)
            index += 2
            continue
        merged.append(current_chunk)
        index += 1

    candidates: list[str] = []
    seen: set[str] = set()
    for chunk_lines in merged:
        candidate = "\n".join(chunk_lines).strip()
        if candidate and candidate not in seen:
            seen.add(candidate)
            candidates.append(candidate)
    return candidates


def table_like_penalty(text: str) -> float:
    lines = [clean_line(line) for line in text.splitlines() if clean_line(line)]
    if not lines:
        return 0.0

    numeric_line_count = sum(1 for line in lines if len(NUMERIC_TOKEN_PATTERN.findall(line)) >= 2)
    penalty = 0.0
    if numeric_line_count >= 2:
        penalty += 1.5 + min(1.5, 0.25 * (numeric_line_count - 2))
    if TABLE_SIGNAL_PATTERN.search(text):
        penalty += 1.0
    if numeric_line_count / len(lines) >= 0.35:
        penalty += 0.75
    return penalty


def focus_terms_for_section(
    scores: dict[str, float],
    matched_keywords: dict[str, list[str]],
    matched_themes: list[dict[str, Any]],
    added_terms: list[str],
) -> list[str]:
    ranked: list[str] = []
    for dimension_key in sorted(DIMENSION_LABELS, key=lambda key: scores[key], reverse=True):
        hits = sorted(matched_keywords.get(dimension_key, []), key=lambda term: (" " not in term, -len(term)))
        ranked.extend(hits)
    for theme in matched_themes:
        ranked.extend(theme.get("keyword_hits", []))
    ranked.extend(added_terms)

    specific_terms = [term for term in unique_terms(ranked) if is_specific_focus_term(term)]
    if specific_terms:
        return specific_terms
    return unique_terms(ranked)


def anchored_excerpt(text: str, focus_terms: list[str], *, limit: int = 240) -> tuple[str, str, list[str]]:
    if not text.strip():
        return "", "", []

    chunks = subsection_chunks(text)
    if not chunks:
        snippet = preview(text, limit=limit)
        return snippet, "", []

    best_index = -1
    best_hits: list[str] = []
    best_score = -1.0

    for index, chunk in enumerate(chunks):
        collapsed = " ".join(chunk.split())
        lowered = collapsed.lower()
        hits = [term for term in focus_terms if term.lower() in lowered]
        if not hits:
            continue
        ordered_hits = unique_terms(hits)
        score = 0.0
        for term in ordered_hits:
            rank = focus_terms.index(term)
            rank_weight = max(0.25, (len(focus_terms) - rank) / max(1, len(focus_terms)))
            term_weight = 3.0 if " " in term else 1.0
            score += term_weight + rank_weight + min(len(term), 12) / 12
        if chunk.splitlines() and is_heading_line(chunk.splitlines()[0]):
            score += 0.4
        score -= table_like_penalty(chunk)
        score -= max(0.0, (len(collapsed) - 480) / 600)
        score += max(0.0, 0.25 - 0.03 * index)
        if score > best_score:
            best_score = score
            best_index = index
            best_hits = ordered_hits

    if best_index < 0:
        snippet = preview(text, limit=limit)
        return snippet, "", []

    excerpt = chunks[best_index]
    if len(" ".join(excerpt.split())) < 140 and best_index + 1 < len(chunks):
        candidate = f"{excerpt}\n{chunks[best_index + 1]}".strip()
        if len(candidate) <= limit + 40:
            excerpt = candidate
    excerpt = preview_around(excerpt, best_hits[0], limit=limit)
    return excerpt, best_hits[0], best_hits


def score_rationale(
    scores: dict[str, float],
    matched_keywords: dict[str, list[str]],
    matched_themes: list[dict[str, Any]],
) -> str:
    parts: list[str] = []
    dimension_order = sorted(
        DIMENSION_LABELS,
        key=lambda key: scores[key],
        reverse=True,
    )
    for dimension_key in dimension_order:
        hits = [term for term in matched_keywords.get(dimension_key, []) if is_specific_focus_term(term)]
        if not hits:
            hits = matched_keywords.get(dimension_key, [])
        if scores[dimension_key] < 6 or not hits:
            continue
        parts.append(f"{DIMENSION_LABELS[dimension_key]}: {', '.join(hits[:3])}")
        if len(parts) >= 2:
            break

    if matched_themes:
        theme_names = [theme["theme_name"] for theme in matched_themes[:2]]
        parts.append(f"SEC theme match: {', '.join(theme_names)}")

    rationale = "; ".join(parts)
    return preview(rationale, limit=220)


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
        matched_keywords = {
            "marketing_rule_relevance": marketing_hits,
            "client_service_mix_change": client_hits,
            "operational_complexity_change": ops_hits,
        }
        section_scores = {
            "marketing_rule_relevance": marketing_score,
            "client_service_mix_change": client_score,
            "operational_complexity_change": ops_score,
            "confidence": confidence,
            "composite": composite,
        }
        theme_matches = matched_themes(delta, themes)
        focus_terms = focus_terms_for_section(section_scores, matched_keywords, theme_matches, delta["added_terms"])
        excerpt, focus_term, excerpt_hits = anchored_excerpt(delta["current_text"] or delta["previous_text"], focus_terms)
        scored_sections.append(
            {
                **delta,
                "scores": section_scores,
                "matched_keywords": matched_keywords,
                "matched_themes": theme_matches,
                "focus_terms": focus_terms,
                "evidence_focus_term": focus_term,
                "evidence_focus_hits": excerpt_hits,
                "evidence_excerpt": excerpt,
                "score_rationale": score_rationale(section_scores, matched_keywords, theme_matches),
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
            "focus_term": section["evidence_focus_term"],
            "score_rationale": section["score_rationale"],
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
