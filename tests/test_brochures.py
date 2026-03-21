from __future__ import annotations

import pytest

from pipeline.brochures import ensure_text_snapshot, snapshot_text
from pipeline.remote_zip import ZipMember


def test_snapshot_text_uses_existing_snapshot_without_pdf_source(tmp_path, monkeypatch) -> None:
    snapshot_path = tmp_path / "brochure.txt"
    snapshot_path.write_text("cached brochure text")

    def fail_extract(_pdf_bytes: bytes) -> str:
        raise AssertionError("cached snapshot reads should not attempt PDF extraction")

    monkeypatch.setattr("pipeline.brochures.extract_pdf_text", fail_extract)

    assert snapshot_text(None, snapshot_path) == "cached brochure text"


def test_snapshot_text_requires_pdf_source_when_snapshot_missing(tmp_path) -> None:
    with pytest.raises(ValueError, match="requires PDF bytes or a cached source PDF path"):
        snapshot_text(None, tmp_path / "missing.txt")


def test_ensure_text_snapshot_skips_existing_snapshot(tmp_path, monkeypatch) -> None:
    snapshot_path = tmp_path / "brochure.txt"
    snapshot_path.write_text("cached brochure text")

    def fail_write_cache(*_args, **_kwargs):
        raise AssertionError("existing snapshots should not touch the PDF cache")

    monkeypatch.setattr("pipeline.brochures.write_member_cache", fail_write_cache)

    member = ZipMember(
        archive_url="https://example.com/archive.zip",
        file_name="123456_1_1_20260131.pdf",
        compressed_size=10,
        uncompressed_size=10,
        compression_method=0,
        crc32=0,
        local_header_offset=0,
    )

    assert (
        ensure_text_snapshot(
            member,
            tmp_path / "brochure.pdf",
            snapshot_path,
            user_agent="test-agent",
            allow_download=False,
        )
        is False
    )


def test_ensure_text_snapshot_backfills_missing_snapshot(tmp_path, monkeypatch) -> None:
    pdf_path = tmp_path / "brochure.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    snapshot_path = tmp_path / "brochure.txt"

    def fake_write_cache(member, destination, *, user_agent: str, allow_download: bool):
        assert member.file_name == "123456_1_1_20260131.pdf"
        assert destination == pdf_path
        assert user_agent == "test-agent"
        assert allow_download is False
        return destination

    def fake_snapshot_text(_pdf_bytes, destination, *, source_pdf_path=None):
        assert source_pdf_path == pdf_path
        destination.write_text("fresh brochure text")
        return "fresh brochure text"

    monkeypatch.setattr("pipeline.brochures.write_member_cache", fake_write_cache)
    monkeypatch.setattr("pipeline.brochures.snapshot_text", fake_snapshot_text)

    member = ZipMember(
        archive_url="https://example.com/archive.zip",
        file_name="123456_1_1_20260131.pdf",
        compressed_size=10,
        uncompressed_size=10,
        compression_method=0,
        crc32=0,
        local_header_offset=0,
    )

    assert (
        ensure_text_snapshot(
            member,
            pdf_path,
            snapshot_path,
            user_agent="test-agent",
            allow_download=False,
        )
        is True
    )
    assert snapshot_path.read_text() == "fresh brochure text"
