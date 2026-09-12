"""Profile-scoped health catalogue, atomic file import and ECG read actions."""
from __future__ import annotations

import asyncio
from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import tempfile
from time import monotonic
from typing import Any, Iterable

import voluptuous as vol

from homeassistant.components.file_upload import process_uploaded_file
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from .const import DEFAULT_EXPOSED_TYPE_IDS, DOMAIN
from .health_import import ECG_TYPE, HealthImportError, MAX_RECORDS, MAX_TOTAL_POINTS, json_records, read_file
from .profile_summary import profile_loaded

ECG_EVENT = "health_link_ecg_imported"
IMPORT_EVENT = "health_link_records_imported"


def sensitive(metric: dict[str, Any]) -> bool:
    return metric.get("privacy_class") not in {None, "wellness", "standard"} or metric.get("type_id") == ECG_TYPE


def exposable(metric: dict[str, Any]) -> bool:
    return metric.get("object_kind") in {"quantity", "category", "activity_summary"} or metric.get("type_id") == ECG_TYPE


async def exposed_types(store, options) -> list[dict[str, Any]]:
    return [item for item in await store.async_exposed_types()
            if exposable(item) and (options.get("enable_sensitive", False) or not sensitive(item))]


async def set_exposure(store, selected: Iterable[str], allowed: Iterable[str]) -> None:
    """Change only the metrics displayed in this form, leaving core summaries intact."""
    selected_set = set(selected)
    allowed_set = set(allowed) - DEFAULT_EXPOSED_TYPE_IDS
    if selected_set - allowed_set:
        raise HealthImportError("invalid_metric_selection")
    def apply() -> None:
        with closing(store._connect()) as con, con:
            con.executemany("UPDATE health_types SET exposed=? WHERE profile_id=? AND type_id=?",
                            [(int(type_id in selected_set), store.profile_id, type_id) for type_id in allowed_set])
    await store._run(apply)


def _parse_payload(row) -> dict[str, Any]:
    result = dict(row)
    payload = json.loads(result.pop("payload_json") or "{}")
    return {"object_uuid": result["object_uuid"], "start": result["start_ts"], "end": result["end_ts"],
            **{key: payload.get(key) for key in ("classification", "average_heart_rate", "symptoms_status",
                "sampling_frequency_hz", "point_count", "duration_seconds", "voltage_unit", "lead")},
            "classification_origin": "source_record", "medical_diagnosis": False}


def _ecg_records_sync(store, limit: int = 50, offset: int = 0) -> dict[str, Any]:
    with closing(store._connect()) as con:
        count = con.execute("SELECT COUNT(*) FROM structured_objects WHERE profile_id=? AND type_id=? AND deleted=0",
                            (store.profile_id, ECG_TYPE)).fetchone()[0]
        rows = con.execute("SELECT object_uuid,start_ts,end_ts,payload_json FROM structured_objects "
                           "WHERE profile_id=? AND type_id=? AND deleted=0 ORDER BY start_ts DESC,object_uuid LIMIT ? OFFSET ?",
                           (store.profile_id, ECG_TYPE, limit, offset)).fetchall()
    return {"count": count, "records": [_parse_payload(row) for row in rows],
            "next_offset": offset + len(rows) if offset + len(rows) < count else None}


async def ecg_snapshot(store, options) -> dict[str, Any]:
    if not options.get("enable_sensitive", False):
        return {}
    visible = await exposed_types(store, options)
    if not any(item["type_id"] == ECG_TYPE for item in visible):
        return {}
    result = await store._run(_ecg_records_sync, store, 1, 0)
    return {"count": result["count"], "latest": result["records"][0] if result["records"] else None}


def _waveform_sync(store, object_uuid: str, offset: int, limit: int) -> dict[str, Any]:
    with closing(store._connect()) as con:
        parent = con.execute("SELECT object_uuid,start_ts,end_ts,payload_json FROM structured_objects "
                             "WHERE profile_id=? AND type_id=? AND object_uuid=? AND deleted=0",
                             (store.profile_id, ECG_TYPE, object_uuid)).fetchone()
        if parent is None:
            raise HealthImportError("ecg_not_found")
        summary = _parse_payload(parent)
        rows = con.execute("SELECT chunk_index,payload_json FROM series_chunks WHERE profile_id=? AND series_uuid=? "
                           "AND chunk_index>=? AND chunk_index<=? ORDER BY chunk_index",
                           (store.profile_id, object_uuid, offset // 512, (offset + limit - 1) // 512)).fetchall()
        points = []
        for row in rows:
            values = json.loads(row["payload_json"])
            for index, value in enumerate(values):
                position = row["chunk_index"] * 512 + index
                if offset <= position < offset + limit:
                    points.append(value)
    count = int(summary.get("point_count") or 0)
    return {"object_uuid": object_uuid, "start": summary["start"], "offset": offset,
            "time_unit": "seconds_since_start", "voltage_unit": "mV", "points": points,
            "total_points": count, "next_offset": offset + len(points) if offset + len(points) < count else None,
            "medical_diagnosis": False}


def _import_sync(store, records, include_sensitive: bool, scope: str) -> dict[str, Any]:
    """Validate to temporary SQLite, then commit in ONE live-store transaction.

    Parsing errors cannot leave a half-imported profile. The staging database is
    removed on success/failure; no uploaded file, waveform or name is published.
    Temporary staging deliberately disables its own durability journal because the
    staging database is disposable; the live HealthLink transaction remains atomic.
    """
    skipped_sensitive = skipped_unsupported = total_points = visited = 0
    with tempfile.TemporaryDirectory(prefix="healthlink-import-") as directory:
        stage_path = Path(directory) / "stage.db"
        with closing(sqlite3.connect(stage_path)) as stage:
            stage.executescript(
                "PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF; PRAGMA temp_store=MEMORY;"
                "CREATE TABLE records(identity TEXT PRIMARY KEY,kind TEXT,payload TEXT);"
            )
            batch: list[tuple[str, str, str]] = []

            def flush_batch() -> None:
                if batch:
                    stage.executemany("INSERT OR IGNORE INTO records VALUES(?,?,?)", batch)
                    batch.clear()

            for item in records:
                visited += 1
                if visited > MAX_RECORDS:
                    raise HealthImportError("too_many_records")
                if item.get("_skip"):
                    skipped_unsupported += 1
                    continue
                if scope == "ecg" and item.get("type_id") != ECG_TYPE:
                    skipped_unsupported += 1
                    continue
                if sensitive(item) and not include_sensitive:
                    if item.get("object_kind") != "series_chunk":
                        skipped_sensitive += 1
                    continue
                if item.get("object_kind") == "series_chunk":
                    total_points += len(item["points"])
                    if total_points > MAX_TOTAL_POINTS:
                        raise HealthImportError("too_many_ecg_points")
                    identity = f"series:{item['series_uuid']}:{item['chunk_index']}"
                else:
                    identity = item["sample_uuid"]
                encoded = json.dumps(item, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
                batch.append((identity, item["object_kind"], encoded))
                if len(batch) >= 1000:
                    flush_batch()
            flush_batch()
            stage.commit()
            count = stage.execute("SELECT COUNT(*) FROM records").fetchone()[0]
            if not count:
                return {"inserted": 0, "updated": 0, "skipped_sensitive": skipped_sensitive,
                        "skipped_unsupported": skipped_unsupported, "ecg_new": 0, "empty": True,
                        "records_scanned": visited, "ecg_points": total_points}
            kinds = dict(stage.execute("SELECT kind,COUNT(*) FROM records GROUP BY kind"))
            new_ecgs = []
            with closing(store._connect()) as current:
                for (identity,) in stage.execute("SELECT identity FROM records WHERE kind='ecg'"):
                    if current.execute("SELECT 1 FROM structured_objects WHERE profile_id=? AND object_uuid=? AND deleted=0",
                                       (store.profile_id, identity)).fetchone() is None:
                        new_ecgs.append(identity)
            def items():
                # Metadata is last so series chunks cannot turn the ECG catalogue
                # entry into a series_chunk entity.
                for (raw,) in stage.execute("SELECT payload FROM records ORDER BY CASE WHEN kind='ecg' THEN 1 ELSE 0 END,identity"):
                    yield json.loads(raw)
            result = store._ingest_sync(items(), None, update_sync=False)
            result.update({"skipped_sensitive": skipped_sensitive, "skipped_unsupported": skipped_unsupported,
                           "ecg_new": len(new_ecgs), "ecg_records": kinds.get("ecg", 0),
                           "quantity_records": kinds.get("quantity", 0), "category_records": kinds.get("category", 0),
                           "workout_records": kinds.get("workout", 0), "empty": False,
                           "records_scanned": visited, "ecg_points": total_points})
            with closing(store._connect()) as con, con:
                con.execute("INSERT INTO meta(profile_id,key,value) VALUES(?,?,?) ON CONFLICT(profile_id,key) DO UPDATE SET value=excluded.value",
                            (store.profile_id, "last_import_result", json.dumps(result)))
            return result


async def _finish_worker(future):
    """Keep the import lock until a non-cancellable executor job has finished."""
    try:
        return await asyncio.shield(future)
    except asyncio.CancelledError:
        while not future.done():
            try:
                await asyncio.shield(future)
            except asyncio.CancelledError:
                continue
            except Exception:
                break
        if future.done() and not future.cancelled():
            # Consume a worker error without replacing the caller cancellation.
            future.exception()
        raise


async def import_uploaded(hass: HomeAssistant, entry, file_id: str, *, include_sensitive: bool = False,
                          scope: str = "all") -> dict[str, Any]:
    if not profile_loaded(entry):
        raise HealthImportError("profile_unavailable")
    if include_sensitive and not entry.options.get("enable_sensitive", False):
        raise HealthImportError("sensitive_disabled")
    locks = hass.data.setdefault(DOMAIN, {}).setdefault("import_locks", {})
    lock = locks.setdefault(entry.entry_id, asyncio.Lock())
    if lock.locked():
        raise HealthImportError("import_in_progress")
    store = entry.runtime_data.store
    started = monotonic()
    def process():
        with process_uploaded_file(hass, file_id) as path:
            return _import_sync(store, read_file(path, scope), include_sensitive, scope)
    async with lock:
        try:
            result = await _finish_worker(hass.async_add_executor_job(process))
        except HealthImportError:
            raise
        except Exception as err:
            # Never return filenames, XML fragments or original medical data in errors.
            raise HealthImportError("invalid_import_file") from err
    result["scope"] = scope
    result["elapsed_seconds"] = round(monotonic() - started, 1)
    await store.async_audit("import_health_file", object_type=f"local_file:{scope}")
    await entry.runtime_data.coordinator.async_refresh_from_store()
    hass.bus.async_fire(IMPORT_EVENT, {"config_entry_id": entry.entry_id, **result})
    if result["ecg_new"]:
        hass.bus.async_fire(ECG_EVENT, {"config_entry_id": entry.entry_id, "new_records": result["ecg_new"],
                                      "historical_import": True})
    return result


async def _admin_entry(hass: HomeAssistant, call: ServiceCall):
    if call.context.user_id:
        user = await hass.auth.async_get_user(call.context.user_id)
        if user is None or not user.is_admin:
            raise HomeAssistantError("Administrator permission is required")
    entries = [entry for entry in hass.config_entries.async_entries(DOMAIN) if profile_loaded(entry)]
    wanted = call.data.get("config_entry_id")
    entry = next((item for item in entries if item.entry_id == wanted), None) if wanted else (entries[0] if len(entries) == 1 else None)
    if entry is None:
        raise ServiceValidationError("Select a loaded HealthLink profile")
    return entry


def register_data_services(hass: HomeAssistant) -> None:
    """Native HA actions; no public upload endpoint or separate iOS app."""
    async def handle(call: ServiceCall):
        entry = await _admin_entry(hass, call)
        store = entry.runtime_data.store
        try:
            if call.service == "list_available_metrics":
                catalog = await store.async_catalog()
                return {"profile": entry.title, "metrics": [
                    {**item, "can_expose": exposable(item),
                     "sensitive_permission_required": sensitive(item) and not entry.options.get("enable_sensitive", False)}
                    for item in catalog], "labs_reads_ecg": False}
            if call.service == "import_health_file":
                if not call.data.get("confirm_profile"):
                    raise HealthImportError("confirm_profile_required")
                return await import_uploaded(hass, entry, call.data["file_id"],
                    include_sensitive=call.data.get("include_sensitive", False), scope=call.data.get("scope", "all"))
            if call.service == "import_health_samples":
                if not call.data.get("confirm_profile"):
                    raise HealthImportError("confirm_profile_required")
                data = call.data["data"]
                if len(json.dumps(data, ensure_ascii=False).encode()) > 2 * 1024 * 1024:
                    raise HealthImportError("json_too_large")
                include = call.data.get("include_sensitive", False)
                if include and not entry.options.get("enable_sensitive", False):
                    raise HealthImportError("sensitive_disabled")
                locks = hass.data.setdefault(DOMAIN, {}).setdefault("import_locks", {})
                lock = locks.setdefault(entry.entry_id, asyncio.Lock())
                if lock.locked():
                    raise HealthImportError("import_in_progress")
                async with lock:
                    result = await _finish_worker(hass.async_add_executor_job(_import_sync, store, json_records(data), include, "all"))
                await store.async_audit("import_health_samples", actor=call.context.user_id or "system")
                await entry.runtime_data.coordinator.async_refresh_from_store()
                hass.bus.async_fire(IMPORT_EVENT, {"config_entry_id": entry.entry_id, **result})
                if result["ecg_new"]:
                    hass.bus.async_fire(ECG_EVENT, {"config_entry_id": entry.entry_id, "new_records": result["ecg_new"], "historical_import": True})
                return result
            if not entry.options.get("enable_sensitive", False):
                raise HealthImportError("sensitive_disabled")
            if call.service == "get_ecg_records":
                return await store._run(_ecg_records_sync, store, call.data["limit"], call.data["offset"])
            if call.service == "get_ecg_waveform":
                return await store._run(_waveform_sync, store, call.data["object_uuid"], call.data["offset"], call.data["limit"])
            record = await store.async_structured_object(call.data["object_uuid"])
            if record is None or record.get("type_id") != ECG_TYPE:
                raise HealthImportError("ecg_not_found")
            return record
        except (HealthImportError, ValueError, TypeError, RecursionError) as err:
            message = str(err) if isinstance(err, HealthImportError) else "invalid_import_data"
            raise ServiceValidationError(message) from err

    profile = {vol.Optional("config_entry_id"): str}
    offset = {vol.Optional("offset", default=0): vol.All(vol.Coerce(int), vol.Range(min=0, max=1_000_000))}
    schema = {
        "list_available_metrics": profile,
        "import_health_file": {**profile, vol.Required("file_id"): str,
            vol.Required("confirm_profile"): vol.In([True]), vol.Optional("include_sensitive", default=False): bool,
            vol.Optional("scope", default="all"): vol.In(["all", "ecg"])},
        "import_health_samples": {**profile, vol.Required("data"): dict,
            vol.Required("confirm_profile"): vol.In([True]), vol.Optional("include_sensitive", default=False): bool},
        "get_ecg_records": {**profile, **offset, vol.Optional("limit", default=50): vol.All(vol.Coerce(int), vol.Range(min=1, max=200))},
        "get_ecg": {**profile, vol.Required("object_uuid"): str},
        "get_ecg_waveform": {**profile, **offset, vol.Required("object_uuid"): str,
            vol.Optional("limit", default=4096): vol.All(vol.Coerce(int), vol.Range(min=1, max=4096))},
    }
    for name, fields in schema.items():
        if not hass.services.has_service(DOMAIN, name):
            hass.services.async_register(DOMAIN, name, handle, schema=vol.Schema(fields), supports_response=SupportsResponse.ONLY)
