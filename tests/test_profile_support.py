"""Regression tests for family device discovery and profile isolation."""
import asyncio
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, Mock

from custom_components.health_link import config_flow
from custom_components.health_link.companion import CompanionImporter
from custom_components.health_link.profile_support import (
    discover_ios_devices, devices_in_use, entry_device_ids, normalize_device_ids,
)


def entry(eid, ids=None, *, options=None, data=None, runtime=None):
    return NS(entry_id=eid, data=data if data is not None else {"companion_device_ids": ids or []},
              options=options or {}, runtime_data=runtime)


def test_cleared_options_do_not_resurrect_legacy_phone():
    e = entry("profile", ["old"], options={"companion_device_ids": []})
    assert entry_device_ids(e) == set()
    e.data["companion_device_id"] = "legacy"
    assert entry_device_ids(e) == set()
    assert normalize_device_ids({"not": "a list"}) == []


def test_multiple_phones_stay_reserved_per_person():
    entries = [entry("a", ["phone-a", "phone-b"]), entry("b", ["phone-c"])]
    hass = NS(config_entries=NS(async_entries=lambda domain: entries))
    assert devices_in_use(hass, ["phone-b", "phone-c", "phone-d"], exclude_entry_id="a") == {"phone-c"}


def test_registered_iphone_is_discoverable_without_health_entities(monkeypatch):
    registrations = [
        entry("ios", data={"os_name": "iOS", "model": "iPhone17,3", "manufacturer": "Apple"}),
        entry("android", data={"os_name": "Android", "manufacturer": "Google"}),
        entry("mac", data={"os_name": "macOS", "manufacturer": "Apple"}),
    ]
    devices = {key: NS(id=key, config_entries={key}, manufacturer=manufacturer,
                      model=model, name=name, name_by_user=None)
               for key, manufacturer, model, name in [
                   ("ios", "Apple", "iPhone17,3", "가족 iPhone"),
                   ("android", "Google", "Pixel", "Android"),
                   ("mac", "Apple", "MacBook", "Mac"),
               ]}
    from custom_components.health_link import profile_support
    monkeypatch.setattr(profile_support.dr, "async_get", lambda hass: NS(devices=devices))
    monkeypatch.setattr(profile_support.er, "async_get", lambda hass: NS(entities={}))
    hass = NS(config_entries=NS(async_entries=lambda domain: registrations if domain == "mobile_app" else []))
    assert discover_ios_devices(hass) == {"ios": "가족 iPhone"}


def test_exactly_one_remaining_iphone_is_shown(monkeypatch):
    entries = [entry("person-a", ["phone-a"])]
    hass = NS(config=NS(language="ko"), config_entries=NS(async_entries=lambda domain: entries))
    monkeypatch.setattr(config_flow, "discover_companion_devices", lambda hass: {"phone-a": "내 iPhone", "phone-b": "가족 iPhone"})
    flow = config_flow.HealthLinkConfigFlow()
    flow.hass = hass
    flow.async_show_form = Mock(side_effect=lambda **kwargs: kwargs)
    result = asyncio.run(flow.async_step_user())
    schema = result["data_schema"].schema
    selector = next(value for key, value in schema.items() if str(key) == "companion_device_ids")
    assert selector.config["options"] == [{"value": "phone-b", "label": "가족 iPhone"}]
    assert result["description_placeholders"]["available_device_count"] == "1"


def test_empty_multiphone_selection_requires_explicit_choice(monkeypatch):
    monkeypatch.setattr(config_flow, "discover_companion_devices", lambda hass: {"a": "A", "b": "B"})
    flow = config_flow.HealthLinkConfigFlow()
    flow.hass = NS(config=NS(language="ko"), config_entries=NS(async_entries=lambda domain: []))
    flow.async_show_form = Mock(side_effect=lambda **kwargs: kwargs)
    result = asyncio.run(flow.async_step_user({"profile_name": "가족", "companion_device_ids": []}))
    assert result["errors"]["companion_device_ids"] == "select_device"


def test_state_reported_listener_starts_on_real_home_assistant(tmp_path):
    from homeassistant.core import HomeAssistant
    async def run():
        hass = HomeAssistant(str(tmp_path))
        runtime = NS(coordinator=NS(entry=entry("profile", ["phone"])))
        importer = CompanionImporter(hass, runtime, ["phone"])
        importer._async_rescan = AsyncMock()
        await importer.async_start()
        await importer.async_stop()
        assert importer._unsubs == []
    asyncio.run(run())


def test_second_unassigned_profile_never_auto_binds_existing_phone(monkeypatch):
    from custom_components.health_link import companion
    existing = entry("person-a", ["phone-a"])
    waiting = entry("person-b", [])
    entries = [existing, waiting]
    hass = NS(config_entries=NS(async_entries=lambda domain: entries, async_update_entry=Mock()))
    runtime = NS(coordinator=NS(entry=waiting, async_refresh_from_store=AsyncMock()), store=NS(async_ingest=AsyncMock()))
    monkeypatch.setattr(companion.er, "async_get", lambda hass: NS(entities={}))
    monkeypatch.setattr(companion, "discover_companion_devices", lambda hass: {"phone-a": "A"})
    importer = CompanionImporter(hass, runtime, [])
    asyncio.run(importer._async_rescan(import_now=True))
    assert importer.bound_device_ids == ()
    assert importer.needs_device_selection
    runtime.store.async_ingest.assert_not_awaited()
    hass.config_entries.async_update_entry.assert_not_called()
