"""Profile identity and Apple mobile-device discovery."""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import CONF_COMPANION_DEVICE_ID, CONF_COMPANION_DEVICE_IDS, DOMAIN


def normalize_device_ids(value: Any) -> list[str]:
    """Keep stable IDs; an explicit empty selection must stay empty."""
    if isinstance(value, str):
        return [value] if value else []
    if not isinstance(value, (list, tuple, set, frozenset)):
        return []
    return list(dict.fromkeys(item for item in value if isinstance(item, str) and item))


def entry_device_ids(entry: Any) -> set[str]:
    """Options override data, including when the user explicitly clears them."""
    if CONF_COMPANION_DEVICE_IDS in entry.options:
        return set(normalize_device_ids(entry.options[CONF_COMPANION_DEVICE_IDS]))
    if CONF_COMPANION_DEVICE_ID in entry.options:
        return set(normalize_device_ids(entry.options[CONF_COMPANION_DEVICE_ID]))
    selected = normalize_device_ids(entry.data.get(CONF_COMPANION_DEVICE_IDS))
    if not selected:
        selected = normalize_device_ids(entry.data.get(CONF_COMPANION_DEVICE_ID))
    if selected:
        return set(selected)
    runtime = getattr(entry, "runtime_data", None)
    companion = getattr(runtime, "companion", None)
    return set(normalize_device_ids(getattr(companion, "bound_device_ids", None)))


def devices_in_use(hass, device_ids: Iterable[str], *, exclude_entry_id=None) -> set[str]:
    """Keep an Apple mobile device assigned to only one personal profile."""
    requested = set(device_ids)
    used: set[str] = set()
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.entry_id != exclude_entry_id:
            used.update(requested & entry_device_ids(entry))
    return used


def discover_ios_devices(hass) -> dict[str, str]:
    """List Companion-registered iOS/iPadOS devices before Labs is enabled.

    The selector represents Apple mobile devices registered to this Home Assistant
    through the official Companion app, not Home Assistant user accounts. Apple
    Watch is not selected directly; its HealthKit records can be present in the
    Apple Health data read by the selected iPhone or iPad.

    Registration OS/model is evidence of eligibility, not of health permission.
    Do not enumerate arbitrary HA users or infer ownership from a device name.
    """
    mobile = {e.entry_id: e for e in hass.config_entries.async_entries("mobile_app")}
    registry = dr.async_get(hass)
    health_devices = {
        e.device_id
        for e in er.async_get(hass).entities.values()
        if e.platform == "mobile_app" and e.domain == "sensor" and e.device_id
        and "health_" in str(e.unique_id or "")
    }
    result: dict[str, str] = {}
    for device in registry.devices.values():
        registrations = [mobile[eid] for eid in device.config_entries if eid in mobile]
        if not registrations:
            continue
        eligible = False
        for registration in registrations:
            data = registration.data
            os_name = str(data.get("os_name") or "").lower()
            model = str(data.get("model") or device.model or "").lower()
            manufacturer = str(data.get("manufacturer") or device.manufacturer or "").lower()
            if os_name and os_name not in {"ios", "ipados"}:
                continue
            if os_name in {"ios", "ipados"} or (
                manufacturer == "apple" and model.startswith(("iphone", "ipad"))
            ) or (not os_name and device.id in health_devices and manufacturer == "apple"):
                eligible = True
                break
        if eligible:
            result[device.id] = device.name_by_user or device.name or device.id
    # Duplicate device names must remain distinguishable in the selector.
    names = list(result.values())
    return {
        device_id: f"{name} ({device_id[:6]})" if names.count(name) > 1 else name
        for device_id, name in sorted(result.items(), key=lambda item: (item[1].casefold(), item[0]))
    }
