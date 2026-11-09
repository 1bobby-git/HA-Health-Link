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


def test_registered_iphone_and_ipad_are_discoverable_without_health_entities(monkeypatch):
    registrations = [
        entry("ios", data={"os_name": "iOS", "model": "iPhone17,3", "manufacturer": "Apple"}),
        entry("ipad", data={"os_name": "iPadOS", "model": "iPad16,3", "manufacturer": "Apple"}),
        entry("android", data={"os_name": "Android", "manufacturer": "Google"}),
        entry("mac", data={"os_name": "macOS", "manufacturer": "Apple"}),
    ]
    devices = {key: NS(id=key, config_entries={key}, manufacturer=manufacturer,
                      model=model, name=name, name_by_user=None)
               for key, manufacturer, model, name in [
                   ("ios", "Apple", "iPhone17,3", "가족 iPhone"),
                   ("ipad", "Apple", "iPad16,3", "가족 iPad"),
                   ("android", "Google", "Pixel", "Android"),
                   ("mac", "Apple", "MacBook", "Mac"),
               ]}
    _patch_registries(monkeypatch, devices)
    hass = NS(config_entries=NS(async_entries=lambda domain: registrations if domain == "mobile_app" else []))
    assert discover_ios_devices(hass) == {"ios": "가족 iPhone", "ipad": "가족 iPad"}


class _GuardedDevice:
    """Device whose deprecated config-entry fields fail loudly when read.

    HA 2026.11 deprecates DeviceEntry.config_entries / config_entries_subentries /
    primary_config_entry; every read runs report_usage(), which walks the stack
    and sys.modules and can dominate the event loop on large installs.
    """

    def __init__(self, device_id, owners, *, manufacturer="Apple", model="iPhone17,3", name=None):
        self.id = device_id
        self.owners = frozenset(owners)
        self.manufacturer = manufacturer
        self.model = model
        self.name = name or device_id
        self.name_by_user = None

    @property
    def config_entries(self):
        raise AssertionError("deprecated DeviceEntry.config_entries was read")

    @property
    def config_entries_subentries(self):
        raise AssertionError("deprecated DeviceEntry.config_entries_subentries was read")

    @property
    def primary_config_entry(self):
        raise AssertionError("deprecated DeviceEntry.primary_config_entry was read")


def _patch_registries(monkeypatch, devices):
    """Fake the device registry; owners are resolvable only via the per-entry index."""
    from custom_components.health_link import profile_support

    registry = NS(devices=devices)
    calls = []

    def entries_for_config_entry(reg, entry_id):
        assert reg is registry
        calls.append(entry_id)
        return [d for d in devices.values()
                if entry_id in (d.owners if isinstance(d, _GuardedDevice) else d.config_entries)]

    monkeypatch.setattr(profile_support.dr, "async_get", lambda hass: registry)
    monkeypatch.setattr(profile_support.dr, "async_entries_for_config_entry", entries_for_config_entry)
    monkeypatch.setattr(profile_support.er, "async_get", lambda hass: NS(entities={}))
    return calls


def test_discovery_never_reads_deprecated_device_config_entries(monkeypatch):
    registrations = [
        entry("ios", data={"os_name": "iOS", "model": "iPhone17,3", "manufacturer": "Apple"}),
        entry("android", data={"os_name": "Android", "manufacturer": "Google"}),
    ]
    devices = {
        "phone": _GuardedDevice("phone", {"ios"}, name="내 iPhone"),
        "pixel": _GuardedDevice("pixel", {"android"}, manufacturer="Google", model="Pixel"),
        # A device owned only by a non-Companion integration is never considered.
        "light": _GuardedDevice("light", {"hue"}, manufacturer="Signify", model="Bulb"),
    }
    calls = _patch_registries(monkeypatch, devices)
    hass = NS(config_entries=NS(async_entries=lambda domain: registrations if domain == "mobile_app" else []))
    assert discover_ios_devices(hass) == {"phone": "내 iPhone"}
    # Only the Companion registrations are looked up through the index.
    assert sorted(calls) == ["android", "ios"]


def test_composite_device_keeps_all_companion_registrations(monkeypatch):
    """A device shared by several entries is listed once; any iOS owner qualifies it."""
    registrations = [
        entry("android", data={"os_name": "Android", "manufacturer": "Google"}),
        entry("ios", data={"os_name": "iOS", "model": "iPhone17,3", "manufacturer": "Apple"}),
    ]
    devices = {
        "shared": _GuardedDevice("shared", {"android", "ios", "other"}, name="공유 iPhone"),
        "android-only": _GuardedDevice("android-only", {"android"}, manufacturer="Google", model="Pixel"),
    }
    _patch_registries(monkeypatch, devices)
    hass = NS(config_entries=NS(async_entries=lambda domain: registrations if domain == "mobile_app" else []))
    assert discover_ios_devices(hass) == {"shared": "공유 iPhone"}


def test_discovery_without_companion_registrations_lists_nothing(monkeypatch):
    calls = _patch_registries(monkeypatch, {"phone": _GuardedDevice("phone", {"ios"})})
    hass = NS(config_entries=NS(async_entries=lambda domain: []))
    assert discover_ios_devices(hass) == {}
    assert calls == []


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
