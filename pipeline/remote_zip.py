from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import struct
import urllib.request
import zlib


EOCD_SIGNATURE = b"PK\x05\x06"
CENTRAL_DIRECTORY_SIGNATURE = b"PK\x01\x02"
LOCAL_FILE_HEADER_SIGNATURE = b"PK\x03\x04"
TAIL_WINDOW_BYTES = 70_000


@dataclass(frozen=True)
class ZipMember:
    archive_url: str
    file_name: str
    compressed_size: int
    uncompressed_size: int
    compression_method: int
    crc32: int
    local_header_offset: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ZipMember":
        return cls(
            archive_url=str(payload["archive_url"]),
            file_name=str(payload["file_name"]),
            compressed_size=int(payload["compressed_size"]),
            uncompressed_size=int(payload["uncompressed_size"]),
            compression_method=int(payload["compression_method"]),
            crc32=int(payload["crc32"]),
            local_header_offset=int(payload["local_header_offset"]),
        )


def fetch_range_bytes(url: str, start: int | None = None, end: int | None = None, *, user_agent: str) -> bytes:
    headers = {"User-Agent": user_agent}
    if start is not None and end is not None:
        headers["Range"] = f"bytes={start}-{end}"
    elif start is None and end is not None:
        headers["Range"] = f"bytes=-{end}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def locate_end_of_central_directory(tail_bytes: bytes) -> int:
    offset = tail_bytes.rfind(EOCD_SIGNATURE)
    if offset < 0:
        raise ValueError("Could not locate end-of-central-directory record in ZIP tail.")
    return offset


def parse_end_of_central_directory(tail_bytes: bytes) -> tuple[int, int]:
    offset = locate_end_of_central_directory(tail_bytes)
    _, _, _, _, _, central_directory_size, central_directory_offset, _ = struct.unpack(
        "<4s4H2LH", tail_bytes[offset : offset + 22]
    )
    return central_directory_size, central_directory_offset


def parse_central_directory(directory_bytes: bytes, archive_url: str) -> list[ZipMember]:
    members: list[ZipMember] = []
    offset = 0
    while offset < len(directory_bytes):
        if directory_bytes[offset : offset + 4] != CENTRAL_DIRECTORY_SIGNATURE:
            break
        header = struct.unpack("<4s6H3L5H2L", directory_bytes[offset : offset + 46])
        compression_method = header[4]
        crc32 = header[7]
        compressed_size = header[8]
        uncompressed_size = header[9]
        file_name_length = header[10]
        extra_length = header[11]
        comment_length = header[12]
        local_header_offset = header[16]
        file_name = directory_bytes[offset + 46 : offset + 46 + file_name_length].decode("utf-8", "replace")
        members.append(
            ZipMember(
                archive_url=archive_url,
                file_name=file_name,
                compressed_size=compressed_size,
                uncompressed_size=uncompressed_size,
                compression_method=compression_method,
                crc32=crc32,
                local_header_offset=local_header_offset,
            )
        )
        offset += 46 + file_name_length + extra_length + comment_length
    return members


def list_zip_members(archive_url: str, *, user_agent: str, cache_path: Path | None = None) -> list[ZipMember]:
    if cache_path and cache_path.exists():
        payload = json.loads(cache_path.read_text())
        return [ZipMember.from_dict(item) for item in payload["members"]]

    tail_bytes = fetch_range_bytes(archive_url, end=TAIL_WINDOW_BYTES, user_agent=user_agent)
    central_directory_size, central_directory_offset = parse_end_of_central_directory(tail_bytes)
    central_directory_bytes = fetch_range_bytes(
        archive_url,
        start=central_directory_offset,
        end=central_directory_offset + central_directory_size - 1,
        user_agent=user_agent,
    )
    members = parse_central_directory(central_directory_bytes, archive_url)

    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(
                {"archive_url": archive_url, "member_count": len(members), "members": [member.to_dict() for member in members]},
                indent=2,
            )
        )
    return members


def read_member_bytes(member: ZipMember, *, user_agent: str) -> bytes:
    local_header = fetch_range_bytes(
        member.archive_url,
        start=member.local_header_offset,
        end=member.local_header_offset + 30 - 1,
        user_agent=user_agent,
    )
    if local_header[:4] != LOCAL_FILE_HEADER_SIGNATURE:
        raise ValueError(f"Invalid local ZIP header for {member.file_name}.")
    local_file_name_length, local_extra_length = struct.unpack("<2H", local_header[26:30])
    data_start = member.local_header_offset + 30 + local_file_name_length + local_extra_length
    compressed_bytes = fetch_range_bytes(
        member.archive_url,
        start=data_start,
        end=data_start + member.compressed_size - 1,
        user_agent=user_agent,
    )
    if member.compression_method == 0:
        return compressed_bytes
    if member.compression_method == 8:
        return zlib.decompress(compressed_bytes, -zlib.MAX_WBITS)
    raise ValueError(f"Unsupported ZIP compression method {member.compression_method} for {member.file_name}.")


def write_member_cache(member: ZipMember, destination: Path, *, user_agent: str) -> Path:
    if destination.exists():
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(read_member_bytes(member, user_agent=user_agent))
    return destination
