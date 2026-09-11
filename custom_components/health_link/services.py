"""Home Assistant actions exposed by HealthLink."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from .const import (
    DOMAIN,
    EVENT_BACKFILL_REQUESTED,
    EVENT_SYNC_REQUESTED,
)
from .models import HealthLinkRuntimeData

ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_TYPE_ID = "type_id"
ATTR_DAYS = "days"
ATTR_FORMAT = "format"
ATTR_START = "start"
ATTR_END = "end"


def _runtime_for_call(hass: HomeAssistant, call: ServiceCall) -> tuple[Any, HealthLinkRuntimeData]:
    entries = [e for e in hass.config_entries.async_entries(DOMAIN) if getattr(e, "runtime_data", None)]
    wanted = call.data.get(ATTR_CONFIG_ENTRY_ID)
    if wanted:
        entry = next((e for e in entries if e.entry_id == wanted), None)
        if entry is None:
            raise ServiceValidationError("HealthLink profile not found")
    elif len(entries) == 1:
        entry = entries[0]
    elif not entries:
        raise HomeAssistantError("No loaded HealthLink profile")
    else:
        raise ServiceValidationError("Select a HealthLink profile when more than one profile exists")
    return entry, entry.runtime_data


async def _require_admin(hass: HomeAssistant, call: ServiceCall) -> None:
    if not call.context.user_id:
        return
    user = await hass.auth.async_get_user(call.context.user_id)
    if user is None or not user.is_admin:
        raise HomeAssistantError("Administrator permission is required")


def _actor(call: ServiceCall) -> str:
    return call.context.user_id or "system"


async def _recalculate(hass: HomeAssistant, call: ServiceCall) -> None:
    _, runtime = _runtime_for_call(hass, call)
    await runtime.coordinator.async_refresh_from_store()
    await runtime.store.async_audit("recalculate", actor=_actor(call))


async def _refresh_baseline(hass: HomeAssistant, call: ServiceCall) -> None:
    _, runtime = _runtime_for_call(hass, call)
    await runtime.coordinator.async_refresh_from_store()
    await runtime.store.async_audit("refresh_baseline", actor=_actor(call))


async def _sync_request(hass: HomeAssistant, call: ServiceCall) -> None:
    entry, runtime = _runtime_for_call(hass, call)
    hass.bus.async_fire(EVENT_SYNC_REQUESTED, {"config_entry_id": entry.entry_id})
    await runtime.store.async_audit("sync_request", actor=_actor(call))


async def _backfill_request(hass: HomeAssistant, call: ServiceCall) -> None:
    entry, runtime = _runtime_for_call(hass, call)
    days = int(call.data.get(ATTR_DAYS, 30))
    hass.bus.async_fire(EVENT_BACKFILL_REQUESTED, {"config_entry_id": entry.entry_id, "days": days})
    await runtime.store.async_audit("backfill_request", actor=_actor(call))


async def _purge(hass: HomeAssistant, call: ServiceCall) -> dict[str, Any]:
    await _require_admin(hass, call)
    _, runtime = _runtime_for_call(hass, call)
    days = int(call.data.get(ATTR_DAYS, 365))
    removed = await runtime.store.async_purge(days)
    await runtime.coordinator.async_refresh_from_store()
    await runtime.store.async_audit("purge", actor=_actor(call), object_type=f"older_than_{days}d")
    return {"removed": removed, "older_than_days": days}


async def _metric_exposure(hass: HomeAssistant, call: ServiceCall, exposed: bool) -> None:
    await _require_admin(hass, call)
    entry, runtime = _runtime_for_call(hass, call)
    type_id = str(call.data[ATTR_TYPE_ID])
    if exposed and not entry.options.get("enable_sensitive", False):
        catalog = await runtime.store.async_catalog()
        metric = next((item for item in catalog if item.get("type_id") == type_id), None)
        if metric and metric.get("privacy_class") not in {None, "wellness", "standard"}:
            raise ServiceValidationError("Enable sensitive metric exposure in HealthLink options first")
    changed = await runtime.store.async_set_exposed(type_id, exposed)
    if not changed:
        raise ServiceValidationError("HealthKit metric was not found")
    await runtime.store.async_audit(
        "enable_metric" if exposed else "disable_metric",
        actor=_actor(call),
        object_type=type_id,
    )
    await hass.config_entries.async_reload(entry.entry_id)


async def _export(hass: HomeAssistant, call: ServiceCall) -> dict[str, Any]:
    await _require_admin(hass, call)
    entry, runtime = _runtime_for_call(hass, call)
    fmt = str(call.data.get(ATTR_FORMAT, "json")).lower()
    if fmt not in {"json", "csv"}:
        raise ServiceValidationError("HealthLink 0.1 supports JSON or CSV export")
    rows = await runtime.store.async_export_rows(
        type_id=call.data.get(ATTR_TYPE_ID),
        start=call.data.get(ATTR_START),
        end=call.data.get(ATTR_END),
    )
    export_dir = Path(hass.config.path("health_link_exports"))
    await hass.async_add_executor_job(export_dir.mkdir, 0o700, True, True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    file_path = export_dir / f"healthlink_{entry.entry_id[:8]}_{stamp}.{fmt}"

    def _write() -> None:
        if fmt == "json":
            file_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            fieldnames = list(rows[0].keys()) if rows else ["sample_uuid", "type_id", "start_ts", "end_ts", "numeric_value", "text_value", "canonical_unit"]
            with file_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(rows)
        try:
            file_path.chmod(0o600)
        except OSError:
            pass

    await hass.async_add_executor_job(_write)
    await runtime.store.async_audit("export", actor=_actor(call), object_type=fmt)
    return {"path": str(file_path), "rows": len(rows), "format": fmt}


def async_register_services(hass: HomeAssistant) -> None:
    """Register HealthLink actions once."""
    if hass.services.has_service(DOMAIN, "recalculate"):
        return

    async def handle_recalculate(call: ServiceCall) -> None:
        await _recalculate(hass, call)

    async def handle_refresh_baseline(call: ServiceCall) -> None:
        await _refresh_baseline(hass, call)

    async def handle_sync_request(call: ServiceCall) -> None:
        await _sync_request(hass, call)

    async def handle_backfill_request(call: ServiceCall) -> None:
        await _require_admin(hass, call)
        await _backfill_request(hass, call)

    async def handle_purge(call: ServiceCall) -> dict[str, Any]:
        return await _purge(hass, call)

    async def handle_enable_metric(call: ServiceCall) -> None:
        await _metric_exposure(hass, call, True)

    async def handle_disable_metric(call: ServiceCall) -> None:
        await _metric_exposure(hass, call, False)

    async def handle_export(call: ServiceCall) -> dict[str, Any]:
        return await _export(hass, call)

    profile_schema = {vol.Optional(ATTR_CONFIG_ENTRY_ID): str}
    hass.services.async_register(DOMAIN, "recalculate", handle_recalculate, schema=vol.Schema(profile_schema))
    hass.services.async_register(DOMAIN, "refresh_baseline", handle_refresh_baseline, schema=vol.Schema(profile_schema))
    hass.services.async_register(DOMAIN, "sync_request", handle_sync_request, schema=vol.Schema(profile_schema))
    hass.services.async_register(DOMAIN, "backfill_request", handle_backfill_request, schema=vol.Schema({**profile_schema, vol.Optional(ATTR_DAYS, default=30): vol.All(vol.Coerce(int), vol.Range(min=1, max=3650))}))
    hass.services.async_register(DOMAIN, "purge", handle_purge, schema=vol.Schema({**profile_schema, vol.Required(ATTR_DAYS): vol.All(vol.Coerce(int), vol.Range(min=0, max=3650))}), supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, "enable_metric", handle_enable_metric, schema=vol.Schema({**profile_schema, vol.Required(ATTR_TYPE_ID): str}))
    hass.services.async_register(DOMAIN, "disable_metric", handle_disable_metric, schema=vol.Schema({**profile_schema, vol.Required(ATTR_TYPE_ID): str}))
    hass.services.async_register(DOMAIN, "export", handle_export, schema=vol.Schema({**profile_schema, vol.Optional(ATTR_FORMAT, default="json"): vol.In(["json", "csv"]), vol.Optional(ATTR_TYPE_ID): str, vol.Optional(ATTR_START): str, vol.Optional(ATTR_END): str}), supports_response=SupportsResponse.OPTIONAL)
