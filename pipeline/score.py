from __future__ import annotations

from functools import lru_cache
import re
from typing import Any


DIMENSION_LABELS = {
    "marketing_rule_relevance": "marketing-rule signal",
    "client_service_mix_change": "service-mix signal",
    "operational_complexity_change": "ops-complexity signal",
}
MARKETING_CONTEXT_WINDOW = 96
MARKETING_RULE_CONTEXT_RULES = {
    "advertisement": {
        "accept": (
            "testimonial",
            "endorsement",
            "promoter",
            "solicitor",
            "rating",
            "ratings",
            "review",
            "reviews",
            "compensated",
            "gross performance",
            "net performance",
        ),
        "reject": (
            "reimbursement for training",
            "travel expenses",
            "bonus programs",
            "gifts, meals",
            "marketing and/or override fee",
        ),
    },
    "advertising": {
        "accept": (
            "testimonial",
            "endorsement",
            "promoter",
            "solicitor",
            "rating",
            "ratings",
            "review",
            "reviews",
            "compensated",
            "gross performance",
            "net performance",
        ),
        "reject": (
            "reimbursement for training",
            "travel expenses",
            "bonus programs",
            "gifts, meals",
            "marketing and/or override fee",
        ),
    },
    "compensated": {
        "accept": ("testimonial", "endorsement", "promoter", "solicitor", "marketing", "advertising"),
        "reject": (),
    },
    "performance": {
        "accept": (
            "gross performance",
            "net performance",
            "performance results",
            "performance information",
            "performance data",
            "performance advertising",
            "advertised performance",
            "advertising",
            "advertisement",
            "testimonial",
            "endorsement",
        ),
        "reject": (
            "past performance",
            "future performance",
            "portfolio performance",
            "investment performance",
            "performance-based fee",
            "performance based fee",
        ),
    },
    "rating": {
        "accept": ("third-party", "third party", "client", "public", "testimonial", "endorsement", "review"),
        "reject": ("credit rating", "rating agency", "debt security", "bond rating", "security rating"),
    },
    "review": {
        "accept": (
            "client review",
            "client reviews",
            "online",
            "public",
            "google",
            "yelp",
            "third-party",
            "third party",
            "rating",
            "testimonial",
            "endorsement",
        ),
        "reject": (
            "review of accounts",
            "accounts are reviewed",
            "reviewed typically",
            "regular reviews",
            "review and discuss",
            "compare reports",
            "reviewed in the context",
            "more frequent reviews",
        ),
    },
    "third-party": {
        "accept": ("rating", "ratings", "testimonial", "endorsement", "promoter", "solicitor", "review", "reviews"),
        "reject": ("service provider", "service providers", "research service", "research services"),
    },
}
LOW_VALUE_SECTION_RULES = (
    {
        "rule_id": "custodian_platform_boilerplate",
        "patterns": (
            re.compile(r"\beducational conferences? and events?\b", re.IGNORECASE),
            re.compile(r"\beducational events?\b", re.IGNORECASE),
            re.compile(r"\bpractice management\b", re.IGNORECASE),
            re.compile(r"\bmarketing consulting and support\b", re.IGNORECASE),
            re.compile(r"\brecruiting and custodial search consulting\b", re.IGNORECASE),
            re.compile(r"\bplatform services include\b", re.IGNORECASE),
            re.compile(r"\badministrative support\b", re.IGNORECASE),
            re.compile(r"\bbusiness entertainment\b", re.IGNORECASE),
            re.compile(r"\bsporting events?\b", re.IGNORECASE),
            re.compile(r"\bgolf tournaments?\b", re.IGNORECASE),
            re.compile(r"\bback-?office training and support\b", re.IGNORECASE),
            re.compile(r"\brecord keeping\b", re.IGNORECASE),
            re.compile(r"\bresearch and brokerage services\b", re.IGNORECASE),
            re.compile(r"\bbusiness succession\b", re.IGNORECASE),
            re.compile(r"\bhuman capital consultants?\b", re.IGNORECASE),
            re.compile(r"\binsurance and marketing\b", re.IGNORECASE),
            re.compile(r"\bat no additional charge\b", re.IGNORECASE),
        ),
        "min_matches": 2,
        "penalties": {
            "client_service_mix_change": 1.5,
            "operational_complexity_change": 1.25,
        },
    },
    {
        "rule_id": "sponsor_incentive_boilerplate",
        "patterns": (
            re.compile(r"\bgifts, meals, or entertainment\b", re.IGNORECASE),
            re.compile(r"\bbonus programs\b", re.IGNORECASE),
            re.compile(r"\breimbursement for training\b", re.IGNORECASE),
            re.compile(r"\btravel expenses to conferences? or events\b", re.IGNORECASE),
            re.compile(r"\bthird parties or life insurance carriers\b", re.IGNORECASE),
            re.compile(r"\bmarketing and/?or override fee\b", re.IGNORECASE),
        ),
        "min_matches": 2,
        "penalties": {
            "marketing_rule_relevance": 1.75,
            "client_service_mix_change": 0.75,
        },
    },
    {
        "rule_id": "generic_investment_risk_boilerplate",
        "patterns": (
            re.compile(r"\binvestment strategies and risk of loss\b", re.IGNORECASE),
            re.compile(r"\bmethods of analysis\b", re.IGNORECASE),
            re.compile(r"\bfundamental analysis\b", re.IGNORECASE),
            re.compile(r"\blong-?term purchases\b", re.IGNORECASE),
            re.compile(r"\bstrategic asset allocation\b", re.IGNORECASE),
            re.compile(r"\bclients may suffer loss of all or part of (?:a )?principal investment\b", re.IGNORECASE),
            re.compile(r"\btemporary or extended bear markets\b", re.IGNORECASE),
        ),
        "reject_patterns": (
            re.compile(r"\bfinancial planning services?\b", re.IGNORECASE),
            re.compile(r"\bportfolio management\b", re.IGNORECASE),
            re.compile(r"\bretirement planning\b", re.IGNORECASE),
            re.compile(r"\bwritten financial plans?\b", re.IGNORECASE),
            re.compile(r"\bconsulting services?\b", re.IGNORECASE),
        ),
        "min_matches": 2,
        "penalties": {
            "client_service_mix_change": 1.5,
            "operational_complexity_change": 1.25,
        },
    },
    {
        "rule_id": "brokerage_support_boilerplate",
        "patterns": (
            re.compile(r"\bsoft dollar practices\b", re.IGNORECASE),
            re.compile(r"\bsection 28\(e\)\b", re.IGNORECASE),
            re.compile(r"\bbrokerage and research services\b", re.IGNORECASE),
            re.compile(r"\blowest commission rate available\b", re.IGNORECASE),
            re.compile(r"\bdirected brokerage\b", re.IGNORECASE),
            re.compile(r"\border aggregation\b", re.IGNORECASE),
            re.compile(r"\btrade error policy\b", re.IGNORECASE),
        ),
        "min_matches": 2,
        "penalties": {
            "client_service_mix_change": 1.25,
            "operational_complexity_change": 1.0,
        },
    },
    {
        "rule_id": "routine_account_review_boilerplate",
        "patterns": (
            re.compile(r"\bperiodic reviews?\b", re.IGNORECASE),
            re.compile(r"\bintermittent review factors\b", re.IGNORECASE),
            re.compile(r"\baccounts are reviewed\b", re.IGNORECASE),
            re.compile(r"\bconfirmations and statements\b", re.IGNORECASE),
            re.compile(r"\breports clients may receive\b", re.IGNORECASE),
            re.compile(r"\bfinancial planning accounts are reviewed\b", re.IGNORECASE),
        ),
        "min_matches": 2,
        "penalties": {
            "client_service_mix_change": 1.0,
            "operational_complexity_change": 0.75,
        },
    },
)
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
    "discretionary",
    "non-discretionary",
    "fee",
    "fees",
    "firm",
    "firms",
    "individual",
    "individuals",
    "management",
    "performance",
    "review",
    "reviews",
    "service",
    "services",
    "third-party",
    "wealth",
}
HEADING_PREFIX_PATTERN = re.compile(r"^(?:[A-Z]\.|[IVX]+\.)\s+")
ITEM_PREFIX_PATTERN = re.compile(r"^item\s+\d+[a-z]?\s*[:.-]?\s*", re.IGNORECASE)
NUMERIC_TOKEN_PATTERN = re.compile(r"\b\$?\d[\d,]*(?:\.\d+)?%?\b")
TABLE_SIGNAL_PATTERN = re.compile(
    r"\b(?:annual fees|assets under management|date calculated|fee schedule|discretionary amounts|non-?discretionary amounts|discretionary assets|non-?discretionary assets)\b",
    re.IGNORECASE,
)


def keyword_hits(text: str, keywords: list[str]) -> list[str]:
    return [keyword for keyword in keywords if keyword_pattern(keyword).search(text)]


def marketing_rule_keyword_hits(text: str, keywords: list[str]) -> list[str]:
    collapsed = collapsed_text(text)
    hits: list[str] = []
    for keyword in keywords:
        pattern = keyword_pattern(keyword)
        matches = list(pattern.finditer(collapsed))
        if not matches:
            continue
        if keyword in MARKETING_RULE_CONTEXT_RULES and not has_marketing_rule_context(collapsed, keyword, matches):
            continue
        hits.append(keyword)
    return hits


def collapsed_text(text: str) -> str:
    return " ".join(text.lower().split())


def low_value_section_penalties(text: str) -> dict[str, float]:
    collapsed = collapsed_text(text)
    penalties = {key: 0.0 for key in DIMENSION_LABELS}
    if not collapsed:
        return penalties

    for rule in LOW_VALUE_SECTION_RULES:
        match_count = sum(1 for pattern in rule["patterns"] if pattern.search(collapsed))
        if match_count < rule["min_matches"]:
            continue
        reject_patterns = rule.get("reject_patterns", ())
        if reject_patterns and any(pattern.search(collapsed) for pattern in reject_patterns):
            continue
        scale = min(1.6, 1.0 + 0.2 * (match_count - rule["min_matches"]))
        for dimension_key, penalty in rule["penalties"].items():
            penalties[dimension_key] = round(min(3.0, penalties[dimension_key] + (penalty * scale)), 2)
    return penalties


def low_value_excerpt_penalty(text: str) -> float:
    penalties = low_value_section_penalties(text)
    return round(sum(penalties.values()) * 0.25, 2)


def has_marketing_rule_context(text: str, keyword: str, matches: list[re.Match[str]]) -> bool:
    rule = MARKETING_RULE_CONTEXT_RULES[keyword]
    accept_terms = rule["accept"]
    reject_terms = rule["reject"]
    for match in matches:
        start = max(0, match.start() - MARKETING_CONTEXT_WINDOW)
        end = min(len(text), match.end() + MARKETING_CONTEXT_WINDOW)
        window = text[start:end]
        if any(term in window for term in reject_terms):
            continue
        if accept_terms and not any(term in window for term in accept_terms):
            continue
        return True
    return False


@lru_cache(maxsize=256)
def keyword_pattern(keyword: str) -> re.Pattern[str]:
    normalized = keyword.strip().lower()
    escaped = re.escape(normalized)
    escaped = escaped.replace(r"\ ", r"\s+")
    escaped = escaped.replace(r"\-", r"(?:-|\s+)")
    if re.fullmatch(r"[a-z]+", normalized) and not normalized.endswith("s"):
        escaped = f"{escaped}s?"
    return re.compile(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", re.IGNORECASE)


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


def normalized_alpha_tokens(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-z]+", text.lower()) if len(token) >= 4]


def focus_term_matches_firm_name(focus_term: str, firm_name: str) -> bool:
    focus_tokens = normalized_alpha_tokens(focus_term)
    firm_tokens = set(normalized_alpha_tokens(firm_name))
    if not focus_tokens or not firm_tokens:
        return False
    return all(token in firm_tokens for token in focus_tokens)


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
        or (len(alpha_words) >= 2 and title_case_ratio >= 0.75)
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


def stitch_fragmented_lines(text: str) -> str:
    lines = text.splitlines()
    stitched_lines: list[str] = []
    fragment_buffer: list[str] = []

    def flush_fragments() -> None:
        nonlocal fragment_buffer
        if fragment_buffer:
            stitched_lines.append(" ".join(fragment_buffer))
            fragment_buffer = []

    for raw_line in lines:
        cleaned = clean_line(raw_line)
        if not cleaned:
            continue
        words = cleaned.split()
        is_short_fragment = (
            len(words) <= 3
            and len(cleaned) <= 24
            and cleaned[-1] not in ".:;?!"
            and not HEADING_PREFIX_PATTERN.match(cleaned)
            and not ITEM_PREFIX_PATTERN.match(cleaned)
        )
        if is_short_fragment:
            fragment_buffer.append(cleaned)
            continue
        flush_fragments()
        stitched_lines.append(cleaned)

    flush_fragments()
    return "\n".join(stitched_lines)


def trim_table_like_tail(text: str) -> str:
    lines = [line for line in text.splitlines() if clean_line(line)]
    while len(lines) > 1 and table_like_penalty(lines[-1]) >= 1.0:
        lines.pop()
    return "\n".join(lines).strip()


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
    normalized_text = stitch_fragmented_lines(text)
    if not normalized_text.strip():
        return "", "", []

    chunks = subsection_chunks(normalized_text)
    if not chunks:
        snippet = preview(normalized_text, limit=limit)
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
        score -= low_value_excerpt_penalty(chunk)
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
        next_chunk = chunks[best_index + 1]
        candidate = f"{excerpt}\n{next_chunk}".strip()
        if len(candidate) <= limit + 40 and table_like_penalty(next_chunk) < 1.0:
            excerpt = candidate
    excerpt = trim_table_like_tail(excerpt)
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


def section_operator_value(section: dict[str, Any], firm_name: str) -> float:
    matched_keywords = section.get("matched_keywords", {})
    focus_term = section.get("evidence_focus_term", "").strip()
    source_text = section.get("current_text") or section.get("previous_text") or section.get("evidence_excerpt", "")

    specific_service_hits = [
        hit for hit in matched_keywords.get("client_service_mix_change", []) if is_specific_focus_term(hit)
    ]
    specific_ops_hits = [
        hit for hit in matched_keywords.get("operational_complexity_change", []) if is_specific_focus_term(hit)
    ]
    specific_marketing_hits = [
        hit for hit in matched_keywords.get("marketing_rule_relevance", []) if is_specific_focus_term(hit)
    ]

    operator_value = 0.0
    if specific_service_hits:
        operator_value += 2.0 + min(1.25, 0.45 * len(unique_terms(specific_service_hits)))
    elif specific_ops_hits:
        operator_value += 1.0 + min(0.75, 0.3 * len(unique_terms(specific_ops_hits)))
    elif specific_marketing_hits:
        operator_value += 0.75 + min(0.5, 0.25 * len(unique_terms(specific_marketing_hits)))

    if focus_term and not focus_term_matches_firm_name(focus_term, firm_name):
        if is_specific_focus_term(focus_term):
            operator_value += 1.25
            if " " in focus_term:
                operator_value += 0.5
        else:
            operator_value += 0.25

    rationale = section.get("score_rationale", "").strip()
    if rationale.startswith("SEC theme match:"):
        operator_value -= 1.25

    low_value_penalty = sum(low_value_section_penalties(source_text).values())
    if low_value_penalty:
        operator_value -= min(2.5, round(low_value_penalty * 0.5, 2))

    if table_like_penalty(section.get("evidence_excerpt", "")) >= 1.0:
        operator_value -= 1.25

    return round(operator_value, 2)


def section_evidence_priority(section: dict[str, Any], firm_name: str) -> tuple[float, float, float]:
    rationale = section.get("score_rationale", "").strip()
    focus_term = section.get("evidence_focus_term", "").strip()
    excerpt = section.get("evidence_excerpt", "")
    operator_value = section_operator_value(section, firm_name)

    explainability = 0.0
    if rationale:
        explainability += 2.0
    if focus_term:
        explainability += 1.0
        if is_specific_focus_term(focus_term):
            explainability += 1.5
        if focus_term_matches_firm_name(focus_term, firm_name):
            explainability -= 1.5
    if section.get("matched_themes"):
        explainability += 0.75
    if excerpt:
        explainability += 0.5 if table_like_penalty(excerpt) < 1.0 else -1.0
    if not rationale and not focus_term:
        explainability -= 3.0

    return operator_value, round(explainability, 2), float(section["scores"]["composite"])


def select_evidence_sections(scored_sections: list[dict[str, Any]], firm_name: str, *, limit: int = 3) -> list[dict[str, Any]]:
    if limit <= 0 or not scored_sections:
        return []
    if len(scored_sections) <= limit:
        return scored_sections[:limit]

    preserve_count = min(2, limit)
    selected = scored_sections[:preserve_count]
    remaining = sorted(
        scored_sections[preserve_count:],
        key=lambda section: section_evidence_priority(section, firm_name),
        reverse=True,
    )

    for section in remaining:
        if len(selected) >= limit:
            break
        selected.append(section)
    return selected[:limit]


def score_dimension(
    delta: dict[str, Any],
    *,
    search_text: str,
    keywords: list[str],
    preferred_sections: list[str],
    keyword_matcher=keyword_hits,
    penalty: float = 0.0,
) -> tuple[float, list[str]]:
    hits = keyword_matcher(search_text, keywords)
    hit_factor = min(1.0, len(hits) / 4)
    similarity_factor = min(1.0, max(0.0, 1.0 - float(delta["similarity"])) / 0.4)
    word_factor = min(1.0, abs(int(delta["word_delta"])) / 120)
    section_bonus = 0.15 if delta["section_key"] in preferred_sections else 0.0
    score = min(10.0, round(10 * (0.45 * hit_factor + 0.35 * similarity_factor + 0.2 * word_factor + section_bonus), 2))
    if penalty:
        score = round(max(0.0, score - penalty), 2)
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
        matcher = marketing_rule_keyword_hits if theme["theme_id"] == "marketing_rule_2025_12_16" else keyword_hits
        hits = matcher(search_text, theme["keywords"])
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
        search_text = " ".join(
            [
                str(delta.get("current_text", "")),
                " ".join(delta.get("added_terms", [])),
                " ".join(delta.get("removed_terms", [])),
            ]
        )
        low_value_penalties = low_value_section_penalties(search_text)
        marketing_score, marketing_hits = score_dimension(
            delta,
            search_text=search_text,
            keywords=dimensions["marketing_rule_relevance"]["keywords"],
            preferred_sections=dimensions["marketing_rule_relevance"]["preferred_sections"],
            keyword_matcher=marketing_rule_keyword_hits,
            penalty=low_value_penalties["marketing_rule_relevance"],
        )
        client_score, client_hits = score_dimension(
            delta,
            search_text=search_text,
            keywords=dimensions["client_service_mix_change"]["keywords"],
            preferred_sections=dimensions["client_service_mix_change"]["preferred_sections"],
            penalty=low_value_penalties["client_service_mix_change"],
        )
        ops_score, ops_hits = score_dimension(
            delta,
            search_text=search_text,
            keywords=dimensions["operational_complexity_change"]["keywords"],
            preferred_sections=dimensions["operational_complexity_change"]["preferred_sections"],
            penalty=low_value_penalties["operational_complexity_change"],
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

    evidence_sections = select_evidence_sections(scored_sections, firm_context["firm_name"], limit=3)
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
        for section in evidence_sections
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
