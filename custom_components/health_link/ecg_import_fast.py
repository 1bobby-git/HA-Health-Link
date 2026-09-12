"""Fast ECG-only import path for real Apple Health export ZIPs.

The full Apple Health export can expand to well over a gigabyte even when the
ECG payload is only a few hundred kilobytes. In ECG-only mode we validate the
archive container globally but apply expanded-size limits only to eligible ECG
members. This avoids parsing or sizing unrelated export XML/GPX payloads.
"""
from __future__ import annotations

import csv
import io
from pathlib import Path, PurePosixPath
import re
from typing import BinaryIO, Iterator
import zipfile

from .health_import import (
    HealthImportError,
    MAX_ECG_POINTS,
    MAX_FILE_BYTES,
    _NUMBER,
    ecg_record,
    finite,
    read_file as read_health_file,
)

MAX_ECG_ARCHIVE_BYTES = 128 * 1024 * 1024
MAX_ECG_FILES = 5000

# Apple localizes ECG export metadata. Only structural metadata keys are
# recognized; patient name/date-of-birth lines are intentionally ignored.
_ECG_KEYS = {
    "recorded date": "recorded date",
    "기록된 날짜": "recorded date",
    "sample rate": "sample rate",
    "샘플률": "sample rate",
    "샘플 레이트": "sample rate",
    "샘플링 주파수": "sample rate",
    "classification": "classification",
    "분류": "classification",
    "symptoms": "symptoms",
    "증상": "symptoms",
    "device": "device",
    "기기": "device",
    "lead": "lead",
    "유도": "lead",
    "unit": "unit",
    "단위": "unit",
}

_RATE = re.compile(r"([\d.]+)\s*(?:hertz|hz|헤르츠)?", re.I)


def ecg_csv_localized(stream: BinaryIO) -> list[dict]:
    """Parse English or Korean Apple single-lead ECG CSV exports."""
    text = io.TextIOWrapper(stream, encoding="utf-8-sig", newline="")
    metadata: dict[str, str] = {}
    values: list[float] = []
    in_values = False
    try:
        for raw_line in text:
            line = raw_line.strip()
            if not line:
                continue
            if in_values or (_NUMBER.fullmatch(line) and "unit" in metadata):
                in_values = True
                if not _NUMBER.fullmatch(line):
                    raise HealthImportError("unsupported_ecg_csv")
                values.append(finite(line.replace(",", ".")))
                if len(values) > MAX_ECG_POINTS:
                    raise HealthImportError("too_many_ecg_points")
                continue

            parts = next(csv.reader([line]))
            if len(parts) < 2:
                raise HealthImportError("unsupported_ecg_csv")
            key = _ECG_KEYS.get(parts[0].strip().lower())
            if key:
                metadata[key] = ",".join(parts[1:]).strip()

        rate = _RATE.fullmatch(metadata.get("sample rate", ""))
        if not values or rate is None or not metadata.get("recorded date"):
            raise HealthImportError("unsupported_ecg_csv")
        return ecg_record({
            "start": metadata["recorded date"],
            "samplingFrequency": rate.group(1),
            "classification": metadata.get("classification"),
            "symptoms": metadata.get("symptoms"),
            "source": metadata.get("device", "Apple Health ECG export"),
            "lead": metadata.get("lead"),
            "voltage_unit": metadata.get("unit"),
            "points": [{"voltage": value} for value in values],
        })
    finally:
        text.detach()


def _safe_member(member: zipfile.ZipInfo) -> PurePosixPath:
    name = PurePosixPath(member.filename)
    if name.is_absolute() or ".." in name.parts or "\\" in member.filename or member.flag_bits & 1:
        raise HealthImportError("unsafe_archive")
    return name


def read_ecg_only(path: Path) -> Iterator[dict]:
    """Read only ECG payloads without expanding/scanning huge health XML files."""
    if path.stat().st_size > MAX_FILE_BYTES:
        raise HealthImportError("file_too_large")

    suffix = path.suffix.lower()
    if suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            if len(members) > 10000:
                raise HealthImportError("archive_too_large")

            eligible: list[tuple[zipfile.ZipInfo, PurePosixPath]] = []
            for member in members:
                name = _safe_member(member)
                if (
                    not member.is_dir()
                    and name.suffix.lower() == ".csv"
                    and "electrocardiograms" in {part.lower() for part in name.parts}
                ):
                    eligible.append((member, name))

            if not eligible:
                raise HealthImportError("no_ecg_in_archive")
            if len(eligible) > MAX_ECG_FILES:
                raise HealthImportError("too_many_ecg_files")
            if sum(member.file_size for member, _ in eligible) > MAX_ECG_ARCHIVE_BYTES:
                raise HealthImportError("ecg_archive_too_large")

            for member, _ in eligible:
                if member.file_size > max(1024 * 1024, member.compress_size * 2000):
                    raise HealthImportError("archive_too_large")
                with archive.open(member) as stream:
                    yield from ecg_csv_localized(stream)
        return

    if suffix == ".csv":
        with path.open("rb") as stream:
            yield from ecg_csv_localized(stream)
        return

    # JSON ECG input keeps the existing strict parser. XML is not an ECG source.
    if suffix == ".xml":
        raise HealthImportError("no_ecg_in_xml")
    yield from read_health_file(path, "ecg")


def read_file(path: Path, scope: str = "all") -> Iterator[dict]:
    """Use the fast localized ECG path only when the user selected ECG-only."""
    if scope == "ecg":
        yield from read_ecg_only(path)
        return
    yield from read_health_file(path, scope)
