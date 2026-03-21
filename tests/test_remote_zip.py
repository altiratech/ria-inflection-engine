from __future__ import annotations

from io import BytesIO
import zipfile

from pipeline.remote_zip import parse_central_directory, parse_end_of_central_directory


def build_archive_bytes() -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("105849_423900_1_20260228.pdf", b"alpha")
        archive.writestr("notes.txt", b"beta")
    return buffer.getvalue()


def test_parse_central_directory_reads_member_names() -> None:
    archive_bytes = build_archive_bytes()
    tail_bytes = archive_bytes[-70000:]
    directory_size, directory_offset = parse_end_of_central_directory(tail_bytes)
    members = parse_central_directory(
        archive_bytes[directory_offset : directory_offset + directory_size],
        archive_url="https://example.com/archive.zip",
    )

    assert [member.file_name for member in members] == ["105849_423900_1_20260228.pdf", "notes.txt"]
    assert members[0].archive_url == "https://example.com/archive.zip"
