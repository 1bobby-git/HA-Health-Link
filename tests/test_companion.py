"""Tests for Companion event filtering and multi-device binding."""

from custom_components.health_link.companion import (
    CompanionImporter,
    _normalize_device_ids,
)


def test_state_reported_filter_only_accepts_imported_health_entities() -> None:
    """Only state_reported events for mapped Health sensors should pass."""
    importer = object.__new__(CompanionImporter)
    importer._entity_map = {
        "sensor.iphone_health_heart_rate": "health_heart_rate",
        "sensor.iphone_health_steps": "health_steps",
    }

    assert importer._state_reported_filter(
        {"entity_id": "sensor.iphone_health_heart_rate"}
    )
    assert not importer._state_reported_filter({"entity_id": "sensor.living_room_temperature"})
    assert not importer._state_reported_filter({})


def test_normalize_device_ids_supports_single_and_multiple_iphones() -> None:
    """One profile can bind one or several Companion iPhones."""
    assert _normalize_device_ids(None) == frozenset()
    assert _normalize_device_ids("iphone-a") == frozenset({"iphone-a"})
    assert _normalize_device_ids(["iphone-a", "iphone-b", "iphone-a"]) == frozenset(
        {"iphone-a", "iphone-b"}
    )


def test_importer_exposes_multiple_bound_device_ids() -> None:
    """The importer keeps all configured source devices for one person profile."""
    importer = CompanionImporter(None, None, ["iphone-b", "iphone-a"])  # type: ignore[arg-type]

    assert importer.bound_device_ids == ("iphone-a", "iphone-b")
    assert importer.bound_device_id is None
