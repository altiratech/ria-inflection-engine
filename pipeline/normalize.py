from __future__ import annotations

from collections import Counter
from difflib import SequenceMatcher
import re


ITEM_HEADER_PATTERN = re.compile(
    r"(?im)^\s*(?:-\s*\d+\s*-\s*)?(?:item)\s+(\d+[a-z]?)\s*[-:.]?\s*([^\n]{3,120})$"
)
ITEM_FOUR_PATTERN = re.compile(r"(?im)^\s*(?:-\s*\d+\s*-\s*)?(?:item)\s+4\b")
TOKEN_PATTERN = re.compile(r"[a-z][a-z0-9/&-]{2,}")
DOT_LEADER_PATTERN = re.compile(r"\.{3,}\s*\d+\s*$")
INLINE_PAGE_MARKER_PATTERN = re.compile(r"^\s*-\s*\d+\s*-\s*")
LEADING_PAGE_NUMBER_PATTERN = re.compile(r"^\s*\d+\s+(?=[A-Za-z])")
STOPWORDS = {
    "a",
    "an",
    "and",
    "about",
    "adviser",
    "advisers",
    "advisory",
    "agreement",
    "are",
    "client",
    "clients",
    "each",
    "firm",
    "for",
    "forms",
    "from",
    "has",
    "have",
    "into",
    "investment",
    "is",
    "llc",
    "may",
    "not",
    "of",
    "on",
    "or",
    "our",
    "that",
    "the",
    "their",
    "there",
    "these",
    "this",
    "through",
    "to",
    "we",
    "were",
    "which",
    "who",
    "you",
    "your",
    "registered",
    "services",
    "will",
    "with",
}
DEFAULT_SECTION_TITLES = {
    "4": "Advisory Business",
    "5": "Fees and Compensation",
    "6": "Performance-Based Fees and Side-By-Side Management",
    "7": "Types of Clients",
    "8": "Methods of Analysis, Investment Strategies and Risk of Loss",
    "9": "Disciplinary Information",
    "10": "Other Financial Industry Activities and Affiliations",
    "11": "Code of Ethics, Participation or Interest in Client Transactions and Personal Trading",
    "12": "Brokerage Practices",
    "13": "Review of Accounts",
    "14": "Client Referrals and Other Compensation",
    "15": "Custody",
    "16": "Investment Discretion",
    "17": "Voting Client Securities",
    "18": "Financial Information",
}


def normalize_whitespace(text: str) -> str:
    cleaned = text.replace("\r", "\n")
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def canonicalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", normalize_whitespace(text)).strip()


def strip_table_of_contents_lines(text: str) -> str:
    cleaned_lines = []
    for line in text.splitlines():
        if DOT_LEADER_PATTERN.search(line.strip()):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def strip_table_of_contents_block(text: str) -> str:
    lowered = text.lower()
    toc_index = lowered.find("table of contents")
    if toc_index < 0:
        return text
    toc_line_start = text.rfind("\n", 0, toc_index)
    toc_line_start = 0 if toc_line_start < 0 else toc_line_start + 1
    item_four_matches = list(ITEM_FOUR_PATTERN.finditer(text))
    if len(item_four_matches) >= 2:
        return text[:toc_line_start].rstrip() + "\n\n" + text[item_four_matches[1].start() :].lstrip()
    return text.replace("Table of Contents", "").replace("TABLE OF CONTENTS", "")


def clean_section_title(section_number: str, raw_title: str) -> str:
    cleaned = normalize_whitespace(raw_title)
    if DOT_LEADER_PATTERN.search(cleaned):
        return DEFAULT_SECTION_TITLES.get(section_number, f"Item {section_number.upper()}")
    cleaned = DOT_LEADER_PATTERN.sub("", cleaned).strip(" -:.–—")
    if not cleaned or not re.search(r"[a-zA-Z]", cleaned) or cleaned.lower().endswith((" and", " or")):
        return DEFAULT_SECTION_TITLES.get(section_number, f"Item {section_number.upper()}")
    if len(cleaned.split()) > 10 or len(cleaned) > 80:
        return DEFAULT_SECTION_TITLES.get(section_number, f"Item {section_number.upper()}")
    return cleaned


def sanitize_section_body(text: str) -> str:
    cleaned_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if re.fullmatch(r"-\s*\d+\s*-", stripped) or re.fullmatch(r"\d+", stripped):
            continue
        line = INLINE_PAGE_MARKER_PATTERN.sub("", line)
        line = LEADING_PAGE_NUMBER_PATTERN.sub("", line)
        cleaned_lines.append(line)
    return normalize_whitespace("\n".join(cleaned_lines))


def sectionize_brochure(text: str) -> list[dict[str, str]]:
    normalized = normalize_whitespace(text)
    normalized = strip_table_of_contents_block(normalized)
    normalized = strip_table_of_contents_lines(normalized)
    matches = list(ITEM_HEADER_PATTERN.finditer(normalized))
    if not matches:
        return []

    sections_by_key: dict[str, dict[str, str]] = {}
    for index, match in enumerate(matches):
        section_number = match.group(1).lower()
        section_key = f"item_{section_number}"
        title = clean_section_title(section_number, match.group(2))
        body_start = match.end()
        body_end = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
        body = sanitize_section_body(normalized[body_start:body_end])
        if len(body) < 80:
            continue
        section = {
            "section_key": section_key,
            "section_number": section_number,
            "section_title": title,
            "text": body,
            "normalized_text": canonicalize_text(body),
        }
        existing = sections_by_key.get(section_key)
        if existing is None or len(section["text"]) > len(existing["text"]):
            sections_by_key[section_key] = section
    return list(sections_by_key.values())


def meaningful_terms(text: str, *, limit: int) -> list[str]:
    counter = Counter(term for term in TOKEN_PATTERN.findall(text.lower()) if term not in STOPWORDS)
    return [term for term, _ in counter.most_common(limit)]


def delta_terms(previous_text: str, current_text: str, *, limit: int) -> tuple[list[str], list[str]]:
    previous_counter = Counter(term for term in TOKEN_PATTERN.findall(previous_text.lower()) if term not in STOPWORDS)
    current_counter = Counter(term for term in TOKEN_PATTERN.findall(current_text.lower()) if term not in STOPWORDS)

    added = []
    removed = []
    for term, count in (current_counter - previous_counter).most_common(limit):
        if count > 0:
            added.append(term)
    for term, count in (previous_counter - current_counter).most_common(limit):
        if count > 0:
            removed.append(term)
    return added, removed


def summarize_change(change_type: str, added_terms: list[str], removed_terms: list[str]) -> str:
    parts = [change_type.replace("_", " ")]
    if added_terms:
        parts.append(f"added terms: {', '.join(added_terms)}")
    if removed_terms:
        parts.append(f"removed terms: {', '.join(removed_terms)}")
    return "; ".join(parts)


def build_section_deltas(
    previous_sections: list[dict[str, str]],
    current_sections: list[dict[str, str]],
    *,
    cosmetic_similarity_floor: float,
    minimum_word_delta: int,
    maximum_terms_per_excerpt: int,
) -> list[dict[str, object]]:
    previous_by_key = {section["section_key"]: section for section in previous_sections}
    current_by_key = {section["section_key"]: section for section in current_sections}
    deltas: list[dict[str, object]] = []

    for section_key in sorted(set(previous_by_key) | set(current_by_key)):
        previous_section = previous_by_key.get(section_key)
        current_section = current_by_key.get(section_key)
        previous_text = previous_section["normalized_text"] if previous_section else ""
        current_text = current_section["normalized_text"] if current_section else ""

        if previous_section and current_section:
            similarity = SequenceMatcher(None, previous_text, current_text).ratio()
            change_type = "unchanged" if similarity >= cosmetic_similarity_floor else "modified"
            title = current_section["section_title"]
        elif current_section:
            similarity = 0.0
            change_type = "added"
            title = current_section["section_title"]
        else:
            similarity = 0.0
            change_type = "removed"
            title = previous_section["section_title"]

        previous_word_count = len(previous_text.split())
        current_word_count = len(current_text.split())
        word_delta = current_word_count - previous_word_count
        added_terms, removed_terms = delta_terms(
            previous_text,
            current_text,
            limit=maximum_terms_per_excerpt,
        )
        is_material = (
            change_type != "unchanged"
            and (
                abs(word_delta) >= minimum_word_delta
                or similarity < cosmetic_similarity_floor
                or bool(added_terms)
                or bool(removed_terms)
            )
        )
        deltas.append(
            {
                "section_key": section_key,
                "section_title": title,
                "change_type": change_type,
                "similarity": round(similarity, 4),
                "previous_text": previous_section["text"] if previous_section else "",
                "current_text": current_section["text"] if current_section else "",
                "previous_word_count": previous_word_count,
                "current_word_count": current_word_count,
                "word_delta": word_delta,
                "added_terms": added_terms,
                "removed_terms": removed_terms,
                "is_material": is_material,
                "change_summary": summarize_change(change_type, added_terms, removed_terms),
            }
        )
    return deltas
