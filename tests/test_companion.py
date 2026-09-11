"""Tests for Companion event filtering."""

from custom_components.health_link.companion import CompanionImporter


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
