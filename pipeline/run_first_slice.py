from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from collections.abc import Callable
from pathlib import Path
import zipfile

from pipeline.brochures import brochure_type, ensure_text_snapshot, parse_brochure_member
from pipeline.iapd import ArchiveFile, download_file, fetch_firm_detail, fetch_json, select_latest_archives
from pipeline.normalize import build_section_deltas, sectionize_brochure
from pipeline.remote_zip import list_zip_members
from pipeline.score import DIMENSION_LABELS, score_firm_delta


REPO_ROOT = Path(__file__).resolve().parents[1]
COMPARISON_DIMENSION_LABELS = {
    **DIMENSION_LABELS,
    "confidence": "confidence",
}


def load_json_file(path: Path) -> dict:
    return json.loads(path.read_text())


def write_json(path: Path, payload: dict | list) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))
    return path


def brochure_member_cache_path(raw_root: Path, archive: ArchiveFile, firm_id: str, file_name: str) -> Path:
    return raw_root / "sec" / "brochures" / archive.year / archive.display_name.lower().replace(" ", "_") / firm_id / file_name


def text_snapshot_path(snapshot_root: Path, archive: ArchiveFile, firm_id: str, file_name: str) -> Path:
    return snapshot_root / "brochure_text" / archive.year / archive.display_name.lower().replace(" ", "_") / firm_id / f"{file_name}.txt"


def filing_zip_cache_path(raw_root: Path, archive: ArchiveFile) -> Path:
    return raw_root / "sec" / "adv_filing_data" / archive.year / archive.file_name


def archive_index_cache_path(raw_root: Path, archive: ArchiveFile) -> Path:
    return raw_root / "sec" / "brochure_indexes" / f"{archive.file_name}.json"


def firm_detail_cache_path(raw_root: Path, firm_id: str) -> Path:
    return raw_root / "adviserinfo" / "firm_detail" / f"{firm_id}.json"


def brochure_cache_is_available(pdf_path: Path, snapshot_path: Path) -> bool:
    return pdf_path.exists() or snapshot_path.exists()


def cache_status_for_pair(raw_root: Path, snapshot_root: Path, pair: dict) -> dict[str, bool]:
    firm_id = pair["firm_id"]
    current_pdf_path = brochure_member_cache_path(
        raw_root, pair["current_archive"], firm_id, pair["current_member"].member.file_name
    )
    prior_pdf_path = brochure_member_cache_path(
        raw_root, pair["prior_archive"], firm_id, pair["prior_member"].member.file_name
    )
    current_snapshot_path = text_snapshot_path(
        snapshot_root, pair["current_archive"], firm_id, pair["current_member"].member.file_name
    )
    prior_snapshot_path = text_snapshot_path(
        snapshot_root, pair["prior_archive"], firm_id, pair["prior_member"].member.file_name
    )
    return {
        "firm_detail_cached": firm_detail_cache_path(raw_root, firm_id).exists(),
        "current_brochure_pdf_cached": current_pdf_path.exists(),
        "prior_brochure_pdf_cached": prior_pdf_path.exists(),
        "current_text_snapshot_cached": current_snapshot_path.exists(),
        "prior_text_snapshot_cached": prior_snapshot_path.exists(),
        "current_brochure_cache_available": brochure_cache_is_available(current_pdf_path, current_snapshot_path),
        "prior_brochure_cache_available": brochure_cache_is_available(prior_pdf_path, prior_snapshot_path),
    }


def pair_has_complete_cache(cache_status: dict[str, bool]) -> bool:
    return (
        cache_status["firm_detail_cached"]
        and cache_status["current_brochure_cache_available"]
        and cache_status["prior_brochure_cache_available"]
    )


def cache_gap_reason(cache_status: dict[str, bool]) -> str | None:
    if not cache_status["firm_detail_cached"]:
        return "missing_firm_detail_cache"
    if not cache_status["current_brochure_cache_available"]:
        return "missing_current_brochure_cache"
    if not cache_status["prior_brochure_cache_available"]:
        return "missing_prior_brochure_cache"
    return None


def refresh_action_for_reason(skip_reason: str) -> str | None:
    action_map = {
        "missing_firm_detail_cache": "fetch_firm_detail",
        "missing_current_brochure_cache": "cache_current_brochure",
        "missing_prior_brochure_cache": "cache_prior_brochure",
    }
    return action_map.get(skip_reason)


def submitted_sort_key(entry: dict[str, object]) -> tuple[str, str]:
    return str(entry.get("current_submitted_at", "")), str(entry.get("firm_id", ""))


def next_refresh_targets(
    skipped_candidates: list[dict[str, object]],
    *,
    queue_limit_per_reason: int = 10,
) -> dict[str, object]:
    actionable_reasons = [
        "missing_firm_detail_cache",
        "missing_current_brochure_cache",
        "missing_prior_brochure_cache",
    ]
    grouped_targets: list[dict[str, object]] = []
    actionable_total = 0

    for reason in actionable_reasons:
        matching_entries = [entry for entry in skipped_candidates if entry["skip_reason"] == reason]
        if not matching_entries:
            continue
        actionable_total += len(matching_entries)
        matching_entries.sort(key=submitted_sort_key, reverse=True)
        grouped_targets.append(
            {
                "skip_reason": reason,
                "refresh_action": refresh_action_for_reason(reason),
                "candidate_count": len(matching_entries),
                "targets": [
                    {
                        "firm_id": entry["firm_id"],
                        "firm_name": entry.get("firm_name", ""),
                        "sec_number": entry.get("sec_number", ""),
                        "current_submitted_at": entry["current_submitted_at"],
                        "prior_submitted_at": entry["prior_submitted_at"],
                        "current_file_name": entry["current_file_name"],
                        "prior_file_name": entry["prior_file_name"],
                    }
                    for entry in matching_entries[:queue_limit_per_reason]
                ],
            }
        )

    return {
        "queue_limit_per_reason": queue_limit_per_reason,
        "actionable_gap_total": actionable_total,
        "groups": grouped_targets,
    }


def cache_report_entry(
    pair: dict,
    *,
    cache_status: dict[str, bool],
    skip_stage: str,
    skip_reason: str,
    detail: dict | None = None,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    basic_information = (detail or {}).get("basicInformation", {})
    return {
        "firm_id": pair["firm_id"],
        "firm_name": basic_information.get("firmName", ""),
        "sec_number": basic_information.get("iaSECNumber", ""),
        "current_submitted_at": pair["current_member"].submitted_at,
        "prior_submitted_at": pair["prior_member"].submitted_at,
        "current_file_name": pair["current_member"].member.file_name,
        "prior_file_name": pair["prior_member"].member.file_name,
        "skip_stage": skip_stage,
        "skip_reason": skip_reason,
        "cache_status": cache_status,
        **(extra or {}),
    }


def build_cache_report(
    *,
    source_version: str,
    cache_only: bool,
    prior_brochure_archive: ArchiveFile,
    latest_brochure_archive: ArchiveFile,
    candidate_pairs_total: int,
    selection_limit: int,
    shortlist_limit: int,
    selected_pairs_total: int,
    shortlisted_total: int,
    cache_complete_pairs_total: int,
    skipped_candidates: list[dict[str, object]],
    snapshot_backfill_summary: dict[str, object] | None = None,
) -> dict[str, object]:
    reason_counts = Counter(entry["skip_reason"] for entry in skipped_candidates)
    stage_counts = Counter(entry["skip_stage"] for entry in skipped_candidates)
    refresh_targets = next_refresh_targets(skipped_candidates)
    return {
        "version": source_version,
        "mode": "cache_only" if cache_only else "default",
        "brochure_archive_pair": [
            {"display_name": prior_brochure_archive.display_name, "year": prior_brochure_archive.year, "url": prior_brochure_archive.url},
            {"display_name": latest_brochure_archive.display_name, "year": latest_brochure_archive.year, "url": latest_brochure_archive.url},
        ],
        "summary": {
            "candidate_pairs_total": candidate_pairs_total,
            "selection_limit": selection_limit,
            "shortlist_limit": shortlist_limit,
            "cache_complete_pairs_total": cache_complete_pairs_total,
            "selected_pairs_total": selected_pairs_total,
            "shortlisted_total": shortlisted_total,
            "skipped_candidates_total": len(skipped_candidates),
            "skipped_by_reason": dict(reason_counts),
            "skipped_by_stage": dict(stage_counts),
        },
        "snapshot_backfill": snapshot_backfill_summary
        or {
            "scope": "selected_pairs_plus_deferred_comparison_candidates",
            "eligible_snapshot_tasks_total": 0,
            "snapshots_already_cached": 0,
            "snapshots_generated": 0,
        },
        "next_refresh_targets": refresh_targets,
        "skipped_candidates": skipped_candidates,
    }


def selection_window_entry(
    skipped_candidate: dict[str, object],
    *,
    raw_root: Path,
    deferred_rank: int,
    selection_limit: int,
) -> dict[str, object]:
    firm_id = str(skipped_candidate["firm_id"])
    detail_path = firm_detail_cache_path(raw_root, firm_id)
    detail_cache_available = detail_path.exists()
    basic_information: dict[str, object] = {}
    if detail_cache_available:
        basic_information = load_cached_firm_detail(detail_path).get("basicInformation", {})

    return {
        "selection_position": selection_limit + deferred_rank,
        "deferred_rank": deferred_rank,
        "firm_id": firm_id,
        "firm_name": basic_information.get("firmName", skipped_candidate.get("firm_name", "")),
        "sec_number": basic_information.get("iaSECNumber", skipped_candidate.get("sec_number", "")),
        "ia_scope": basic_information.get("iaScope", ""),
        "detail_cache_available": detail_cache_available,
        "current_submitted_at": skipped_candidate["current_submitted_at"],
        "prior_submitted_at": skipped_candidate["prior_submitted_at"],
        "current_file_name": skipped_candidate["current_file_name"],
        "prior_file_name": skipped_candidate["prior_file_name"],
        "cache_status": skipped_candidate["cache_status"],
        "diagnostic_note": f"Deferred because the current {selection_limit}-pair selection window filled before this pair was evaluated for scoring.",
    }


def build_selection_window_artifact(
    *,
    source_version: str,
    selection_limit: int,
    selected_pairs_total: int,
    shortlisted_total: int,
    raw_root: Path,
    skipped_candidates: list[dict[str, object]],
) -> dict[str, object]:
    deferred_candidates = [
        entry for entry in skipped_candidates if entry["skip_reason"] == "selection_window_limit"
    ]
    deferred_entries = [
        selection_window_entry(
            entry,
            raw_root=raw_root,
            deferred_rank=index,
            selection_limit=selection_limit,
        )
        for index, entry in enumerate(deferred_candidates, start=1)
    ]
    return {
        "version": source_version,
        "selection_limit": selection_limit,
        "selected_pairs_total": selected_pairs_total,
        "shortlisted_total": shortlisted_total,
        "deferred_candidates_total": len(deferred_entries),
        "deferred_candidates_with_detail_cache": sum(1 for entry in deferred_entries if entry["detail_cache_available"]),
        "deferred_candidates": deferred_entries,
    }


def load_cached_firm_detail(path: Path) -> dict[str, object]:
    payload = load_json_file(path)
    if "basicInformation" in payload:
        return payload
    hits = payload.get("hits", {}).get("hits", [])
    if not hits:
        return {}
    return json.loads(hits[0]["_source"]["iacontent"])


def selection_priority_tuple(pair: dict, cache_status: dict[str, bool]) -> tuple[int, int, int, int, str, str]:
    return (
        1 if pair_has_complete_cache(cache_status) else 0,
        1 if cache_status["firm_detail_cached"] else 0,
        1 if cache_status["current_brochure_cache_available"] else 0,
        1 if cache_status["prior_brochure_cache_available"] else 0,
        pair["current_member"].submitted_at,
        pair["firm_id"],
    )


def evaluate_pair(
    *,
    pair: dict,
    detail: dict,
    cache_status: dict[str, bool],
    raw_root: Path,
    snapshot_root: Path,
    source_config: dict,
    cache_only: bool,
    selection: dict,
    rubric: dict,
    themes_payload: dict,
    filing_context_current: dict[str, dict],
    filing_context_prior: dict[str, dict],
) -> tuple[dict[str, object] | None, dict[str, object] | None]:
    current_pdf_path = brochure_member_cache_path(
        raw_root, pair["current_archive"], pair["firm_id"], pair["current_member"].member.file_name
    )
    prior_pdf_path = brochure_member_cache_path(
        raw_root, pair["prior_archive"], pair["firm_id"], pair["prior_member"].member.file_name
    )
    current_snapshot_path = text_snapshot_path(
        snapshot_root, pair["current_archive"], pair["firm_id"], pair["current_member"].member.file_name
    )
    prior_snapshot_path = text_snapshot_path(
        snapshot_root, pair["prior_archive"], pair["firm_id"], pair["prior_member"].member.file_name
    )
    try:
        current_text = load_brochure_text(
            pair["current_member"].member,
            current_pdf_path,
            current_snapshot_path,
            user_agent=source_config["browser_headers"]["user_agent"],
            allow_download=not cache_only,
        )
    except FileNotFoundError:
        return None, {"skip_stage": "brochure", "skip_reason": "missing_current_brochure_cache"}
    try:
        prior_text = load_brochure_text(
            pair["prior_member"].member,
            prior_pdf_path,
            prior_snapshot_path,
            user_agent=source_config["browser_headers"]["user_agent"],
            allow_download=not cache_only,
        )
    except FileNotFoundError:
        return None, {"skip_stage": "brochure", "skip_reason": "missing_prior_brochure_cache"}

    current_brochure_type = brochure_type(current_text)
    prior_brochure_type = brochure_type(prior_text)
    if current_brochure_type != "part_2a" or prior_brochure_type != "part_2a":
        return None, {
            "skip_stage": "brochure",
            "skip_reason": "unsupported_brochure_type",
            "extra": {
                "current_brochure_type": current_brochure_type,
                "prior_brochure_type": prior_brochure_type,
            },
        }

    current_sections = sectionize_brochure(current_text)
    prior_sections = sectionize_brochure(prior_text)
    if len(current_sections) < selection["minimum_sections_per_snapshot"] or len(prior_sections) < selection["minimum_sections_per_snapshot"]:
        return None, {
            "skip_stage": "normalize",
            "skip_reason": "insufficient_sections",
            "extra": {
                "current_section_count": len(current_sections),
                "prior_section_count": len(prior_sections),
            },
        }

    current_row = filing_context_current.get(pair["firm_id"], {})
    prior_row = filing_context_prior.get(pair["firm_id"], {})
    context = firm_context(
        detail,
        pair["firm_id"],
        pair,
        filing_context={
            "filing_id_current": current_row.get("FilingID", ""),
            "filing_id_prior": prior_row.get("FilingID", ""),
            "raum_current": current_row.get("5F2c", ""),
            "raum_prior": prior_row.get("5F2c", ""),
            "state_current": current_row.get("1F1-State", ""),
            "state_prior": prior_row.get("1F1-State", ""),
        },
    )

    section_deltas = build_section_deltas(
        prior_sections,
        current_sections,
        cosmetic_similarity_floor=rubric["materiality"]["cosmetic_similarity_floor"],
        minimum_word_delta=rubric["materiality"]["minimum_word_delta"],
        maximum_terms_per_excerpt=rubric["materiality"]["maximum_terms_per_excerpt"],
    )
    try:
        scored_delta = score_firm_delta(context, section_deltas, rubric, themes_payload["themes"])
    except ValueError:
        return None, {"skip_stage": "score", "skip_reason": "no_scored_evidence"}
    return scored_delta, None


def score_gap_to_shortlist_floor(candidate_score: dict[str, float], floor_score: dict[str, float]) -> dict[str, float]:
    return {
        key: round(candidate_score[key] - floor_score[key], 2)
        for key in [
            "marketing_rule_relevance",
            "client_service_mix_change",
            "operational_complexity_change",
            "confidence",
            "overall_score",
        ]
    }


def comparison_summary(candidate_score: dict[str, float], floor_score: dict[str, float]) -> str:
    gaps = score_gap_to_shortlist_floor(candidate_score, floor_score)
    overall_gap = gaps["overall_score"]
    dimension_gaps = {
        key: value
        for key, value in gaps.items()
        if key not in {"overall_score"}
    }
    weakest_dimension = min(dimension_gaps, key=dimension_gaps.get)
    weakest_label = COMPARISON_DIMENSION_LABELS[weakest_dimension]
    if overall_gap >= 0:
        return f"Would clear the shortlist floor by {overall_gap:.2f}; deferred only because the evaluation window filled first."
    if overall_gap >= -0.5:
        return f"Trails the shortlist floor by {abs(overall_gap):.2f}, mostly on {weakest_label}."
    return f"Trails the shortlist floor by {abs(overall_gap):.2f}; the largest gap is {weakest_label}."


def comparison_unavailable_summary(skip_info: dict[str, object]) -> str:
    reason = str(skip_info["skip_reason"])
    if reason == "unsupported_brochure_type":
        return "Comparison unavailable because this pair still resolves to an unsupported brochure type."
    if reason == "no_scored_evidence":
        return "Comparison unavailable because the pair still produced no scored evidence after normalization."
    if reason == "insufficient_sections":
        return "Comparison unavailable because the brochure snapshots did not yield enough sections for scoring."
    if reason == "missing_current_brochure_cache":
        return "Comparison unavailable because the current brochure cache is still incomplete."
    if reason == "missing_prior_brochure_cache":
        return "Comparison unavailable because the prior brochure cache is still incomplete."
    return f"Comparison unavailable because this pair skipped at {skip_info['skip_stage']}."


def selection_window_comparison_entry(
    selection_entry: dict[str, object],
    *,
    shortlist_floor: dict[str, object],
    scored_delta: dict[str, object] | None = None,
    skip_info: dict[str, object] | None = None,
) -> dict[str, object]:
    base = {
        "selection_position": selection_entry["selection_position"],
        "deferred_rank": selection_entry["deferred_rank"],
        "firm_id": selection_entry["firm_id"],
        "firm_name": selection_entry["firm_name"],
        "sec_number": selection_entry["sec_number"],
        "ia_scope": selection_entry["ia_scope"],
        "detail_cache_available": selection_entry["detail_cache_available"],
        "current_submitted_at": selection_entry["current_submitted_at"],
        "prior_submitted_at": selection_entry["prior_submitted_at"],
        "cache_status": selection_entry["cache_status"],
    }
    if scored_delta is None:
        return {
            **base,
            "comparison_status": "not_scored",
            "comparison_skip_stage": skip_info["skip_stage"] if skip_info else "",
            "comparison_skip_reason": skip_info["skip_reason"] if skip_info else "",
            "comparison_summary": comparison_unavailable_summary(skip_info or {"skip_stage": "", "skip_reason": ""}),
        }

    floor_score = shortlist_floor["score"]
    candidate_score = scored_delta["score"]
    gaps = score_gap_to_shortlist_floor(candidate_score, floor_score)
    top_evidence = scored_delta["evidence"][0]
    return {
        **base,
        "comparison_status": "scored",
        "shadow_score": candidate_score,
        "score_gap_to_shortlist_floor": gaps["overall_score"],
        "dimension_gaps_to_shortlist_floor": gaps,
        "would_enter_shortlist": candidate_score["overall_score"] >= floor_score["overall_score"],
        "comparison_summary": comparison_summary(candidate_score, floor_score),
        "top_evidence": {
            "section_title": top_evidence["section_title"],
            "change_summary": top_evidence["change_summary"],
            "focus_term": top_evidence.get("focus_term", ""),
            "score_rationale": top_evidence.get("score_rationale", ""),
            "current_excerpt": top_evidence.get("current_excerpt", ""),
            "composite": top_evidence["composite"],
        },
    }


def build_selection_window_comparison_artifact(
    *,
    source_version: str,
    selection_limit: int,
    shortlist_limit: int,
    shortlist_floor: dict[str, object],
    comparisons: list[dict[str, object]],
) -> dict[str, object]:
    scored_candidates = [entry for entry in comparisons if entry["comparison_status"] == "scored"]
    scored_candidates.sort(key=lambda entry: entry["shadow_score"]["overall_score"], reverse=True)
    unscored_candidates = [entry for entry in comparisons if entry["comparison_status"] != "scored"]
    ordered = scored_candidates + unscored_candidates
    for rank, entry in enumerate(ordered, start=1):
        entry["comparison_rank"] = rank

    return {
        "version": source_version,
        "selection_limit": selection_limit,
        "shortlist_limit": shortlist_limit,
        "shortlist_floor": {
            "firm_id": shortlist_floor["firm_id"],
            "firm_name": shortlist_floor["firm_name"],
            "score": shortlist_floor["score"],
        },
        "deferred_candidates_total": len(comparisons),
        "scored_candidates_total": len(scored_candidates),
        "would_enter_shortlist_total": sum(1 for entry in scored_candidates if entry["would_enter_shortlist"]),
        "comparisons": ordered,
    }


def merge_shortlist_with_promotions(
    shortlisted: list[dict[str, object]],
    promoted_candidates: list[dict[str, object]],
    *,
    shortlist_limit: int,
) -> tuple[list[dict[str, object]], set[str], set[str]]:
    merged_by_firm = {item["firm_id"]: item for item in shortlisted}
    original_ids = set(merged_by_firm)
    for candidate in promoted_candidates:
        merged_by_firm[candidate["firm_id"]] = candidate

    merged = sorted(
        merged_by_firm.values(),
        key=lambda item: item["score"]["overall_score"],
        reverse=True,
    )
    final_shortlist = merged[:shortlist_limit]
    final_ids = {item["firm_id"] for item in final_shortlist}
    promoted_ids = final_ids - original_ids
    displaced_ids = original_ids - final_ids
    return final_shortlist, promoted_ids, displaced_ids


def filing_rows(zip_path: Path, *, firm_ids: set[str]) -> dict[str, dict]:
    rows_by_firm: dict[str, dict] = {}
    with zipfile.ZipFile(zip_path) as archive:
        member_name = next(name for name in archive.namelist() if name.startswith("IA_ADV_Base_A_"))
        with archive.open(member_name) as handle:
            reader = csv.DictReader((line.decode("utf-8-sig") for line in handle))
            for row in reader:
                firm_id = (row.get("1E1") or "").strip()
                if firm_id in firm_ids:
                    rows_by_firm[firm_id] = row
    return rows_by_firm


def candidate_pairs(current_archive: ArchiveFile, prior_archive: ArchiveFile, current_members, prior_members, require_single: bool) -> list[dict]:
    current_by_firm = {}
    prior_by_firm = {}

    for member in current_members:
        brochure_member = parse_brochure_member(member)
        if brochure_member is None:
            continue
        current_by_firm.setdefault(brochure_member.firm_id, []).append(brochure_member)

    for member in prior_members:
        brochure_member = parse_brochure_member(member)
        if brochure_member is None:
            continue
        prior_by_firm.setdefault(brochure_member.firm_id, []).append(brochure_member)

    overlap = sorted(set(current_by_firm) & set(prior_by_firm))
    pairs = []
    for firm_id in overlap:
        current_entries = sorted(current_by_firm[firm_id], key=lambda item: (item.submitted_at, item.sequence), reverse=True)
        prior_entries = sorted(prior_by_firm[firm_id], key=lambda item: (item.submitted_at, item.sequence), reverse=True)
        if require_single and (len(current_entries) != 1 or len(prior_entries) != 1):
            continue
        pairs.append(
            {
                "firm_id": firm_id,
                "current_member": current_entries[0],
                "prior_member": prior_entries[0],
                "current_archive": current_archive,
                "prior_archive": prior_archive,
            }
        )
    pairs.sort(key=lambda item: (item["current_member"].submitted_at, item["firm_id"]), reverse=True)
    return pairs


def firm_context(detail: dict, firm_id: str, pair: dict, filing_context: dict) -> dict:
    address = detail.get("firmAddressDetails", {}).get("officeAddress", {})
    basic_information = detail.get("basicInformation", {})
    return {
        "firm_id": firm_id,
        "firm_name": basic_information.get("firmName", ""),
        "state": address.get("state", "") or filing_context.get("state_current", ""),
        "sec_number": basic_information.get("iaSECNumber", ""),
        "current_snapshot": {
            "archive_month": pair["current_archive"].display_name,
            "archive_year": pair["current_archive"].year,
            "submitted_at": pair["current_member"].submitted_at,
            "version_id": pair["current_member"].version_id,
            "file_name": pair["current_member"].member.file_name,
        },
        "prior_snapshot": {
            "archive_month": pair["prior_archive"].display_name,
            "archive_year": pair["prior_archive"].year,
            "submitted_at": pair["prior_member"].submitted_at,
            "version_id": pair["prior_member"].version_id,
            "file_name": pair["prior_member"].member.file_name,
        },
        "filing_context": filing_context,
    }


def shortlist_row(delta_payload: dict) -> dict[str, object]:
    evidence = delta_payload["evidence"][0]
    filing_context = delta_payload.get("filing_context", {})
    return {
        "firm_id": delta_payload["firm_id"],
        "firm_name": delta_payload["firm_name"],
        "state": delta_payload.get("state", ""),
        "sec_number": delta_payload.get("sec_number", ""),
        "current_submitted_at": delta_payload["current_snapshot"]["submitted_at"],
        "prior_submitted_at": delta_payload["prior_snapshot"]["submitted_at"],
        "marketing_rule_relevance": delta_payload["score"]["marketing_rule_relevance"],
        "client_service_mix_change": delta_payload["score"]["client_service_mix_change"],
        "operational_complexity_change": delta_payload["score"]["operational_complexity_change"],
        "confidence": delta_payload["score"]["confidence"],
        "overall_score": delta_payload["score"]["overall_score"],
        "raum_current": filing_context.get("raum_current", ""),
        "raum_prior": filing_context.get("raum_prior", ""),
        "top_section": evidence["section_title"],
        "top_evidence": evidence["change_summary"],
        "top_focus_term": evidence.get("focus_term", ""),
        "top_rationale": evidence.get("score_rationale", ""),
        "top_excerpt": evidence.get("current_excerpt", ""),
    }


def write_shortlist_csv(path: Path, rows: list[dict[str, object]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return path


def brochure_snapshot_task(pair: dict, *, snapshot_kind: str, raw_root: Path, snapshot_root: Path) -> dict[str, object]:
    member_key = f"{snapshot_kind}_member"
    archive_key = f"{snapshot_kind}_archive"
    member = pair[member_key]
    archive = pair[archive_key]
    return {
        "firm_id": pair["firm_id"],
        "snapshot_kind": snapshot_kind,
        "submitted_at": member.submitted_at,
        "file_name": member.member.file_name,
        "member": member.member,
        "pdf_path": brochure_member_cache_path(raw_root, archive, pair["firm_id"], member.member.file_name),
        "snapshot_path": text_snapshot_path(snapshot_root, archive, pair["firm_id"], member.member.file_name),
    }


def build_snapshot_backfill_tasks(
    *,
    selected_pairs: list[tuple[dict, dict]],
    deferred_selection_entries: list[dict[str, object]],
    pair_lookup: dict[str, dict],
    cache_status_lookup: dict[str, dict[str, bool]],
    raw_root: Path,
    snapshot_root: Path,
) -> list[dict[str, object]]:
    tasks_by_snapshot: dict[str, dict[str, object]] = {}

    def register_pair(pair: dict) -> None:
        cache_status = cache_status_lookup[pair["firm_id"]]
        for snapshot_kind, cache_flag in (
            ("current", "current_brochure_cache_available"),
            ("prior", "prior_brochure_cache_available"),
        ):
            if not cache_status[cache_flag]:
                continue
            task = brochure_snapshot_task(
                pair,
                snapshot_kind=snapshot_kind,
                raw_root=raw_root,
                snapshot_root=snapshot_root,
            )
            tasks_by_snapshot[str(task["snapshot_path"])] = task

    for pair, _detail in selected_pairs:
        register_pair(pair)
    for selection_entry in deferred_selection_entries:
        register_pair(pair_lookup[str(selection_entry["firm_id"])])

    return sorted(
        tasks_by_snapshot.values(),
        key=lambda task: (
            str(task["firm_id"]),
            0 if str(task["snapshot_kind"]) == "current" else 1,
            str(task["submitted_at"]),
            str(task["file_name"]),
        ),
    )


def backfill_brochure_text_snapshots(
    tasks: list[dict[str, object]],
    *,
    user_agent: str,
    allow_download: bool,
    progress: Callable[[str], None] | None = None,
) -> dict[str, object]:
    summary = {
        "scope": "selected_pairs_plus_deferred_comparison_candidates",
        "eligible_snapshot_tasks_total": len(tasks),
        "snapshots_already_cached": 0,
        "snapshots_generated": 0,
    }
    if progress is not None:
        progress(
            "snapshot_backfill_queue: "
            f"{summary['eligible_snapshot_tasks_total']} brochure snapshots "
            "across the selected window and deferred comparison bench."
        )
    for task in tasks:
        snapshot_path = task["snapshot_path"]
        if not isinstance(snapshot_path, Path):
            raise TypeError("snapshot_path must be a Path.")
        if snapshot_path.exists():
            summary["snapshots_already_cached"] += 1
            continue
        generated = ensure_text_snapshot(
            task["member"],
            task["pdf_path"],
            snapshot_path,
            user_agent=user_agent,
            allow_download=allow_download,
        )
        if generated:
            summary["snapshots_generated"] += 1
        else:
            summary["snapshots_already_cached"] += 1
    if progress is not None:
        progress(
            "snapshot_backfill_complete: "
            f"{summary['snapshots_generated']} generated, "
            f"{summary['snapshots_already_cached']} already cached."
        )
    return summary


def refresh_skipped_candidate_cache_statuses(
    skipped_candidates: list[dict[str, object]],
    cache_status_lookup: dict[str, dict[str, bool]],
) -> None:
    for entry in skipped_candidates:
        firm_id = str(entry["firm_id"])
        if firm_id in cache_status_lookup:
            entry["cache_status"] = cache_status_lookup[firm_id]


def load_brochure_text(member, pdf_path: Path, snapshot_path: Path, *, user_agent: str, allow_download: bool = True) -> str:
    ensure_text_snapshot(member, pdf_path, snapshot_path, user_agent=user_agent, allow_download=allow_download)
    return snapshot_path.read_text()


def run(*, cache_only: bool = False, progress: Callable[[str], None] | None = None) -> dict[str, Path]:
    source_config = load_json_file(REPO_ROOT / "configs" / "sources" / "first_slice_sources.json")
    rubric = load_json_file(REPO_ROOT / "configs" / "rubrics" / "first_slice_rubric_v1.json")
    themes_payload = load_json_file(REPO_ROOT / "configs" / "themes" / "sec_regulatory_themes_v1.json")
    selection = source_config["selection"]

    raw_root = REPO_ROOT / "data" / "raw"
    snapshot_root = REPO_ROOT / "data" / "snapshots"
    canonical_root = REPO_ROOT / "data" / "canonical" / "first_slice"
    artifact_root = REPO_ROOT / "artifacts" / "first_slice"

    reports_metadata = fetch_json(
        source_config["reports_metadata_url"],
        raw_root / "sec" / "reports_metadata" / "reports_metadata.json",
        headers={"User-Agent": source_config["browser_headers"]["user_agent"]},
        allow_download=not cache_only,
    )
    prior_brochure_archive, latest_brochure_archive = select_latest_archives(reports_metadata, "advBrochures", count=2)
    prior_filing_archive, latest_filing_archive = select_latest_archives(reports_metadata, "advFilingData", count=2)

    current_members = list_zip_members(
        latest_brochure_archive.url,
        user_agent=source_config["browser_headers"]["user_agent"],
        cache_path=archive_index_cache_path(raw_root, latest_brochure_archive),
        allow_download=not cache_only,
    )
    prior_members = list_zip_members(
        prior_brochure_archive.url,
        user_agent=source_config["browser_headers"]["user_agent"],
        cache_path=archive_index_cache_path(raw_root, prior_brochure_archive),
        allow_download=not cache_only,
    )

    pairs = candidate_pairs(
        latest_brochure_archive,
        prior_brochure_archive,
        current_members,
        prior_members,
        selection["require_single_brochure_file_per_month"],
    )
    selection_limit = selection["cohort_size"] * 4
    shortlist_limit = selection["cohort_size"]
    pair_cache_statuses = [cache_status_for_pair(raw_root, snapshot_root, pair) for pair in pairs]
    pair_lookup = {pair["firm_id"]: pair for pair in pairs}
    cache_status_lookup = {pair["firm_id"]: cache_status for pair, cache_status in zip(pairs, pair_cache_statuses)}
    cache_complete_pairs_total = sum(1 for status in pair_cache_statuses if pair_has_complete_cache(status))
    prioritized_pairs = sorted(
        zip(pairs, pair_cache_statuses),
        key=lambda item: selection_priority_tuple(item[0], item[1]),
        reverse=True,
    )

    filing_zip_paths = {
        "current": download_file(
            latest_filing_archive.url,
            filing_zip_cache_path(raw_root, latest_filing_archive),
            allow_download=not cache_only,
        ),
        "prior": download_file(
            prior_filing_archive.url,
            filing_zip_cache_path(raw_root, prior_filing_archive),
            allow_download=not cache_only,
        ),
    }

    shortlisted: list[dict] = []
    scored_selected: list[dict] = []
    selected_pairs = []
    selected_details_by_firm: dict[str, dict[str, object]] = {}
    skipped_candidates: list[dict[str, object]] = []
    for pair, cache_status in prioritized_pairs:
        if len(selected_pairs) >= selection_limit:
            skip_reason = cache_gap_reason(cache_status) or "selection_window_limit"
            skipped_candidates.append(
                cache_report_entry(
                    pair,
                    cache_status=cache_status,
                    skip_stage="selection",
                    skip_reason=skip_reason,
                )
            )
            continue
        try:
            detail = fetch_firm_detail(
                source_config,
                pair["firm_id"],
                firm_detail_cache_path(raw_root, pair["firm_id"]),
                allow_download=not cache_only,
            )
        except FileNotFoundError:
            skipped_candidates.append(
                cache_report_entry(
                    pair,
                    cache_status=cache_status,
                    skip_stage="selection",
                    skip_reason="missing_firm_detail_cache",
                )
            )
            continue
        ia_scope = detail.get("basicInformation", {}).get("iaScope")
        if ia_scope != "ACTIVE":
            skipped_candidates.append(
                cache_report_entry(
                    pair,
                    cache_status=cache_status,
                    skip_stage="selection",
                    skip_reason="inactive_scope",
                    detail=detail,
                    extra={"ia_scope": ia_scope or ""},
                )
            )
            continue
        selected_pairs.append((pair, detail))
        selected_details_by_firm[pair["firm_id"]] = detail

    if not selected_pairs:
        raise RuntimeError("No active brochure pairs were available for the first slice.")

    selected_firm_ids = {pair["firm_id"] for pair, _ in selected_pairs}
    selection_window_firm_ids = {
        str(entry["firm_id"]) for entry in skipped_candidates if entry["skip_reason"] == "selection_window_limit"
    }
    filing_context_firm_ids = selected_firm_ids | selection_window_firm_ids
    filing_context_current = filing_rows(filing_zip_paths["current"], firm_ids=filing_context_firm_ids)
    filing_context_prior = filing_rows(filing_zip_paths["prior"], firm_ids=filing_context_firm_ids)
    deferred_selection_entries = build_selection_window_artifact(
        source_version=source_config["version"],
        selection_limit=selection_limit,
        selected_pairs_total=len(selected_pairs),
        shortlisted_total=0,
        raw_root=raw_root,
        skipped_candidates=skipped_candidates,
    )["deferred_candidates"]
    snapshot_backfill_tasks = build_snapshot_backfill_tasks(
        selected_pairs=selected_pairs,
        deferred_selection_entries=deferred_selection_entries,
        pair_lookup=pair_lookup,
        cache_status_lookup=cache_status_lookup,
        raw_root=raw_root,
        snapshot_root=snapshot_root,
    )
    snapshot_backfill_summary = backfill_brochure_text_snapshots(
        snapshot_backfill_tasks,
        user_agent=source_config["browser_headers"]["user_agent"],
        allow_download=not cache_only,
        progress=progress,
    )
    cache_status_lookup = {pair["firm_id"]: cache_status_for_pair(raw_root, snapshot_root, pair) for pair in pairs}
    refresh_skipped_candidate_cache_statuses(skipped_candidates, cache_status_lookup)
    initial_selection_window_payload = build_selection_window_artifact(
        source_version=source_config["version"],
        selection_limit=selection_limit,
        selected_pairs_total=len(selected_pairs),
        shortlisted_total=0,
        raw_root=raw_root,
        skipped_candidates=skipped_candidates,
    )
    if progress is not None:
        progress(f"selected_window_scoring: {len(selected_pairs)} active pairs queued for scoring.")

    for pair, detail in selected_pairs:
        cache_status = cache_status_lookup[pair["firm_id"]]
        scored_delta, skip_info = evaluate_pair(
            pair=pair,
            detail=detail,
            cache_status=cache_status,
            raw_root=raw_root,
            snapshot_root=snapshot_root,
            source_config=source_config,
            cache_only=cache_only,
            selection=selection,
            rubric=rubric,
            themes_payload=themes_payload,
            filing_context_current=filing_context_current,
            filing_context_prior=filing_context_prior,
        )
        if skip_info is not None:
            skipped_candidates.append(
                cache_report_entry(
                    pair,
                    cache_status=cache_status,
                    skip_stage=str(skip_info["skip_stage"]),
                    skip_reason=str(skip_info["skip_reason"]),
                    detail=detail,
                    extra=skip_info.get("extra"),
                )
            )
            continue
        scored_selected.append(scored_delta)

    if not scored_selected:
        raise RuntimeError("No scored firms were produced for the first slice.")

    scored_selected.sort(key=lambda item: item["score"]["overall_score"], reverse=True)
    shortlisted = scored_selected[:shortlist_limit]
    shortlist_floor = shortlisted[-1]
    shortlist_underfilled = len(shortlisted) < shortlist_limit
    selection_window_evaluations: dict[str, tuple[dict[str, object] | None, dict[str, object] | None]] = {}
    promotion_candidates: list[dict[str, object]] = []
    if progress is not None:
        progress(
            "deferred_comparison_scoring: "
            f"{len(initial_selection_window_payload['deferred_candidates'])} deferred pairs queued for comparison."
        )
    for selection_entry in initial_selection_window_payload["deferred_candidates"]:
        pair = pair_lookup[str(selection_entry["firm_id"])]
        detail = load_cached_firm_detail(firm_detail_cache_path(raw_root, str(selection_entry["firm_id"])))
        scored_delta, skip_info = evaluate_pair(
            pair=pair,
            detail=detail,
            cache_status=selection_entry["cache_status"],
            raw_root=raw_root,
            snapshot_root=snapshot_root,
            source_config=source_config,
            cache_only=cache_only,
            selection=selection,
            rubric=rubric,
            themes_payload=themes_payload,
            filing_context_current=filing_context_current,
            filing_context_prior=filing_context_prior,
        )
        firm_id = str(selection_entry["firm_id"])
        selection_window_evaluations[firm_id] = (scored_delta, skip_info)
        if scored_delta is not None and (
            shortlist_underfilled or scored_delta["score"]["overall_score"] >= shortlist_floor["score"]["overall_score"]
        ):
            promotion_candidates.append(scored_delta)

    shortlisted, promoted_ids, _displaced_ids = merge_shortlist_with_promotions(
        shortlisted,
        promotion_candidates,
        shortlist_limit=shortlist_limit,
    )
    shortlist_ids = {item["firm_id"] for item in shortlisted}
    if promoted_ids:
        skipped_candidates = [
            entry
            for entry in skipped_candidates
            if not (entry["skip_reason"] == "selection_window_limit" and str(entry["firm_id"]) in promoted_ids)
        ]
    for scored_delta in scored_selected:
        firm_id = scored_delta["firm_id"]
        if firm_id in shortlist_ids:
            continue
        skipped_candidates.append(
            cache_report_entry(
                pair_lookup[firm_id],
                cache_status=cache_status_lookup[firm_id],
                skip_stage="shortlist",
                skip_reason="shortlist_window_limit",
                detail=selected_details_by_firm[firm_id],
            )
        )

    shortlisted.sort(key=lambda item: item["score"]["overall_score"], reverse=True)
    shortlist_rows = [shortlist_row(item) for item in shortlisted]
    for rank, row in enumerate(shortlist_rows, start=1):
        row["rank"] = rank

    canonical_payload = {
        "version": source_config["version"],
        "brochure_archive_pair": [
            {"display_name": prior_brochure_archive.display_name, "year": prior_brochure_archive.year, "url": prior_brochure_archive.url},
            {"display_name": latest_brochure_archive.display_name, "year": latest_brochure_archive.year, "url": latest_brochure_archive.url},
        ],
        "firms": shortlisted,
    }
    top_delta_payload = shortlisted[0]
    cache_report_payload = build_cache_report(
        source_version=source_config["version"],
        cache_only=cache_only,
        prior_brochure_archive=prior_brochure_archive,
        latest_brochure_archive=latest_brochure_archive,
        candidate_pairs_total=len(pairs),
        selection_limit=selection_limit,
        shortlist_limit=shortlist_limit,
        selected_pairs_total=len(selected_pairs),
        shortlisted_total=len(shortlisted),
        cache_complete_pairs_total=cache_complete_pairs_total,
        skipped_candidates=skipped_candidates,
        snapshot_backfill_summary=snapshot_backfill_summary,
    )
    selection_window_payload = build_selection_window_artifact(
        source_version=source_config["version"],
        selection_limit=selection_limit,
        selected_pairs_total=len(selected_pairs),
        shortlisted_total=len(shortlisted),
        raw_root=raw_root,
        skipped_candidates=skipped_candidates,
    )
    shortlist_floor = shortlisted[-1]
    selection_window_comparisons = []
    for selection_entry in selection_window_payload["deferred_candidates"]:
        firm_id = str(selection_entry["firm_id"])
        scored_delta, skip_info = selection_window_evaluations.get(firm_id, (None, None))
        if scored_delta is None and skip_info is None:
            pair = pair_lookup[firm_id]
            detail = load_cached_firm_detail(firm_detail_cache_path(raw_root, firm_id))
            scored_delta, skip_info = evaluate_pair(
                pair=pair,
                detail=detail,
                cache_status=selection_entry["cache_status"],
                raw_root=raw_root,
                snapshot_root=snapshot_root,
                source_config=source_config,
                cache_only=cache_only,
                selection=selection,
                rubric=rubric,
                themes_payload=themes_payload,
                filing_context_current=filing_context_current,
                filing_context_prior=filing_context_prior,
            )
        selection_window_comparisons.append(
            selection_window_comparison_entry(
                selection_entry,
                shortlist_floor=shortlist_floor,
                scored_delta=scored_delta,
                skip_info=skip_info,
            )
        )
    selection_window_comparison_payload = build_selection_window_comparison_artifact(
        source_version=source_config["version"],
        selection_limit=selection_limit,
        shortlist_limit=shortlist_limit,
        shortlist_floor=shortlist_floor,
        comparisons=selection_window_comparisons,
    )

    output_paths = {
        "canonical_shortlist_json": write_json(canonical_root / "shortlist_v1.json", canonical_payload),
        "canonical_top_delta_json": write_json(canonical_root / f"top_delta_{top_delta_payload['firm_id']}.json", top_delta_payload),
        "artifact_shortlist_json": write_json(artifact_root / "shortlist_v1.json", canonical_payload),
        "artifact_top_delta_json": write_json(artifact_root / f"top_delta_{top_delta_payload['firm_id']}.json", top_delta_payload),
        "canonical_cache_report_json": write_json(canonical_root / "cache_report_v1.json", cache_report_payload),
        "artifact_cache_report_json": write_json(artifact_root / "cache_report_v1.json", cache_report_payload),
        "canonical_selection_window_json": write_json(canonical_root / "selection_window_v1.json", selection_window_payload),
        "artifact_selection_window_json": write_json(artifact_root / "selection_window_v1.json", selection_window_payload),
        "canonical_selection_window_comparison_json": write_json(
            canonical_root / "selection_window_comparison_v1.json", selection_window_comparison_payload
        ),
        "artifact_selection_window_comparison_json": write_json(
            artifact_root / "selection_window_comparison_v1.json", selection_window_comparison_payload
        ),
    }
    output_paths["canonical_shortlist_csv"] = write_shortlist_csv(canonical_root / "shortlist_v1.csv", shortlist_rows)
    output_paths["artifact_shortlist_csv"] = write_shortlist_csv(artifact_root / "shortlist_v1.csv", shortlist_rows)
    output_paths["canonical_cohort_json"] = write_json(
        canonical_root / "cohort_v1.json",
        {
            "selected_firms": [
                {
                    "firm_id": item["firm_id"],
                    "firm_name": item["firm_name"],
                    "current_submitted_at": item["current_snapshot"]["submitted_at"],
                    "prior_submitted_at": item["prior_snapshot"]["submitted_at"],
                }
                for item in shortlisted
            ]
        },
    )
    return output_paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local-only first slice for the RIA Inflection Engine.")
    parser.add_argument(
        "--cache-only",
        action="store_true",
        help="Reuse only existing local SEC/IAPD/raw brochure caches and skip uncached candidates instead of fetching live data.",
    )
    args = parser.parse_args()
    output_paths = run(cache_only=args.cache_only, progress=lambda message: print(message, flush=True))
    for label, path in output_paths.items():
        print(f"{label}: {path}")


if __name__ == "__main__":
    main()
