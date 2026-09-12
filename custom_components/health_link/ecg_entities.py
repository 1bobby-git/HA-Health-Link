"""Small native ECG summary sensors; waveform points never enter attributes."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .health_import import ECG_TYPE
from .data_features import exposed_types


async def ecg_enabled(store, options) -> bool:
    return any(item["type_id"] == ECG_TYPE for item in await exposed_types(store, options))


def profile_device(runtime, entry):
    return DeviceInfo(identifiers={(DOMAIN, runtime.store.profile_id)}, name=f"HealthLink — {entry.title}",
                      manufacturer="HealthLink", model="Health Context Profile")


class ECGSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, runtime, entry, key, field, unit=None, device_class=None):
        super().__init__(runtime.coordinator)
        self.entry = entry
        self.field = field
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_icon = "mdi:heart-pulse"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_device_info = profile_device(runtime, entry)
        if field in {"count", "average_heart_rate", "point_count", "duration_seconds"}:
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def available(self):
        return super().available and bool(self.entry.options.get("enable_sensitive")) and bool((self.coordinator.data or {}).get("ecg"))

    @property
    def native_value(self):
        summary = (self.coordinator.data or {}).get("ecg") or {}
        if self.field == "count":
            return summary.get("count")
        latest = summary.get("latest") or {}
        value = latest.get(self.field)
        if self.field == "start" and value:
            return datetime.fromisoformat(value)
        return value

    @property
    def extra_state_attributes(self):
        latest = ((self.coordinator.data or {}).get("ecg") or {}).get("latest") or {}
        return {"record_id": latest.get("object_uuid"), "classification_origin": "source_record",
                "medical_diagnosis": False, "live_monitoring": False}


def ecg_sensors(runtime, entry):
    return [ECGSensor(runtime, entry, *args) for args in (
        ("ecg_record_count", "count"),
        ("ecg_last_recorded", "start", None, SensorDeviceClass.TIMESTAMP),
        ("ecg_classification", "classification"),
        ("ecg_average_heart_rate", "average_heart_rate", "bpm"),
        ("ecg_point_count", "point_count"),
        ("ecg_duration", "duration_seconds", "s", SensorDeviceClass.DURATION),
    )]
