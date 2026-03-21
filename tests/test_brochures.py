from __future__ import annotations

import pytest

from pipeline.brochures import snapshot_text


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
