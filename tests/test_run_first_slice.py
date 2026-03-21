from __future__ import annotations

from pipeline.brochures import parse_brochure_member
from pipeline.iapd import ArchiveFile
from pipeline.remote_zip import ZipMember
from pipeline.run_first_slice import (
    build_cache_report,
    build_selection_window_artifact,
    cache_gap_reason,
    cache_report_entry,
    cache_status_for_pair,
    next_refresh_targets,
    pair_has_complete_cache,
    refresh_action_for_reason,
    selection_priority_tuple,
)


def make_archive(display_name: str, uploaded_on: str, file_name: str) -> ArchiveFile:
    return ArchiveFile(
        display_name=display_name,
        display_order="1",
        file_name=file_name,
        size=100,
        uploaded_on=uploaded_on,
        url=f"https://example.com/{file_name}",
        year="2026",
    )


def make_pair(firm_id: str) -> dict:
    current_archive = make_archive("February 2026", "2026-02-28", "current.zip")
    prior_archive = make_archive("January 2026", "2026-01-31", "prior.zip")
    current_member = parse_brochure_member(
        ZipMember(
            archive_url=current_archive.url,
            file_name=f"{firm_id}_1_1_20260228.pdf",
            compressed_size=10,
            uncompressed_size=10,
            compression_method=0,
            crc32=0,
            local_header_offset=0,
        )
    )
    prior_member = parse_brochure_member(
        ZipMember(
            archive_url=prior_archive.url,
            file_name=f"{firm_id}_1_1_20260131.pdf",
            compressed_size=10,
            uncompressed_size=10,
            compression_method=0,
            crc32=0,
            local_header_offset=0,
        )
    )
    assert current_member is not None
    assert prior_member is not None
    return {
        "firm_id": firm_id,
        "current_member": current_member,
        "prior_member": prior_member,
        "current_archive": current_archive,
        "prior_archive": prior_archive,
    }


def test_cache_status_for_pair_tracks_snapshot_and_pdf_layers(tmp_path) -> None:
    pair = make_pair("123456")
    raw_root = tmp_path / "raw"
    snapshot_root = tmp_path / "snapshots"

    current_snapshot = snapshot_root / "brochure_text" / "2026" / "february_2026" / "123456" / "123456_1_1_20260228.pdf.txt"
    current_snapshot.parent.mkdir(parents=True, exist_ok=True)
    current_snapshot.write_text("cached current brochure text")

    prior_pdf = raw_root / "sec" / "brochures" / "2026" / "january_2026" / "123456" / "123456_1_1_20260131.pdf"
    prior_pdf.parent.mkdir(parents=True, exist_ok=True)
    prior_pdf.write_bytes(b"%PDF-1.4")

    status = cache_status_for_pair(raw_root, snapshot_root, pair)

    assert status["firm_detail_cached"] is False
    assert status["current_text_snapshot_cached"] is True
    assert status["current_brochure_cache_available"] is True
    assert status["prior_brochure_pdf_cached"] is True
    assert status["prior_brochure_cache_available"] is True
    assert pair_has_complete_cache(status) is False

    firm_detail = raw_root / "adviserinfo" / "firm_detail" / "123456.json"
    firm_detail.parent.mkdir(parents=True, exist_ok=True)
    firm_detail.write_text("{}")

    refreshed_status = cache_status_for_pair(raw_root, snapshot_root, pair)

    assert refreshed_status["firm_detail_cached"] is True
    assert pair_has_complete_cache(refreshed_status) is True


def test_cache_gap_reason_prioritizes_missing_cache_layers() -> None:
    assert (
        cache_gap_reason(
            {
                "firm_detail_cached": False,
                "current_brochure_pdf_cached": False,
                "prior_brochure_pdf_cached": False,
                "current_text_snapshot_cached": False,
                "prior_text_snapshot_cached": False,
                "current_brochure_cache_available": False,
                "prior_brochure_cache_available": False,
            }
        )
        == "missing_firm_detail_cache"
    )
    assert (
        cache_gap_reason(
            {
                "firm_detail_cached": True,
                "current_brochure_pdf_cached": False,
                "prior_brochure_pdf_cached": True,
                "current_text_snapshot_cached": False,
                "prior_text_snapshot_cached": False,
                "current_brochure_cache_available": False,
                "prior_brochure_cache_available": True,
            }
        )
        == "missing_current_brochure_cache"
    )
    assert (
        cache_gap_reason(
            {
                "firm_detail_cached": True,
                "current_brochure_pdf_cached": True,
                "prior_brochure_pdf_cached": False,
                "current_text_snapshot_cached": False,
                "prior_text_snapshot_cached": False,
                "current_brochure_cache_available": True,
                "prior_brochure_cache_available": False,
            }
        )
        == "missing_prior_brochure_cache"
    )


def test_refresh_action_for_reason_maps_actionable_cache_gaps() -> None:
    assert refresh_action_for_reason("missing_firm_detail_cache") == "fetch_firm_detail"
    assert refresh_action_for_reason("missing_current_brochure_cache") == "cache_current_brochure"
    assert refresh_action_for_reason("missing_prior_brochure_cache") == "cache_prior_brochure"
    assert refresh_action_for_reason("selection_window_limit") is None


def test_next_refresh_targets_groups_and_limits_actionable_queue() -> None:
    pair_a = make_pair("123456")
    pair_b = make_pair("223456")
    pair_c = make_pair("323456")
    missing_detail_status = {
        "firm_detail_cached": False,
        "current_brochure_pdf_cached": False,
        "prior_brochure_pdf_cached": False,
        "current_text_snapshot_cached": False,
        "prior_text_snapshot_cached": False,
        "current_brochure_cache_available": False,
        "prior_brochure_cache_available": False,
    }
    missing_current_status = {
        "firm_detail_cached": True,
        "current_brochure_pdf_cached": False,
        "prior_brochure_pdf_cached": True,
        "current_text_snapshot_cached": False,
        "prior_text_snapshot_cached": True,
        "current_brochure_cache_available": False,
        "prior_brochure_cache_available": True,
    }
    skipped_candidates = [
        cache_report_entry(
            pair_a,
            cache_status=missing_detail_status,
            skip_stage="selection",
            skip_reason="missing_firm_detail_cache",
        ),
        cache_report_entry(
            pair_b,
            cache_status=missing_detail_status,
            skip_stage="selection",
            skip_reason="missing_firm_detail_cache",
        ),
        cache_report_entry(
            pair_c,
            cache_status=missing_current_status,
            skip_stage="selection",
            skip_reason="missing_current_brochure_cache",
        ),
        cache_report_entry(
            pair_c,
            cache_status=missing_current_status,
            skip_stage="selection",
            skip_reason="selection_window_limit",
        ),
    ]

    queue = next_refresh_targets(skipped_candidates, queue_limit_per_reason=1)

    assert queue["actionable_gap_total"] == 3
    assert queue["queue_limit_per_reason"] == 1
    assert [group["skip_reason"] for group in queue["groups"]] == [
        "missing_firm_detail_cache",
        "missing_current_brochure_cache",
    ]
    assert queue["groups"][0]["refresh_action"] == "fetch_firm_detail"
    assert queue["groups"][0]["candidate_count"] == 2
    assert len(queue["groups"][0]["targets"]) == 1
    assert queue["groups"][1]["refresh_action"] == "cache_current_brochure"
    assert queue["groups"][1]["candidate_count"] == 1


def test_selection_priority_prefers_evaluation_ready_pairs() -> None:
    complete_pair = make_pair("123456")
    more_recent_incomplete_pair = make_pair("223456")
    more_recent_incomplete_pair["current_member"] = parse_brochure_member(
        ZipMember(
            archive_url=more_recent_incomplete_pair["current_archive"].url,
            file_name="223456_1_1_20260301.pdf",
            compressed_size=10,
            uncompressed_size=10,
            compression_method=0,
            crc32=0,
            local_header_offset=0,
        )
    )
    assert more_recent_incomplete_pair["current_member"] is not None

    complete_status = {
        "firm_detail_cached": True,
        "current_brochure_pdf_cached": True,
        "prior_brochure_pdf_cached": True,
        "current_text_snapshot_cached": False,
        "prior_text_snapshot_cached": False,
        "current_brochure_cache_available": True,
        "prior_brochure_cache_available": True,
    }
    incomplete_status = {
        "firm_detail_cached": True,
        "current_brochure_pdf_cached": False,
        "prior_brochure_pdf_cached": True,
        "current_text_snapshot_cached": False,
        "prior_text_snapshot_cached": False,
        "current_brochure_cache_available": False,
        "prior_brochure_cache_available": True,
    }

    assert selection_priority_tuple(complete_pair, complete_status) > selection_priority_tuple(
        more_recent_incomplete_pair, incomplete_status
    )


def test_build_cache_report_summarizes_skip_reasons() -> None:
    pair = make_pair("123456")
    detail = {"basicInformation": {"firmName": "Example Wealth", "iaSECNumber": "801-123456"}}
    cache_status = {
        "firm_detail_cached": False,
        "current_brochure_pdf_cached": False,
        "prior_brochure_pdf_cached": True,
        "current_text_snapshot_cached": False,
        "prior_text_snapshot_cached": False,
        "current_brochure_cache_available": False,
        "prior_brochure_cache_available": True,
    }
    skipped_candidates = [
        cache_report_entry(
            pair,
            cache_status=cache_status,
            skip_stage="selection",
            skip_reason="missing_firm_detail_cache",
        ),
        cache_report_entry(
            pair,
            cache_status=cache_status,
            skip_stage="brochure",
            skip_reason="missing_current_brochure_cache",
            detail=detail,
        ),
    ]

    report = build_cache_report(
        source_version="first-slice-v1",
        cache_only=True,
        prior_brochure_archive=pair["prior_archive"],
        latest_brochure_archive=pair["current_archive"],
        candidate_pairs_total=3,
        selection_limit=20,
        shortlist_limit=5,
        selected_pairs_total=1,
        shortlisted_total=1,
        cache_complete_pairs_total=1,
        skipped_candidates=skipped_candidates,
    )

    assert report["mode"] == "cache_only"
    assert report["summary"]["candidate_pairs_total"] == 3
    assert report["summary"]["cache_complete_pairs_total"] == 1
    assert report["summary"]["skipped_candidates_total"] == 2
    assert report["summary"]["skipped_by_reason"]["missing_firm_detail_cache"] == 1
    assert report["summary"]["skipped_by_reason"]["missing_current_brochure_cache"] == 1
    assert report["summary"]["skipped_by_stage"]["selection"] == 1
    assert report["summary"]["skipped_by_stage"]["brochure"] == 1
    assert report["next_refresh_targets"]["actionable_gap_total"] == 2
    assert report["next_refresh_targets"]["groups"][0]["refresh_action"] == "fetch_firm_detail"
    assert report["skipped_candidates"][1]["firm_name"] == "Example Wealth"


def test_build_selection_window_artifact_enriches_cached_detail(tmp_path) -> None:
    pair = make_pair("123456")
    raw_root = tmp_path / "raw"
    detail_path = raw_root / "adviserinfo" / "firm_detail" / "123456.json"
    detail_path.parent.mkdir(parents=True, exist_ok=True)
    detail_path.write_text(
        '{"hits": {"hits": [{"_source": {"iacontent": "{\\"basicInformation\\": {\\"firmName\\": \\"Example Wealth\\", \\"iaSECNumber\\": \\"801-123456\\", \\"iaScope\\": \\"ACTIVE\\"}}"}}]}}'
    )

    cache_status = {
        "firm_detail_cached": True,
        "current_brochure_pdf_cached": True,
        "prior_brochure_pdf_cached": True,
        "current_text_snapshot_cached": False,
        "prior_text_snapshot_cached": False,
        "current_brochure_cache_available": True,
        "prior_brochure_cache_available": True,
    }
    skipped_candidates = [
        cache_report_entry(
            pair,
            cache_status=cache_status,
            skip_stage="selection",
            skip_reason="selection_window_limit",
        )
    ]

    artifact = build_selection_window_artifact(
        source_version="first-slice-v1",
        selection_limit=20,
        selected_pairs_total=20,
        shortlisted_total=5,
        raw_root=raw_root,
        skipped_candidates=skipped_candidates,
    )

    assert artifact["selection_limit"] == 20
    assert artifact["selected_pairs_total"] == 20
    assert artifact["shortlisted_total"] == 5
    assert artifact["deferred_candidates_total"] == 1
    assert artifact["deferred_candidates_with_detail_cache"] == 1
    assert artifact["deferred_candidates"][0]["selection_position"] == 21
    assert artifact["deferred_candidates"][0]["firm_name"] == "Example Wealth"
    assert artifact["deferred_candidates"][0]["ia_scope"] == "ACTIVE"
    assert artifact["deferred_candidates"][0]["detail_cache_available"] is True
