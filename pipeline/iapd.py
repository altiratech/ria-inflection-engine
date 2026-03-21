from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any
import urllib.request


@dataclass(frozen=True)
class ArchiveFile:
    display_name: str
    display_order: str
    file_name: str
    size: int
    uploaded_on: str
    url: str
    year: str


def browser_headers(source_config: dict[str, Any], *, referer_suffix: str = "") -> dict[str, str]:
    payload = source_config["browser_headers"]
    referer_base = payload["referer_base"]
    return {
        "origin": payload["origin"],
        "referer": f"{referer_base}{referer_suffix}",
        "user-agent": payload["user_agent"],
        "accept": payload["accept"],
    }


def fetch_json(
    url: str,
    destination: Path,
    *,
    headers: dict[str, str] | None = None,
    allow_download: bool = True,
) -> dict[str, Any]:
    if destination.exists():
        return json.loads(destination.read_text())
    if not allow_download:
        raise FileNotFoundError(f"Missing cached JSON payload: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)
    destination.write_text(json.dumps(payload, indent=2))
    return payload


def download_file(url: str, destination: Path, *, allow_download: bool = True) -> Path:
    if destination.exists():
        return destination
    if not allow_download:
        raise FileNotFoundError(f"Missing cached file payload: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        destination.write_bytes(response.read())
    return destination


def sort_key_for_display_order(year: str, display_order: str) -> tuple[int, tuple[int, ...]]:
    parts = tuple(int(part) for part in display_order.split("-"))
    return int(year), parts


def resolve_archive_url(report_type: str, file_name: str, year: str) -> str:
    return f"https://reports.adviserinfo.sec.gov/reports/foia/{report_type}/{year}/{file_name}"


def select_latest_archives(metadata: dict[str, Any], report_type: str, *, count: int = 2) -> list[ArchiveFile]:
    files: list[ArchiveFile] = []
    for year, payload in metadata[report_type].items():
        if not year.isdigit():
            continue
        for entry in payload["files"]:
            files.append(
                ArchiveFile(
                    display_name=entry["displayName"],
                    display_order=entry["displayOrder"],
                    file_name=entry["fileName"],
                    size=int(entry["size"]),
                    uploaded_on=entry["uploadedOn"],
                    url=resolve_archive_url(report_type, entry["fileName"], year),
                    year=year,
                )
            )
    files.sort(key=lambda item: sort_key_for_display_order(item.year, item.display_order))
    return files[-count:]


def fetch_firm_detail(
    source_config: dict[str, Any],
    firm_id: str,
    destination: Path,
    *,
    allow_download: bool = True,
) -> dict[str, Any]:
    url = source_config["iapd_firm_detail_url_template"].format(firm_id=firm_id)
    payload = fetch_json(
        url,
        destination,
        headers=browser_headers(source_config, referer_suffix=firm_id),
        allow_download=allow_download,
    )
    hits = payload.get("hits", {}).get("hits", [])
    if not hits:
        raise ValueError(f"No IAPD firm detail payload found for firm {firm_id}.")
    return json.loads(hits[0]["_source"]["iacontent"])
