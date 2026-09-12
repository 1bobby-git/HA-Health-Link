"""Sensor platform for HealthLink."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.const import EntityCategory, PERCENTAGE, UnitOfEnergy, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, DOMAIN_ICONS
from .models import HealthLinkRuntimeData

@dataclass(frozen=True, kw_only=True)
class HealthLinkSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str,Any]], Any]

DESCRIPTIONS = (
    HealthLinkSensorDescription(key="steps_goal_progress",translation_key="steps_goal_progress",native_unit_of_measurement=PERCENTAGE,icon="mdi:target",state_class=SensorStateClass.MEASUREMENT,value_fn=lambda d:((d.get("goal_progress") or {}).get("steps") or {}).get("progress")),
    HealthLinkSensorDescription(key="exercise_goal_progress",translation_key="exercise_goal_progress",native_unit_of_measurement=PERCENTAGE,icon="mdi:target",state_class=SensorStateClass.MEASUREMENT,value_fn=lambda d:((d.get("goal_progress") or {}).get("exercise_minutes") or {}).get("progress")),
    HealthLinkSensorDescription(key="active_energy_goal_progress",translation_key="active_energy_goal_progress",native_unit_of_measurement=PERCENTAGE,icon="mdi:target",state_class=SensorStateClass.MEASUREMENT,value_fn=lambda d:((d.get("goal_progress") or {}).get("active_energy") or {}).get("progress")),
    HealthLinkSensorDescription(key="water_goal_progress",translation_key="water_goal_progress",native_unit_of_measurement=PERCENTAGE,icon="mdi:cup-water",state_class=SensorStateClass.MEASUREMENT,value_fn=lambda d:((d.get("goal_progress") or {}).get("water_ml") or {}).get("progress")),
    HealthLinkSensorDescription(key="sleep_goal_progress",translation_key="sleep_goal_progress",native_unit_of_measurement=PERCENTAGE,icon="mdi:sleep",state_class=SensorStateClass.MEASUREMENT,value_fn=lambda d:((d.get("goal_progress") or {}).get("sleep_minutes") or {}).get("progress")),
    HealthLinkSensorDescription(key="steps_vs_same_time_baseline",translation_key="steps_vs_same_time_baseline",native_unit_of_measurement=PERCENTAGE,icon="mdi:chart-timeline-variant",state_class=SensorStateClass.MEASUREMENT,value_fn=lambda d:d.get("steps_vs_same_time_baseline")),
    HealthLinkSensorDescription(key="daily_goal_context",translation_key="daily_goal_context",icon="mdi:target-account",value_fn=lambda d:d.get("daily_goal_context")),
    HealthLinkSensorDescription(key="daily_focus",translation_key="daily_focus",icon="mdi:lightbulb-on-outline",value_fn=lambda d:d.get("daily_focus")),
    HealthLinkSensorDescription(key="last_sync",translation_key="last_sync",icon="mdi:sync",device_class=SensorDeviceClass.TIMESTAMP,entity_category=EntityCategory.DIAGNOSTIC,value_fn=lambda d:d.get("last_sync")),
    HealthLinkSensorDescription(key="sync_latency",translation_key="sync_latency",native_unit_of_measurement=UnitOfTime.SECONDS,icon="mdi:timer-sync-outline",entity_category=EntityCategory.DIAGNOSTIC,value_fn=lambda d:d.get("sync_latency_seconds")),
    HealthLinkSensorDescription(key="data_confidence",translation_key="data_confidence",native_unit_of_measurement=PERCENTAGE,icon="mdi:shield-check-outline",state_class=SensorStateClass.MEASUREMENT,value_fn=lambda d:d.get("data_confidence")),
    HealthLinkSensorDescription(key="steps_today",entity_registry_enabled_default=False,translation_key="steps_today",native_unit_of_measurement="steps",icon="mdi:walk",state_class=SensorStateClass.TOTAL_INCREASING,value_fn=lambda d:d.get("steps_today")),
    HealthLinkSensorDescription(key="active_energy_today",entity_registry_enabled_default=False,translation_key="active_energy_today",native_unit_of_measurement="kcal",icon="mdi:fire",state_class=SensorStateClass.TOTAL_INCREASING,value_fn=lambda d:d.get("active_energy_today")),
    HealthLinkSensorDescription(key="exercise_time_today",entity_registry_enabled_default=False,translation_key="exercise_time_today",native_unit_of_measurement=UnitOfTime.MINUTES,icon="mdi:timer-outline",state_class=SensorStateClass.TOTAL_INCREASING,value_fn=lambda d:d.get("exercise_time_today")),
    HealthLinkSensorDescription(key="last_sleep_duration",entity_registry_enabled_default=False,translation_key="last_sleep_duration",native_unit_of_measurement=UnitOfTime.MINUTES,icon="mdi:sleep",state_class=SensorStateClass.MEASUREMENT,value_fn=lambda d:d.get("sleep_duration")),
    HealthLinkSensorDescription(key="last_sleep_deep",entity_registry_enabled_default=False,translation_key="last_sleep_deep",native_unit_of_measurement=UnitOfTime.MINUTES,icon="mdi:sleep",state_class=SensorStateClass.MEASUREMENT,value_fn=lambda d:d.get("sleep_deep")),
    HealthLinkSensorDescription(key="last_sleep_rem",entity_registry_enabled_default=False,translation_key="last_sleep_rem",native_unit_of_measurement=UnitOfTime.MINUTES,icon="mdi:brain",state_class=SensorStateClass.MEASUREMENT,value_fn=lambda d:d.get("sleep_rem")),
    HealthLinkSensorDescription(key="last_sleep_efficiency",entity_registry_enabled_default=False,translation_key="last_sleep_efficiency",native_unit_of_measurement=PERCENTAGE,icon="mdi:bed-clock",state_class=SensorStateClass.MEASUREMENT,value_fn=lambda d:d.get("sleep_efficiency")),
    HealthLinkSensorDescription(key="recovery_context",translation_key="recovery_context",icon="mdi:battery-heart-variant",value_fn=lambda d:d.get("recovery_context")),
    HealthLinkSensorDescription(key="recovery_confidence",translation_key="recovery_confidence",native_unit_of_measurement=PERCENTAGE,icon="mdi:shield-check-outline",state_class=SensorStateClass.MEASUREMENT,value_fn=lambda d:d.get("recovery_confidence")),
    HealthLinkSensorDescription(key="hrv_vs_baseline",translation_key="hrv_vs_baseline",native_unit_of_measurement=PERCENTAGE,icon="mdi:heart-pulse",state_class=SensorStateClass.MEASUREMENT,value_fn=lambda d:d.get("hrv_vs_baseline")),
    HealthLinkSensorDescription(key="resting_hr_vs_baseline",translation_key="resting_hr_vs_baseline",native_unit_of_measurement=PERCENTAGE,icon="mdi:heart-pulse",state_class=SensorStateClass.MEASUREMENT,value_fn=lambda d:d.get("resting_hr_vs_baseline")),
    HealthLinkSensorDescription(key="sleep_vs_baseline",translation_key="sleep_vs_baseline",native_unit_of_measurement=PERCENTAGE,icon="mdi:sleep",state_class=SensorStateClass.MEASUREMENT,value_fn=lambda d:d.get("sleep_vs_baseline")),
    HealthLinkSensorDescription(key="activity_vs_baseline",translation_key="activity_vs_baseline",native_unit_of_measurement=PERCENTAGE,icon="mdi:walk",state_class=SensorStateClass.MEASUREMENT,value_fn=lambda d:d.get("activity_vs_baseline")),
)

CORE_TYPES={
    "HKQuantityTypeIdentifierStepCount","HKQuantityTypeIdentifierActiveEnergyBurned",
    "HKQuantityTypeIdentifierAppleExerciseTime","companion.health_sleep_duration",
    "companion.health_sleep_deep","companion.health_sleep_rem",
}

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    runtime:HealthLinkRuntimeData=entry.runtime_data
    entities:list[SensorEntity]=[HealthLinkSensor(runtime,entry,d) for d in DESCRIPTIONS]
    for info in await runtime.store.async_exposed_types():
        if info["type_id"] not in CORE_TYPES:
            entities.append(HealthLinkRawMetricSensor(runtime,entry,info))
    for definition in await runtime.store.async_list_composers():
        if definition.get("enabled") and definition.get("entity_exposure", 1):
            entities.append(HealthLinkComposerSensor(runtime,entry,definition))
    async_add_entities(entities)

class _Base(CoordinatorEntity):
    _attr_has_entity_name=True
    def __init__(self,runtime:HealthLinkRuntimeData,entry:ConfigEntry)->None:
        super().__init__(runtime.coordinator)
        self.runtime=runtime;self.entry=entry
    @property
    def device_info(self)->DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN,self.runtime.store.profile_id)},name=f"HealthLink — {self.entry.title}",manufacturer="HealthLink",model="Health Context Profile")

class HealthLinkSensor(_Base,SensorEntity):
    entity_description:HealthLinkSensorDescription
    def __init__(self,runtime,entry,description):
        super().__init__(runtime,entry);self.entity_description=description
        self._attr_unique_id=f"{entry.entry_id}_{description.key}"
    @property
    def native_value(self):
        value=self.entity_description.value_fn(self.coordinator.data or {})
        if self.entity_description.key=="last_sync" and isinstance(value,str):
            try:return datetime.fromisoformat(value)
            except ValueError:return None
        if isinstance(value,float):return round(value,2)
        return value
    @property
    def extra_state_attributes(self):
        d=self.coordinator.data or {}
        if self.entity_description.key=="recovery_context":
            return {"experimental_wellness_metric":True,"score":d.get("recovery_score"),"confidence":d.get("recovery_confidence"),"medical_diagnosis":False}
        goal_map={
            "steps_goal_progress":"steps",
            "exercise_goal_progress":"exercise_minutes",
            "active_energy_goal_progress":"active_energy",
            "water_goal_progress":"water_ml",
            "sleep_goal_progress":"sleep_minutes",
        }
        goal_key=goal_map.get(self.entity_description.key)
        if goal_key:
            item=((d.get("goal_progress") or {}).get(goal_key) or {})
            return {"target":item.get("target"),"current":item.get("current"),"reached":item.get("reached"),"user_defined_goal":True,"medical_recommendation":False}
        if self.entity_description.key=="steps_vs_same_time_baseline":
            return {"comparison":"median of previous days at or before the same local clock time","personal_baseline":True,"medical_diagnosis":False}
        return None

class HealthLinkRawMetricSensor(_Base,SensorEntity):
    def __init__(self,runtime,entry,info:dict[str,Any]):
        super().__init__(runtime,entry);self.info=info;self.type_id=info["type_id"]
        import hashlib
        token=hashlib.sha1(self.type_id.encode()).hexdigest()[:16]
        self._attr_unique_id=f"{entry.entry_id}_metric_{token}"
        self._attr_name=info.get("display_name") or self.type_id
        self._attr_icon=DOMAIN_ICONS.get(info.get("domain"),"mdi:heart-plus")
        self._attr_native_unit_of_measurement=info.get("canonical_unit")
        if info.get("object_kind") in {"quantity","activity_summary"}:
            if info.get("aggregation_kind") in {"cumulative_sum", "daily_snapshot"}:
                self._attr_state_class=SensorStateClass.TOTAL_INCREASING
            else:
                self._attr_state_class=SensorStateClass.MEASUREMENT
    @property
    def native_value(self):
        row=(self.coordinator.data or {}).get("raw_metrics",{}).get(self.type_id)
        if not row:return None
        return row.get("numeric_value") if row.get("numeric_value") is not None else row.get("text_value")
    @property
    def extra_state_attributes(self):
        row=(self.coordinator.data or {}).get("raw_metrics",{}).get(self.type_id) or {}
        return {"healthkit_type":self.type_id,"health_domain":self.info.get("domain"),"last_sample":row.get("end_ts"),"privacy_class":self.info.get("privacy_class")}


class HealthLinkComposerSensor(_Base,SensorEntity):
    """Sensor created from a no-code Health Composer definition."""
    def __init__(self,runtime,entry,definition:dict[str,Any]):
        super().__init__(runtime,entry)
        self.definition=definition
        self.definition_id=definition["id"]
        self._attr_unique_id=f"{entry.entry_id}_composer_{self.definition_id}"
        self._attr_name=definition.get("name") or self.definition_id.replace("_"," ").title()
        config=definition.get("definition") or {}
        self._attr_native_unit_of_measurement=config.get("unit")
        self._attr_icon=config.get("icon","mdi:function-variant")
    @property
    def native_value(self):
        item=(self.coordinator.data or {}).get("composer_values",{}).get(self.definition_id) or {}
        value=item.get("value")
        return round(value,3) if isinstance(value,float) else value
    @property
    def extra_state_attributes(self):
        item=(self.coordinator.data or {}).get("composer_values",{}).get(self.definition_id) or {}
        return {
            "confidence":item.get("confidence"),
            "available_inputs":item.get("available_inputs"),
            "input_count":item.get("inputs"),
            "generated_by":"HealthLink Composer",
            "medical_diagnosis":False,
        }
