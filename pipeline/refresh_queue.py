from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

from pipeline.brochures import snapshot_text
from pipeline.iapd import ArchiveFile, fetch_firm_detail
from pipeline.remote_zip import ZipMember, list_zip_members, write_member_cache


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_json_file(path: Path) -> dict:
    return json.loads(path.read_text())


def brochure_member_cache_path(raw_root: Path, archive: ArchiveFile, firm_id: str, file_name: str) -> Path:
    return raw_root / "sec" / "brochures" / archive.year / archive.display_name.lower().replace(" ", "_") / firm_id / file_name


def text_snapshot_path(snapshot_root: Path, archive: ArchiveFile, firm_id: str, file_name: str) -> Path:
    return snapshot_root / "brochure_text" / archive.year / archive.display_name.lower().replace(" ", "_") / firm_id / f"{file_name}.txt"


def firm_detail_cache_path(raw_root: Path, firm_id: str) -> Path:
    return raw_root / "adviserinfo" / "firm_detail" / f"{firm_id}.json"


def load_cache_report(path: Path) -> dict:
    return json.loads(path.read_text())


def flatten_refresh_targets(
    cache_report: dict,
    *,
    action: str | None = None,
    limit: int | None = None,
) -> list[dict[str, object]]:
    flattened: list[dict[str, object]] = []
    for group in cache_report.get("next_refresh_targets", {}).get("groups", []):
        refresh_action = group["refresh_action"]
        if action and refresh_action != action:
            continue
        for target in group.get("targets", []):
            flattened.append(
                {
                    "refresh_action": refresh_action,
                    "skip_reason": group["skip_reason"],
                    **target,
                }
            )
            if limit is not None and len(flattened) >= limit:
                return flattened
    return flattened


def report_archive_index_cache_path(raw_root: Path, archive_payload: dict[str, str]) -> Path:
    file_name = Path(urlparse(archive_payload["url"]).path).name
    return raw_root / "sec" / "brochure_indexes" / f"{file_name}.json"


def archive_stub_from_payload(archive_payload: dict[str, str]) -> ArchiveFile:
    file_name = Path(urlparse(archive_payload["url"]).path).name
    return ArchiveFile(
        display_name=archive_payload["display_name"],
        display_order="",
        file_name=file_name,
        size=0,
        uploaded_on="",
        url=archive_payload["url"],
        year=archive_payload["year"],
    )


def archive_payload_for_action(cache_report: dict, refresh_action: str) -> dict[str, str]:
    brochure_pair = cache_report["brochure_archive_pair"]
    if refresh_action == "cache_current_brochure":
        return brochure_pair[1]
    if refresh_action == "cache_prior_brochure":
        return brochure_pair[0]
    raise ValueError(f"Refresh action {refresh_action} does not use brochure archives.")


def find_archive_member(
    source_config: dict,
    archive_payload: dict[str, str],
    file_name: str,
    *,
    raw_root: Path,
) -> ZipMember:
    members = list_zip_members(
        archive_payload["url"],
        user_agent=source_config["browser_headers"]["user_agent"],
        cache_path=report_archive_index_cache_path(raw_root, archive_payload),
        allow_download=True,
    )
    for member in members:
        if member.file_name == file_name:
            return member
    raise ValueError(f"Could not locate brochure member {file_name} in archive {archive_payload['url']}.")


def apply_refresh_target(
    target: dict[str, object],
    *,
    cache_report: dict,
    source_config: dict,
    raw_root: Path,
    snapshot_root: Path,
    generate_snapshots: bool = False,
) -> dict[str, object]:
    action = str(target["refresh_action"])
    firm_id = str(target["firm_id"])

    if action == "fetch_firm_detail":
        destination = firm_detail_cache_path(raw_root, firm_id)
        already_cached = destination.exists()
        fetch_firm_detail(source_config, firm_id, destination, allow_download=True)
        return {
            "refresh_action": action,
            "firm_id": firm_id,
            "status": "already_cached" if already_cached else "fetched",
            "path": str(destination),
        }

    archive_payload = archive_payload_for_action(cache_report, action)
    file_name_key = "current_file_name" if action == "cache_current_brochure" else "prior_file_name"
    file_name = str(target[file_name_key])
    member = find_archive_member(source_config, archive_payload, file_name, raw_root=raw_root)
    archive_stub = archive_stub_from_payload(archive_payload)
    pdf_path = brochure_member_cache_path(
        raw_root,
        archive_stub,
        firm_id,
        file_name,
    )
    already_cached = pdf_path.exists()
    write_member_cache(member, pdf_path, user_agent=source_config["browser_headers"]["user_agent"], allow_download=True)

    result = {
        "refresh_action": action,
        "firm_id": firm_id,
        "status": "already_cached" if already_cached else "fetched",
        "path": str(pdf_path),
    }

    if generate_snapshots:
        snapshot_path = text_snapshot_path(
            snapshot_root,
            archive_stub,
            firm_id,
            file_name,
        )
        snapshot_already_cached = snapshot_path.exists()
        try:
            snapshot_text(None, snapshot_path, source_pdf_path=pdf_path)
            result["snapshot_path"] = str(snapshot_path)
            result["snapshot_status"] = "already_cached" if snapshot_already_cached else "generated"
        except ModuleNotFoundError as exc:
            result["snapshot_status"] = "skipped"
            result["snapshot_error"] = str(exc)

    return result


def summarize_plan(cache_report: dict, targets: list[dict[str, object]]) -> dict[str, object]:
    return {
        "queue_summary": cache_report.get("next_refresh_targets", {}),
        "selected_targets_total": len(targets),
        "selected_targets": targets,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Hydrate local adviser/brochure caches from cache_report_v1 next_refresh_targets.")
    parser.add_argument(
        "--cache-report",
        default=str(REPO_ROOT / "data" / "canonical" / "first_slice" / "cache_report_v1.json"),
        help="Path to cache_report_v1.json.",
    )
    parser.add_argument(
        "--action",
        choices=["all", "fetch_firm_detail", "cache_current_brochure", "cache_prior_brochure"],
        default="all",
        help="Restrict the refresh plan to one action.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of queued targets to include from the ordered next_refresh_targets queue.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually fetch the queued targets. Without this flag, the command prints a dry-run plan only.",
    )
    parser.add_argument(
        "--generate-snapshots",
        action="store_true",
        help="When caching brochure PDFs, also generate brochure text snapshots if pypdf is available.",
    )
    args = parser.parse_args()

    cache_report_path = Path(args.cache_report)
    cache_report = load_cache_report(cache_report_path)
    source_config = load_json_file(REPO_ROOT / "configs" / "sources" / "first_slice_sources.json")
    raw_root = REPO_ROOT / "data" / "raw"
    snapshot_root = REPO_ROOT / "data" / "snapshots"

    selected_action = None if args.action == "all" else args.action
    targets = flatten_refresh_targets(cache_report, action=selected_action, limit=args.limit)
    if not args.apply:
        print(json.dumps({"mode": "dry_run", **summarize_plan(cache_report, targets)}, indent=2))
        return

    results = [
        apply_refresh_target(
            target,
            cache_report=cache_report,
            source_config=source_config,
            raw_root=raw_root,
            snapshot_root=snapshot_root,
            generate_snapshots=args.generate_snapshots,
        )
        for target in targets
    ]
    print(json.dumps({"mode": "apply", "selected_targets_total": len(targets), "results": results}, indent=2))


if __name__ == "__main__":
    main()
