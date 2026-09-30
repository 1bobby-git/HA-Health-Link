"""The last_sync timestamp sensor must expose an aware datetime.

Home Assistant rejects naive datetimes for SensorDeviceClass.TIMESTAMP, so a
naive stored value must be normalized to UTC instead of surfacing an error.
"""
from __future__ import annotations

from types import SimpleNamespace as NS

from custom_components.health_link import sensor


def _last_sync_sensor(value):
    description = next(d for d in sensor.DESCRIPTIONS if d.key == "last_sync")
    runtime = NS(coordinator=NS(data={"last_sync": value}), store=NS(profile_id="p"))
    entity = sensor.HealthLinkSensor.__new__(sensor.HealthLinkSensor)
    entity.entity_description = description
    entity.coordinator = runtime.coordinator
    return entity


def test_naive_last_sync_is_normalized_to_utc():
    entity = _last_sync_sensor("2026-09-10T12:00:00")
    result = entity.native_value
    assert result is not None
    assert result.tzinfo is not None
    assert result.utcoffset().total_seconds() == 0


def test_aware_last_sync_is_preserved():
    entity = _last_sync_sensor("2026-09-10T12:00:00+09:00")
    result = entity.native_value
    assert result.tzinfo is not None
    assert result.utcoffset().total_seconds() == 9 * 3600


def test_invalid_last_sync_is_none():
    entity = _last_sync_sensor("garbage")
    assert entity.native_value is None
