from __future__ import annotations

import pytest

from pipeline.iapd import download_file, fetch_json


def test_fetch_json_cache_only_requires_existing_cache(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="Missing cached JSON payload"):
        fetch_json("https://example.com/payload.json", tmp_path / "missing.json", allow_download=False)


def test_download_file_cache_only_requires_existing_cache(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="Missing cached file payload"):
        download_file("https://example.com/file.zip", tmp_path / "missing.zip", allow_download=False)
