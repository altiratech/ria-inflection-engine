from __future__ import annotations

from pipeline.refresh_queue import apply_refresh_target, archive_stub_from_payload, flatten_refresh_targets
from pipeline.remote_zip import ZipMember


SAMPLE_REPORT = {
    "brochure_archive_pair": [
        {
            "display_name": "January",
            "year": "2026",
            "url": "https://reports.adviserinfo.sec.gov/reports/foia/advBrochures/2026/ADV_Brochures_2026_January.zip",
        },
        {
            "display_name": "February",
            "year": "2026",
            "url": "https://reports.adviserinfo.sec.gov/reports/foia/advBrochures/2026/ADV_Brochures_2026_February.zip",
        },
    ],
    "next_refresh_targets": {
        "queue_limit_per_reason": 10,
        "actionable_gap_total": 3,
        "groups": [
            {
                "skip_reason": "missing_firm_detail_cache",
                "refresh_action": "fetch_firm_detail",
                "candidate_count": 2,
                "targets": [
                    {
                        "firm_id": "173129",
                        "firm_name": "",
                        "sec_number": "",
                        "current_submitted_at": "20260223",
                        "prior_submitted_at": "20260113",
                        "current_file_name": "173129_357943_13_20260223.pdf",
                        "prior_file_name": "173129_357943_12_20260113.pdf",
                    },
                    {
                        "firm_id": "144039",
                        "firm_name": "",
                        "sec_number": "",
                        "current_submitted_at": "20260222",
                        "prior_submitted_at": "20260123",
                        "current_file_name": "144039_422189_2_20260222.pdf",
                        "prior_file_name": "144039_422189_1_20260123.pdf",
                    },
                ],
            },
            {
                "skip_reason": "missing_current_brochure_cache",
                "refresh_action": "cache_current_brochure",
                "candidate_count": 1,
                "targets": [
                    {
                        "firm_id": "140923",
                        "firm_name": "",
                        "sec_number": "",
                        "current_submitted_at": "20260220",
                        "prior_submitted_at": "20260129",
                        "current_file_name": "140923_58540_31_20260220.pdf",
                        "prior_file_name": "140923_58540_30_20260129.pdf",
                    }
                ],
            },
        ],
    },
}


def sample_source_config() -> dict:
    return {
        "browser_headers": {"user_agent": "test-agent"},
        "iapd_firm_detail_url_template": "https://example.com/{firm_id}.json",
    }


def test_archive_stub_from_payload_uses_archive_url_file_name() -> None:
    archive = archive_stub_from_payload(SAMPLE_REPORT["brochure_archive_pair"][1])

    assert archive.display_name == "February"
    assert archive.file_name == "ADV_Brochures_2026_February.zip"
    assert archive.year == "2026"


def test_flatten_refresh_targets_preserves_group_order_and_limit() -> None:
    targets = flatten_refresh_targets(SAMPLE_REPORT, limit=2)

    assert [target["refresh_action"] for target in targets] == [
        "fetch_firm_detail",
        "fetch_firm_detail",
    ]
    assert [target["firm_id"] for target in targets] == ["173129", "144039"]

    current_only = flatten_refresh_targets(SAMPLE_REPORT, action="cache_current_brochure")

    assert len(current_only) == 1
    assert current_only[0]["firm_id"] == "140923"


def test_apply_refresh_target_fetches_firm_detail_to_expected_cache_path(tmp_path, monkeypatch) -> None:
    destination_paths: list[str] = []

    def fake_fetch_firm_detail(source_config, firm_id, destination, *, allow_download):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("{}")
        destination_paths.append(str(destination))
        return {}

    monkeypatch.setattr("pipeline.refresh_queue.fetch_firm_detail", fake_fetch_firm_detail)

    target = flatten_refresh_targets(SAMPLE_REPORT, action="fetch_firm_detail", limit=1)[0]
    result = apply_refresh_target(
        target,
        cache_report=SAMPLE_REPORT,
        source_config=sample_source_config(),
        raw_root=tmp_path / "raw",
        snapshot_root=tmp_path / "snapshots",
    )

    assert result["refresh_action"] == "fetch_firm_detail"
    assert result["status"] == "fetched"
    assert destination_paths and destination_paths[0].endswith("173129.json")


def test_apply_refresh_target_caches_current_brochure_and_snapshot(tmp_path, monkeypatch) -> None:
    member = ZipMember(
        archive_url=SAMPLE_REPORT["brochure_archive_pair"][1]["url"],
        file_name="140923_58540_31_20260220.pdf",
        compressed_size=1,
        uncompressed_size=1,
        compression_method=0,
        crc32=0,
        local_header_offset=0,
    )

    monkeypatch.setattr("pipeline.refresh_queue.find_archive_member", lambda *args, **kwargs: member)

    def fake_write_member_cache(member, destination, *, user_agent, allow_download):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"%PDF-1.4")
        return destination

    def fake_snapshot_text(pdf_bytes, destination, *, source_pdf_path=None):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("cached snapshot")
        return "cached snapshot"

    monkeypatch.setattr("pipeline.refresh_queue.write_member_cache", fake_write_member_cache)
    monkeypatch.setattr("pipeline.refresh_queue.snapshot_text", fake_snapshot_text)

    target = flatten_refresh_targets(SAMPLE_REPORT, action="cache_current_brochure", limit=1)[0]
    result = apply_refresh_target(
        target,
        cache_report=SAMPLE_REPORT,
        source_config=sample_source_config(),
        raw_root=tmp_path / "raw",
        snapshot_root=tmp_path / "snapshots",
        generate_snapshots=True,
    )

    assert result["refresh_action"] == "cache_current_brochure"
    assert result["status"] == "fetched"
    assert result["snapshot_status"] == "generated"
    assert result["path"].endswith("140923_58540_31_20260220.pdf")
    assert result["snapshot_path"].endswith("140923_58540_31_20260220.pdf.txt")
