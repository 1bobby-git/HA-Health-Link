"""Binary sensor platform for HealthLink."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any,Callable

from homeassistant.components.binary_sensor import BinarySensorEntity,BinarySensorEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .models import HealthLinkRuntimeData

@dataclass(frozen=True,kw_only=True)
class Desc(BinarySensorEntityDescription):
    value_fn:Callable[[dict[str,Any]],bool]

DESCRIPTIONS=(
    Desc(key="data_stale",translation_key="data_stale",icon="mdi:database-clock-outline",entity_category=EntityCategory.DIAGNOSTIC,value_fn=lambda d:bool(d.get("data_stale",True))),
    Desc(key="configured_goals_reached",translation_key="configured_goals_reached",icon="mdi:target",value_fn=lambda d:d.get("daily_goal_context")=="all_reached"),
    Desc(key="recovery_below_baseline",translation_key="recovery_below_baseline",icon="mdi:battery-heart-variant",value_fn=lambda d:bool(d.get("recovery_below_baseline",False))),
)

async def async_setup_entry(hass:HomeAssistant,entry:ConfigEntry,async_add_entities:AddEntitiesCallback)->None:
    runtime:HealthLinkRuntimeData=entry.runtime_data
    async_add_entities([HealthLinkBinarySensor(runtime,entry,d) for d in DESCRIPTIONS])

class HealthLinkBinarySensor(CoordinatorEntity,BinarySensorEntity):
    _attr_has_entity_name=True
    entity_description:Desc
    def __init__(self,runtime,entry,description):
        super().__init__(runtime.coordinator);self.runtime=runtime;self.entry=entry;self.entity_description=description
        self._attr_unique_id=f"{entry.entry_id}_{description.key}"
    @property
    def is_on(self):return self.entity_description.value_fn(self.coordinator.data or {})
    @property
    def device_info(self):
        return DeviceInfo(identifiers={(DOMAIN,self.runtime.store.profile_id)},name=f"HealthLink — {self.entry.title}",manufacturer="HealthLink",model="Health Context Profile")
