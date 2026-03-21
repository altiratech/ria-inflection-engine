from __future__ import annotations

from dataclasses import dataclass
import io
from pathlib import Path
import re

from pypdf import PdfReader

from pipeline.remote_zip import ZipMember


BROCHURE_FILE_PATTERN = re.compile(r"^(?P<firm_id>\d+)_(?P<version_id>\d+)_(?P<sequence>\d+)_(?P<submitted>\d{8})\.pdf$")


@dataclass(frozen=True)
class BrochureArchiveMember:
    firm_id: str
    version_id: str
    sequence: int
    submitted_at: str
    member: ZipMember


def parse_brochure_member(member: ZipMember) -> BrochureArchiveMember | None:
    match = BROCHURE_FILE_PATTERN.match(member.file_name)
    if not match:
        return None
    return BrochureArchiveMember(
        firm_id=match.group("firm_id"),
        version_id=match.group("version_id"),
        sequence=int(match.group("sequence")),
        submitted_at=match.group("submitted"),
        member=member,
    )


def extract_pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes), strict=False)
    pages: list[str] = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)


def snapshot_text(pdf_bytes: bytes, destination: Path) -> str:
    if destination.exists():
        return destination.read_text()
    destination.parent.mkdir(parents=True, exist_ok=True)
    text = extract_pdf_text(pdf_bytes)
    destination.write_text(text)
    return text


def brochure_type(text: str) -> str:
    lowered = text.lower()
    if "brochure supplement" in lowered or "part 2b" in lowered:
        return "part_2b"
    return "part_2a"
