from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from collections import Counter
import zipfile

from pipeline.brochures import brochure_type, parse_brochure_member, snapshot_text
from pipeline.iapd import ArchiveFile, download_file, fetch_firm_detail, fetch_json, select_latest_archives
from pipeline.normalize import build_section_deltas, sectionize_brochure
from pipeline.remote_zip import list_zip_members, write_member_cache
from pipeline.score import score_firm_delta


REPO_ROOT = Path(__file__).resolve().parents[1]


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
) -> dict[str, object]:
    reason_counts = Counter(entry["skip_reason"] for entry in skipped_candidates)
    stage_counts = Counter(entry["skip_stage"] for entry in skipped_candidates)
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
        "skipped_candidates": skipped_candidates,
    }


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


def load_brochure_text(member, pdf_path: Path, snapshot_path: Path, *, user_agent: str, allow_download: bool = True) -> str:
    if snapshot_path.exists():
        return snapshot_path.read_text()
    cached_pdf_path = write_member_cache(member, pdf_path, user_agent=user_agent, allow_download=allow_download)
    return snapshot_text(None, snapshot_path, source_pdf_path=cached_pdf_path)


def run(*, cache_only: bool = False) -> dict[str, Path]:
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
    cache_complete_pairs_total = sum(1 for status in pair_cache_statuses if pair_has_complete_cache(status))

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
    selected_pairs = []
    skipped_candidates: list[dict[str, object]] = []
    for pair, cache_status in zip(pairs, pair_cache_statuses):
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

    if not selected_pairs:
        raise RuntimeError("No active brochure pairs were available for the first slice.")

    selected_firm_ids = {pair["firm_id"] for pair, _ in selected_pairs}
    filing_context_current = filing_rows(filing_zip_paths["current"], firm_ids=selected_firm_ids)
    filing_context_prior = filing_rows(filing_zip_paths["prior"], firm_ids=selected_firm_ids)

    for pair, detail in selected_pairs:
        cache_status = cache_status_for_pair(raw_root, snapshot_root, pair)
        if len(shortlisted) >= shortlist_limit:
            skipped_candidates.append(
                cache_report_entry(
                    pair,
                    cache_status=cache_status,
                    skip_stage="shortlist",
                    skip_reason="shortlist_window_limit",
                    detail=detail,
                )
            )
            continue
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
            skipped_candidates.append(
                cache_report_entry(
                    pair,
                    cache_status=cache_status,
                    skip_stage="brochure",
                    skip_reason="missing_current_brochure_cache",
                    detail=detail,
                )
            )
            continue
        try:
            prior_text = load_brochure_text(
                pair["prior_member"].member,
                prior_pdf_path,
                prior_snapshot_path,
                user_agent=source_config["browser_headers"]["user_agent"],
                allow_download=not cache_only,
            )
        except FileNotFoundError:
            skipped_candidates.append(
                cache_report_entry(
                    pair,
                    cache_status=cache_status,
                    skip_stage="brochure",
                    skip_reason="missing_prior_brochure_cache",
                    detail=detail,
                )
            )
            continue
        current_brochure_type = brochure_type(current_text)
        prior_brochure_type = brochure_type(prior_text)
        if current_brochure_type != "part_2a" or prior_brochure_type != "part_2a":
            skipped_candidates.append(
                cache_report_entry(
                    pair,
                    cache_status=cache_status,
                    skip_stage="brochure",
                    skip_reason="unsupported_brochure_type",
                    detail=detail,
                    extra={
                        "current_brochure_type": current_brochure_type,
                        "prior_brochure_type": prior_brochure_type,
                    },
                )
            )
            continue

        current_sections = sectionize_brochure(current_text)
        prior_sections = sectionize_brochure(prior_text)
        if len(current_sections) < selection["minimum_sections_per_snapshot"] or len(prior_sections) < selection["minimum_sections_per_snapshot"]:
            skipped_candidates.append(
                cache_report_entry(
                    pair,
                    cache_status=cache_status,
                    skip_stage="normalize",
                    skip_reason="insufficient_sections",
                    detail=detail,
                    extra={
                        "current_section_count": len(current_sections),
                        "prior_section_count": len(prior_sections),
                    },
                )
            )
            continue

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
            skipped_candidates.append(
                cache_report_entry(
                    pair,
                    cache_status=cache_status,
                    skip_stage="score",
                    skip_reason="no_scored_evidence",
                    detail=detail,
                )
            )
            continue
        shortlisted.append(scored_delta)

    if not shortlisted:
        raise RuntimeError("No scored firms were produced for the first slice.")

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
    )

    output_paths = {
        "canonical_shortlist_json": write_json(canonical_root / "shortlist_v1.json", canonical_payload),
        "canonical_top_delta_json": write_json(canonical_root / f"top_delta_{top_delta_payload['firm_id']}.json", top_delta_payload),
        "artifact_shortlist_json": write_json(artifact_root / "shortlist_v1.json", canonical_payload),
        "artifact_top_delta_json": write_json(artifact_root / f"top_delta_{top_delta_payload['firm_id']}.json", top_delta_payload),
        "canonical_cache_report_json": write_json(canonical_root / "cache_report_v1.json", cache_report_payload),
        "artifact_cache_report_json": write_json(artifact_root / "cache_report_v1.json", cache_report_payload),
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
    output_paths = run(cache_only=args.cache_only)
    for label, path in output_paths.items():
        print(f"{label}: {path}")


if __name__ == "__main__":
    main()
