"""Administrator-visible profile status, including waiting/failed profiles."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState

from .const import CONF_PROFILE_ID
from .profile_support import entry_device_ids


def profile_loaded(entry) -> bool:
    """Never use a retained runtime after an entry was unloaded or disabled."""
    return (
        getattr(entry, "state", None) == ConfigEntryState.LOADED
        and getattr(entry, "disabled_by", None) is None
        and getattr(entry, "runtime_data", None) is not None
    )


def profile_summary(entry) -> dict:
    """Expose metadata but not stale health values for unavailable profiles."""
    state = getattr(entry, "state", None)
    loaded = profile_loaded(entry)
    base = {
        "config_entry_id": entry.entry_id,
        "title": entry.title,
        "profile_id": entry.data.get(CONF_PROFILE_ID),
        "available": loaded,
        "entry_state": getattr(state, "value", str(state or "not_loaded")),
        "source_mode": entry.options.get("source_mode", "auto"),
        "companion_device_ids": sorted(entry_device_ids(entry)),
        "setup_state": "profile_unavailable",
    }
    base["companion_device_count"] = len(base["companion_device_ids"])
    if not loaded:
        return base
    runtime = entry.runtime_data
    data = runtime.coordinator.data or {}
    companion = runtime.companion
    count = companion.sensor_count if companion else 0
    choose = companion.needs_device_selection if companion else False
    setup = "choose_iphone" if choose else "enable_health_sensors" if companion and count == 0 else "ready" if count else "bridge_only"
    keys = (
        "sample_count", "type_count", "source_count", "last_sync", "data_stale",
        "data_confidence", "steps_today", "sleep_duration", "sleep_deep", "sleep_rem",
        "sleep_efficiency", "recovery_context", "recovery_score", "recovery_confidence",
        "goal_progress", "daily_goal_context", "daily_focus", "steps_vs_same_time_baseline",
    )
    return {
        **base,
        **{key: data.get(key) for key in keys},
        "companion_active": companion is not None,
        "companion_device_id": companion.bound_device_id if companion else None,
        "companion_device_ids": list(companion.bound_device_ids) if companion else [],
        "companion_device_count": len(companion.bound_device_ids) if companion else 0,
        "companion_needs_selection": choose,
        "companion_sensor_count": count,
        "setup_state": setup,
        "bridge_ready": base["source_mode"] in {"bridge", "both"} and bool(runtime.webhook_id),
    }
