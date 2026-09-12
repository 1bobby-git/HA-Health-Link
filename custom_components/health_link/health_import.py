"""Bounded, offline parsers for Apple Health exports and ECG records.

Imported samples have a separate namespace: a HealthKit raw interval must never
be added to a Companion daily total. No diagnoses or missing values are invented.
"""
from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import re
from typing import Any, BinaryIO, Iterator
import zipfile

from defusedxml import ElementTree as SafeET

ECG_TYPE = "apple_export.ecg"
MAX_FILE_BYTES = 100 * 1024 * 1024
MAX_EXPANDED_BYTES = 512 * 1024 * 1024
MAX_JSON_BYTES = 32 * 1024 * 1024
MAX_RECORDS = 1_000_000
MAX_ECG_POINTS = 120_000
MAX_TOTAL_POINTS = 2_000_000
_TYPE = re.compile(r"^HK(?:QuantityTypeIdentifier|CategoryTypeIdentifier)[A-Za-z0-9_]{1,160}$")
_NUMBER = re.compile(r"^[+-]?(?:\d+(?:[.,]\d*)?|[.,]\d+)(?:[eE][+-]?\d+)?$")


class HealthImportError(ValueError):
    """A safe error code, never an excerpt of private health data."""


def finite(value: Any) -> float:
    if isinstance(value, bool):
        raise HealthImportError("invalid_number")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as err:
        raise HealthImportError("invalid_number") from err
    if not math.isfinite(number):
        raise HealthImportError("invalid_number")
    return number


def timestamp(value: Any) -> str:
    try:
        stamp = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    except (TypeError, ValueError) as err:
        raise HealthImportError("invalid_timestamp") from err
    if stamp.tzinfo is None:
        raise HealthImportError("timezone_required")
    return stamp.astimezone(timezone.utc).isoformat()


def _text(value: Any, limit: int = 255) -> str:
    text = str(value or "").strip()
    if len(text) > limit:
        raise HealthImportError("field_too_long")
    return text


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def type_details(type_id: str) -> tuple[str, str]:
    """Unknown types are sensitive until deliberately permitted."""
    if any(word in type_id for word in ("Blood", "Insulin", "Temperature", "Sexual", "Menstrual",
                                        "Ovulation", "Pregnan", "Contracept", "StateOfMind", "Symptom")):
        return "vitals", "sensitive"
    for group, words in (
        ("sleep", ("SleepAnalysis",)),
        ("activity", ("StepCount", "Distance", "FlightsClimbed", "EnergyBurned", "ExerciseTime", "StandTime", "VO2Max")),
        ("body", ("BodyMass", "BodyFatPercentage", "LeanBodyMass", "Height")),
        ("heart", ("HeartRate",)),
        ("respiratory", ("RespiratoryRate",)),
        ("nutrition", ("Dietary",)),
        ("mobility", ("Walking", "Stair", "SixMinute")),
        ("hearing", ("AudioExposure", "SoundReduction")),
    ):
        if any(word in type_id for word in words):
            return group, "wellness"
    return "other", "sensitive"


def raw_record(record: dict[str, Any]) -> dict[str, Any]:
    type_id = _text(record.get("type") or record.get("type_id"))
    if not _TYPE.fullmatch(type_id):
        raise HealthImportError("unsupported_health_type")
    start = timestamp(record.get("startDate") or record.get("start"))
    end = timestamp(record.get("endDate") or record.get("end") or start)
    if end < start:
        raise HealthImportError("invalid_interval")
    source = _text(record.get("sourceName") or record.get("source") or "Imported HealthKit record")
    unit = _text(record.get("unit"), 64) or None
    domain, privacy = type_details(type_id)
    kind = "quantity" if "QuantityTypeIdentifier" in type_id else "category"
    value = finite(record.get("value")) if kind == "quantity" else _text(record.get("value"))
    # Separate source and unit series instead of silently adding different devices,
    # conflating units, or replacing a Companion aggregate with one raw interval.
    suffix = _digest([source, unit])[:12]
    name = re.sub(r"^HK(?:QuantityTypeIdentifier|CategoryTypeIdentifier)", "", type_id)
    name = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name)
    result = {
        "sample_uuid": "export:" + _digest([type_id, source, unit, start, end, value]),
        "type_id": f"apple_export.{type_id}.{suffix}", "object_kind": kind,
        "domain": domain, "privacy_class": privacy,
        "display_name": f"{name} · {source} · 원본",
        "start": start, "end": end, "unit": unit,
        "aggregation_kind": "latest", "source": {"name": source},
        "metadata": {"healthkit_type": type_id, "time_semantics": "healthkit_sample_interval",
                     "transport": "local_import", "value_semantics": "raw_export_value",
                     "healthkit_sample_timestamp_available": True},
    }
    result["numeric_value" if kind == "quantity" else "text_value"] = value
    return result


def ecg_record(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Accept documented ECG JSON plus HealthLink's explicit offset/unit format."""
    start = timestamp(record.get("start"))
    frequency_value = record.get("samplingFrequency", record.get("sampling_frequency_hz"))
    frequency = finite(frequency_value) if frequency_value is not None else None
    if frequency is not None and not 0 < frequency <= 10000:
        raise HealthImportError("invalid_sampling_frequency")
    measurements = record.get("voltageMeasurements", record.get("points", []))
    if not isinstance(measurements, list) or len(measurements) > MAX_ECG_POINTS:
        raise HealthImportError("too_many_ecg_points")
    points: list[list[float]] = []
    start_dt = datetime.fromisoformat(start)
    for index, item in enumerate(measurements):
        if not isinstance(item, dict):
            raise HealthImportError("invalid_ecg_point")
        if item.get("date") is not None:
            seconds = (datetime.fromisoformat(timestamp(item["date"])) - start_dt).total_seconds()
        elif item.get("time_since_start") is not None:
            seconds = finite(item["time_since_start"])
        elif frequency:
            seconds = index / frequency
        else:
            raise HealthImportError("point_time_required")
        unit = item.get("units", item.get("unit", record.get("voltage_unit")))
        factors = {"V": 1000.0, "mV": 1.0, "uV": 0.001, "µV": 0.001, "μV": 0.001}
        if unit not in factors:
            raise HealthImportError("voltage_unit_required")
        voltage = finite(item.get("voltage")) * factors[unit]
        if not math.isfinite(voltage) or seconds < 0 or seconds > 3600 or (points and seconds <= points[-1][0]):
            raise HealthImportError("invalid_ecg_point")
        points.append([seconds, voltage])
    count = record.get("numberOfVoltageMeasurements")
    if count is not None and (finite(count) != int(finite(count)) or int(finite(count)) != len(points)):
        raise HealthImportError("ecg_point_count_mismatch")
    if record.get("end") is not None:
        end = timestamp(record["end"])
    elif points and frequency:
        end = (start_dt + timedelta(seconds=points[-1][0] + 1 / frequency)).isoformat()
    else:
        end = start
    duration = (datetime.fromisoformat(end) - start_dt).total_seconds()
    if duration < 0 or duration > 3600 or (points and points[-1][0] > duration):
        raise HealthImportError("invalid_ecg_duration")
    heart_rate_value = record.get("averageHeartRate", record.get("average_heart_rate"))
    heart_rate = finite(heart_rate_value) if heart_rate_value is not None else None
    if heart_rate is not None and heart_rate <= 0:
        raise HealthImportError("invalid_number")
    source = _text(record.get("source") or "Apple Health ECG export")
    payload = {
        "classification": _text(record.get("classification")) or None,
        "average_heart_rate": heart_rate,
        "symptoms_status": _text(record.get("symptomsStatus", record.get("symptoms"))) or None,
        "sampling_frequency_hz": frequency, "point_count": len(points),
        "duration_seconds": duration, "voltage_unit": "mV",
        "lead": _text(record.get("lead")) or None,
        "classification_origin": "source_record", "medical_diagnosis": False,
    }
    identifier = "ecg:" + _digest([source, start, end, payload, points])
    obj = {
        "sample_uuid": identifier, "type_id": ECG_TYPE, "object_kind": "ecg",
        "domain": "heart", "privacy_class": "sensitive", "display_name": "심전도 원본 기록",
        "start": start, "end": end, "payload": payload, "source": {"name": source},
        "metadata": {"time_semantics": "healthkit_sample_interval", "transport": "local_import",
                     "end_inferred_from_sampling": record.get("end") is None,
                     "healthkit_sample_timestamp_available": True},
    }
    output = [obj]
    for offset in range(0, len(points), 512):
        chunk = points[offset:offset + 512]
        output.append({
            "type_id": ECG_TYPE, "object_kind": "series_chunk", "series_kind": "ecg",
            "series_uuid": identifier, "chunk_index": offset // 512,
            "domain": "heart", "privacy_class": "sensitive", "display_name": "심전도 원본 기록",
            "start": start, "end": end, "points": chunk,
        })
    return output


def ecg_csv(stream: BinaryIO) -> list[dict[str, Any]]:
    """Read Apple-export style single-lead CSV; never guess absent units."""
    text = io.TextIOWrapper(stream, encoding="utf-8-sig", newline="")
    metadata: dict[str, str] = {}
    values: list[float] = []
    in_values = False
    try:
        for line in text:
            line = line.strip()
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
            key = parts[0].strip().lower()
            if key in {"recorded date", "sample rate", "classification", "symptoms", "device", "lead", "unit"}:
                metadata[key] = ",".join(parts[1:]).strip()
        rate = re.fullmatch(r"([\d.]+)\s*(?:hertz|hz)?", metadata.get("sample rate", ""), re.I)
        if not values or rate is None or not metadata.get("recorded date"):
            raise HealthImportError("unsupported_ecg_csv")
        return ecg_record({"start": metadata["recorded date"], "samplingFrequency": rate[1],
                           "classification": metadata.get("classification"), "symptoms": metadata.get("symptoms"),
                           "source": metadata.get("device", "Apple Health ECG export"), "lead": metadata.get("lead"),
                           "voltage_unit": metadata.get("unit"), "points": [{"voltage": v} for v in values]})
    finally:
        text.detach()


def _xml_records(stream: BinaryIO) -> Iterator[dict[str, Any]]:
    root = None
    depth = 0
    count = 0
    for event, element in SafeET.iterparse(stream, events=("start", "end"),
                                          forbid_entities=True, forbid_external=True):
        if event == "start":
            depth += 1
            if root is None:
                root = element
                if element.tag != "HealthData":
                    raise HealthImportError("unsupported_xml")
            if depth > 32:
                raise HealthImportError("xml_too_deep")
            continue
        if depth == 2 and element.tag == "Record":
            count += 1
            if count > MAX_RECORDS:
                raise HealthImportError("too_many_records")
            if _TYPE.fullmatch(element.get("type", "")):
                yield raw_record(dict(element.attrib))
            else:
                yield {"_skip": "unsupported_health_type"}
        elif depth == 2 and element.tag == "Workout":
            attrs = {key: _text(value, 512) for key, value in element.attrib.items()}
            start = timestamp(attrs.get("startDate")); end = timestamp(attrs.get("endDate"))
            if end < start:
                raise HealthImportError("invalid_interval")
            yield {"sample_uuid": "workout:" + _digest(attrs), "type_id": "apple_export.workout",
                   "object_kind": "workout", "domain": "workout", "privacy_class": "wellness",
                   "display_name": "운동 원본 기록", "start": start, "end": end, "payload": attrs,
                   "source": {"name": attrs.get("sourceName", "Apple Health export")},
                   "metadata": {"time_semantics": "healthkit_sample_interval", "transport": "local_import"}}
        if depth == 2 and root is not None:
            root.clear()
        depth -= 1


def json_records(value: Any) -> Iterator[dict[str, Any]]:
    """HealthLink records envelope, single ECG, ECG list, or data.ecg envelope."""
    if isinstance(value, dict) and isinstance(value.get("data"), dict):
        value = value["data"]
    if isinstance(value, dict) and ("ecg" in value or "records" in value):
        if set(value) - {"ecg", "records", "schema_version"}:
            raise HealthImportError("unsupported_json_fields")
        for key in ("records", "ecg"):
            records = value.get(key, [])
            if not isinstance(records, list):
                raise HealthImportError("unsupported_json")
            for record in records:
                if not isinstance(record, dict):
                    raise HealthImportError("unsupported_json")
                if key == "ecg":
                    yield from ecg_record(record)
                else:
                    yield raw_record(record)
        return
    if isinstance(value, list):
        for record in value:
            if not isinstance(record, dict):
                raise HealthImportError("unsupported_json")
            yield from ecg_record(record)
        return
    if isinstance(value, dict) and ("voltageMeasurements" in value or "points" in value):
        yield from ecg_record(value)
        return
    raise HealthImportError("unsupported_json")


def _read_stream(stream: BinaryIO, suffix: str) -> Iterator[dict[str, Any]]:
    if suffix == ".xml":
        yield from _xml_records(stream)
    elif suffix == ".csv":
        yield from ecg_csv(stream)
    elif suffix == ".json":
        data = stream.read(MAX_JSON_BYTES + 1)
        if len(data) > MAX_JSON_BYTES:
            raise HealthImportError("json_too_large")
        try:
            value = json.loads(data)
        except (ValueError, UnicodeError, RecursionError) as err:
            raise HealthImportError("invalid_json") from err
        yield from json_records(value)
    else:
        raise HealthImportError("unsupported_file")


def read_file(path: Path, scope: str = "all") -> Iterator[dict[str, Any]]:
    """ZIP members are read directly, never extracted to a filesystem."""
    if path.stat().st_size > MAX_FILE_BYTES:
        raise HealthImportError("file_too_large")
    if scope not in {"all", "ecg"}:
        raise HealthImportError("invalid_scope")
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            if len(members) > 10000 or sum(x.file_size for x in members) > MAX_EXPANDED_BYTES:
                raise HealthImportError("archive_too_large")
            for member in members:
                name = PurePosixPath(member.filename)
                if name.is_absolute() or ".." in name.parts or "\\" in member.filename or member.flag_bits & 1:
                    raise HealthImportError("unsafe_archive")
                if member.file_size > max(1024 * 1024, member.compress_size * 2000):
                    raise HealthImportError("archive_too_large")
                suffix = name.suffix.lower()
                eligible = (name.name == "export.xml" and scope == "all") or (
                    suffix == ".csv" and "electrocardiograms" in name.parts)
                if eligible and not member.is_dir():
                    with archive.open(member) as stream:
                        yield from _read_stream(stream, suffix)
    else:
        with path.open("rb") as stream:
            if scope == "ecg" and path.suffix.lower() == ".xml":
                raise HealthImportError("no_ecg_in_xml")
            yield from _read_stream(stream, path.suffix.lower())
