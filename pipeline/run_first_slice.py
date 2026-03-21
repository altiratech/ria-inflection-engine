from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
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


def run() -> dict[str, Path]:
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
    )
    prior_brochure_archive, latest_brochure_archive = select_latest_archives(reports_metadata, "advBrochures", count=2)
    prior_filing_archive, latest_filing_archive = select_latest_archives(reports_metadata, "advFilingData", count=2)

    current_members = list_zip_members(
        latest_brochure_archive.url,
        user_agent=source_config["browser_headers"]["user_agent"],
        cache_path=archive_index_cache_path(raw_root, latest_brochure_archive),
    )
    prior_members = list_zip_members(
        prior_brochure_archive.url,
        user_agent=source_config["browser_headers"]["user_agent"],
        cache_path=archive_index_cache_path(raw_root, prior_brochure_archive),
    )

    pairs = candidate_pairs(
        latest_brochure_archive,
        prior_brochure_archive,
        current_members,
        prior_members,
        selection["require_single_brochure_file_per_month"],
    )

    filing_zip_paths = {
        "current": download_file(latest_filing_archive.url, filing_zip_cache_path(raw_root, latest_filing_archive)),
        "prior": download_file(prior_filing_archive.url, filing_zip_cache_path(raw_root, prior_filing_archive)),
    }

    shortlisted: list[dict] = []
    selected_pairs = []
    for pair in pairs:
        if len(selected_pairs) >= selection["cohort_size"] * 4:
            break
        detail = fetch_firm_detail(
            source_config,
            pair["firm_id"],
            raw_root / "adviserinfo" / "firm_detail" / f"{pair['firm_id']}.json",
        )
        if detail.get("basicInformation", {}).get("iaScope") != "ACTIVE":
            continue
        selected_pairs.append((pair, detail))

    if not selected_pairs:
        raise RuntimeError("No active brochure pairs were available for the first slice.")

    selected_firm_ids = {pair["firm_id"] for pair, _ in selected_pairs}
    filing_context_current = filing_rows(filing_zip_paths["current"], firm_ids=selected_firm_ids)
    filing_context_prior = filing_rows(filing_zip_paths["prior"], firm_ids=selected_firm_ids)

    for pair, detail in selected_pairs:
        if len(shortlisted) >= selection["cohort_size"]:
            break
        current_pdf_path = write_member_cache(
            pair["current_member"].member,
            brochure_member_cache_path(
                raw_root, pair["current_archive"], pair["firm_id"], pair["current_member"].member.file_name
            ),
            user_agent=source_config["browser_headers"]["user_agent"],
        )
        prior_pdf_path = write_member_cache(
            pair["prior_member"].member,
            brochure_member_cache_path(raw_root, pair["prior_archive"], pair["firm_id"], pair["prior_member"].member.file_name),
            user_agent=source_config["browser_headers"]["user_agent"],
        )
        current_text = snapshot_text(
            current_pdf_path.read_bytes(),
            text_snapshot_path(snapshot_root, pair["current_archive"], pair["firm_id"], pair["current_member"].member.file_name),
        )
        prior_text = snapshot_text(
            prior_pdf_path.read_bytes(),
            text_snapshot_path(snapshot_root, pair["prior_archive"], pair["firm_id"], pair["prior_member"].member.file_name),
        )
        if brochure_type(current_text) != "part_2a" or brochure_type(prior_text) != "part_2a":
            continue

        current_sections = sectionize_brochure(current_text)
        prior_sections = sectionize_brochure(prior_text)
        if len(current_sections) < selection["minimum_sections_per_snapshot"] or len(prior_sections) < selection["minimum_sections_per_snapshot"]:
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

    output_paths = {
        "canonical_shortlist_json": write_json(canonical_root / "shortlist_v1.json", canonical_payload),
        "canonical_top_delta_json": write_json(canonical_root / f"top_delta_{top_delta_payload['firm_id']}.json", top_delta_payload),
        "artifact_shortlist_json": write_json(artifact_root / "shortlist_v1.json", canonical_payload),
        "artifact_top_delta_json": write_json(artifact_root / f"top_delta_{top_delta_payload['firm_id']}.json", top_delta_payload),
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
    parser.parse_args()
    output_paths = run()
    for label, path in output_paths.items():
        print(f"{label}: {path}")


if __name__ == "__main__":
    main()
