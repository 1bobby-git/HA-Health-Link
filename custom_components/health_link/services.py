"""Home Assistant actions exposed by HealthLink."""
from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.components.recorder import get_instance, history
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from .const import (
    DOMAIN,
    EVENT_BACKFILL_REQUESTED,
    EVENT_SYNC_REQUESTED,
)
from .intelligence import GOAL_KEYS, report_payload
from .models import HealthLinkRuntimeData

ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_TYPE_ID = "type_id"
ATTR_DAYS = "days"
ATTR_FORMAT = "format"
ATTR_START = "start"
ATTR_END = "end"
ATTR_GOAL = "goal"
ATTR_TARGET = "target"
ATTR_ROUTINE = "routine"
ATTR_OUTCOME = "outcome"
ATTR_NOTE = "note"
ATTR_ENTITY_ID = "entity_id"
ATTR_HOURS = "hours"
ATTR_LOWER = "lower"
ATTR_UPPER = "upper"
ATTR_LIMIT = "limit"
ATTR_MIN_CONFIDENCE = "min_confidence"


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


async def _sync_request(hass: HomeAssistant, call: ServiceCall) -> dict[str, Any]:
    entry, runtime = _runtime_for_call(hass, call)
    if runtime.companion is not None:
        result = await runtime.companion.async_refresh_now()
        result.update({"source": "current_home_assistant_states", "ios_woken": False})
    else:
        hass.bus.async_fire(EVENT_SYNC_REQUESTED, {"config_entry_id": entry.entry_id})
        result = {"source": "bridge_request_event", "ios_woken": False}
    await runtime.store.async_audit("sync_request", actor=_actor(call))
    return result


async def _backfill_request(hass: HomeAssistant, call: ServiceCall) -> dict[str, Any]:
    entry, runtime = _runtime_for_call(hass, call)
    days = int(call.data.get(ATTR_DAYS, 30))
    if runtime.companion is not None:
        result = await runtime.companion.async_import_recorder_history(days)
        result["source"] = "home_assistant_recorder"
    else:
        hass.bus.async_fire(EVENT_BACKFILL_REQUESTED, {"config_entry_id": entry.entry_id, "days": days})
        result = {"days": days, "source": "bridge_request_event"}
    await runtime.store.async_audit("backfill_request", actor=_actor(call), object_type=f"{days}d")
    return result


async def _daily_report(hass: HomeAssistant, call: ServiceCall) -> dict[str, Any]:
    entry, runtime = _runtime_for_call(hass, call)
    await runtime.coordinator.async_refresh_from_store()
    return report_payload(runtime.coordinator.data or {}, entry.options, profile=entry.title)


async def _set_goal(hass: HomeAssistant, call: ServiceCall) -> dict[str, Any]:
    await _require_admin(hass, call)
    entry, runtime = _runtime_for_call(hass, call)
    goal = str(call.data[ATTR_GOAL])
    option_key = GOAL_KEYS[goal]
    target = float(call.data[ATTR_TARGET])
    options = dict(entry.options); options[option_key] = target
    hass.config_entries.async_update_entry(entry, options=options)
    await runtime.coordinator.async_refresh_from_store()
    await runtime.store.async_audit("set_goal", actor=_actor(call), object_type=goal)
    return {"goal": goal, "target": target, "enabled": target > 0}


async def _evaluate_routine(hass: HomeAssistant, call: ServiceCall) -> dict[str, Any]:
    entry, runtime = _runtime_for_call(hass, call)
    await runtime.coordinator.async_refresh_from_store()
    data = runtime.coordinator.data or {}; routine = str(call.data[ATTR_ROUTINE]); reasons=[]; suggested=False
    if data.get("data_stale"):
        reasons.append("data_stale")
    elif routine == "evening_recovery":
        confidence=float(data.get("recovery_confidence") or 0); minimum=float(call.data.get(ATTR_MIN_CONFIDENCE,60))
        suggested=bool(data.get("recovery_below_baseline") and confidence>=minimum)
        reasons.append("recovery_below_personal_baseline" if suggested else "recovery_condition_not_met")
    else:
        key={"activity_nudge":"steps","hydration_check":"water_ml","sleep_prep":"sleep_minutes"}[routine]
        item=((data.get("goal_progress") or {}).get(key) or {})
        if not item:
            reasons.append("goal_not_configured")
        elif item.get("progress") is None:
            reasons.append("goal_data_unavailable")
        else:
            suggested=float(item["progress"])<100; reasons.append("goal_in_progress" if suggested else "goal_reached")
    return {"profile":entry.title,"routine":routine,"suggested":suggested,"reason_codes":reasons,"wellness_only":True,"medical_diagnosis":False}


async def _record_routine(hass: HomeAssistant, call: ServiceCall) -> dict[str, Any]:
    await _require_admin(hass, call)
    entry, runtime = _runtime_for_call(hass, call)
    routine=str(call.data[ATTR_ROUTINE]); outcome=str(call.data[ATTR_OUTCOME]); note=call.data.get(ATTR_NOTE)
    event_id=await runtime.store.async_record_routine(routine,outcome,note=note,actor=_actor(call))
    hass.bus.async_fire("health_link_routine_recorded",{"config_entry_id":entry.entry_id,"routine":routine,"outcome":outcome,"event_id":event_id})
    return {"id":event_id,"routine":routine,"outcome":outcome}


async def _routine_history(hass: HomeAssistant, call: ServiceCall) -> dict[str, Any]:
    await _require_admin(hass, call)
    entry, runtime = _runtime_for_call(hass, call)
    rows=await runtime.store.async_routine_history(routine=call.data.get(ATTR_ROUTINE),limit=int(call.data.get(ATTR_LIMIT,50)))
    return {"profile":entry.title,"events":rows,"count":len(rows)}


async def _environment_summary(hass: HomeAssistant, call: ServiceCall) -> dict[str, Any]:
    await _require_admin(hass, call)
    _entry_for_profile, _runtime = _runtime_for_call(hass, call)
    entity_id=str(call.data[ATTR_ENTITY_ID]); hours=int(call.data.get(ATTR_HOURS,8)); end=datetime.now(timezone.utc); start=end-timedelta(hours=hours)
    states=await get_instance(hass).async_add_executor_job(history.get_significant_states,hass,start,end,[entity_id],None,True,False,False,True,False)
    points=[]
    for state in states.get(entity_id,[]):
        try: points.append((state.last_updated,float(state.state)))
        except (AttributeError,TypeError,ValueError): pass
    if not points:return {"entity_id":entity_id,"hours":hours,"samples":0,"available":False}
    points.sort(key=lambda item:item[0]); vals=[v for _,v in points]; lower=call.data.get(ATTR_LOWER); upper=call.data.get(ATTR_UPPER)
    seconds_below=seconds_above=seconds_in=0.0
    for index,(stamp,value) in enumerate(points):
        nxt=points[index+1][0] if index+1<len(points) else end; duration=max(0.0,(nxt-stamp).total_seconds())
        if lower is not None and value<float(lower):seconds_below+=duration
        elif upper is not None and value>float(upper):seconds_above+=duration
        else:seconds_in+=duration
    total=max(1.0,(end-start).total_seconds())
    return {"entity_id":entity_id,"hours":hours,"samples":len(points),"available":True,"mean":round(sum(vals)/len(vals),3),"minimum":min(vals),"maximum":max(vals),"seconds_below":round(seconds_below),"seconds_above":round(seconds_above),"seconds_in_range":round(seconds_in),"coverage_percent":round((seconds_below+seconds_above+seconds_in)/total*100,1),"observational_only":True}


async def _trends(hass: HomeAssistant, call: ServiceCall) -> dict[str, Any]:
    entry, runtime = _runtime_for_call(hass, call); days=int(call.data.get(ATTR_DAYS,28)); data=runtime.coordinator.data or {}
    metrics={
        "steps": (["HKQuantityTypeIdentifierStepCount"], True, data.get("steps_today")),
        "hrv": (["HKQuantityTypeIdentifierHeartRateVariabilitySDNN"], True, None),
        "resting_hr": (["HKQuantityTypeIdentifierRestingHeartRate"], True, None),
        "sleep": (["companion.health_sleep_duration"], True, data.get("sleep_duration")),
    }; result={}
    from statistics import median
    for name,(ids,snapshot,current) in metrics.items():
        values=await runtime.store.async_daily_values(ids,days,snapshot=snapshot)
        result[name]={"days_with_data":len(values),"median":round(median(values),3) if values else None,"latest":current}
    return {"profile":entry.title,"window_days":days,"metrics":result,"wellness_only":True}


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
        raise ServiceValidationError("HealthLink supports JSON or CSV export")
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

    async def handle_sync_request(call: ServiceCall) -> dict[str, Any]:
        return await _sync_request(hass, call)

    async def handle_backfill_request(call: ServiceCall) -> dict[str, Any]:
        await _require_admin(hass, call)
        return await _backfill_request(hass, call)

    async def handle_daily_report(call: ServiceCall) -> dict[str, Any]:
        return await _daily_report(hass, call)

    async def handle_trends(call: ServiceCall) -> dict[str, Any]:
        return await _trends(hass, call)

    async def handle_set_goal(call: ServiceCall) -> dict[str, Any]:
        return await _set_goal(hass, call)

    async def handle_evaluate_routine(call: ServiceCall) -> dict[str, Any]:
        return await _evaluate_routine(hass, call)

    async def handle_record_routine(call: ServiceCall) -> dict[str, Any]:
        return await _record_routine(hass, call)

    async def handle_routine_history(call: ServiceCall) -> dict[str, Any]:
        return await _routine_history(hass, call)

    async def handle_environment_summary(call: ServiceCall) -> dict[str, Any]:
        return await _environment_summary(hass, call)

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
    hass.services.async_register(DOMAIN, "sync_request", handle_sync_request, schema=vol.Schema(profile_schema), supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, "backfill_request", handle_backfill_request, schema=vol.Schema({**profile_schema, vol.Optional(ATTR_DAYS, default=30): vol.All(vol.Coerce(int), vol.Range(min=1, max=3650))}), supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, "get_daily_report", handle_daily_report, schema=vol.Schema(profile_schema), supports_response=SupportsResponse.ONLY)
    hass.services.async_register(DOMAIN, "get_trends", handle_trends, schema=vol.Schema({**profile_schema, vol.Optional(ATTR_DAYS, default=28): vol.All(vol.Coerce(int), vol.Range(min=7,max=365))}), supports_response=SupportsResponse.ONLY)
    hass.services.async_register(DOMAIN, "set_goal", handle_set_goal, schema=vol.Schema({**profile_schema, vol.Required(ATTR_GOAL): vol.In(list(GOAL_KEYS)), vol.Required(ATTR_TARGET): vol.All(vol.Coerce(float), vol.Range(min=0,max=100000))}), supports_response=SupportsResponse.ONLY)
    hass.services.async_register(DOMAIN, "evaluate_routine", handle_evaluate_routine, schema=vol.Schema({**profile_schema, vol.Required(ATTR_ROUTINE): vol.In(["evening_recovery","activity_nudge","hydration_check","sleep_prep"]), vol.Optional(ATTR_MIN_CONFIDENCE,default=60): vol.All(vol.Coerce(float),vol.Range(min=0,max=100))}), supports_response=SupportsResponse.ONLY)
    hass.services.async_register(DOMAIN, "record_routine", handle_record_routine, schema=vol.Schema({**profile_schema, vol.Required(ATTR_ROUTINE): str, vol.Required(ATTR_OUTCOME): vol.In(["executed","skipped","cancelled"]), vol.Optional(ATTR_NOTE): str}), supports_response=SupportsResponse.ONLY)
    hass.services.async_register(DOMAIN, "get_routine_history", handle_routine_history, schema=vol.Schema({**profile_schema, vol.Optional(ATTR_ROUTINE): str, vol.Optional(ATTR_LIMIT,default=50): vol.All(vol.Coerce(int),vol.Range(min=1,max=200))}), supports_response=SupportsResponse.ONLY)
    hass.services.async_register(DOMAIN, "analyze_environment", handle_environment_summary, schema=vol.Schema({**profile_schema, vol.Required(ATTR_ENTITY_ID): str, vol.Optional(ATTR_HOURS,default=8): vol.All(vol.Coerce(int),vol.Range(min=1,max=720)), vol.Optional(ATTR_LOWER): vol.Coerce(float), vol.Optional(ATTR_UPPER): vol.Coerce(float)}), supports_response=SupportsResponse.ONLY)
    hass.services.async_register(DOMAIN, "purge", handle_purge, schema=vol.Schema({**profile_schema, vol.Required(ATTR_DAYS): vol.All(vol.Coerce(int), vol.Range(min=0, max=3650))}), supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, "enable_metric", handle_enable_metric, schema=vol.Schema({**profile_schema, vol.Required(ATTR_TYPE_ID): str}))
    hass.services.async_register(DOMAIN, "disable_metric", handle_disable_metric, schema=vol.Schema({**profile_schema, vol.Required(ATTR_TYPE_ID): str}))
    hass.services.async_register(DOMAIN, "export", handle_export, schema=vol.Schema({**profile_schema, vol.Optional(ATTR_FORMAT, default="json"): vol.In(["json", "csv"]), vol.Optional(ATTR_TYPE_ID): str, vol.Optional(ATTR_START): str, vol.Optional(ATTR_END): str}), supports_response=SupportsResponse.OPTIONAL)
