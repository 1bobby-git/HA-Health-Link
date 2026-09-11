"""Zero-friction import of official Home Assistant iOS Apple Health sensors."""
from __future__ import annotations

from datetime import timedelta
import hashlib
import logging
from typing import Any

from homeassistant.const import EVENT_STATE_CHANGED, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_time_interval

from .const import COMPANION_METRICS

_LOGGER=logging.getLogger(__name__)


def _metric_unique_id(entry: er.RegistryEntry) -> str | None:
    uid=str(entry.unique_id or "")
    if uid in COMPANION_METRICS: return uid
    for known in COMPANION_METRICS:
        if uid.endswith(known): return known
    if "health_" in uid:
        return uid[uid.rfind("health_"):]
    return None


def discover_companion_devices(hass: HomeAssistant) -> dict[str,str]:
    registry=er.async_get(hass)
    devices: dict[str,str]={}
    for entry in registry.entities.values():
        if entry.platform!="mobile_app" or entry.domain!="sensor" or not entry.device_id:
            continue
        if _metric_unique_id(entry):
            devices.setdefault(entry.device_id, entry.device_id)
    try:
        from homeassistant.helpers import device_registry as dr
        dreg=dr.async_get(hass)
        for did in list(devices):
            dev=dreg.async_get(did)
            if dev: devices[did]=dev.name_by_user or dev.name or did
    except Exception:
        pass
    return devices

class CompanionImporter:
    """Watch current official iOS Health sensors and mirror them into the universal store."""
    def __init__(self,hass:HomeAssistant,runtime,device_id:str|None)->None:
        self.hass=hass;self.runtime=runtime;self.device_id=device_id
        self._bound_device_id: str | None = device_id
        self._needs_device_selection = False
        self._entity_map:dict[str,str]={}
        self._unsubs:list[Any]=[]

    async def async_start(self)->None:
        await self._async_rescan(import_now=True)
        self._unsubs.append(self.hass.bus.async_listen(EVENT_STATE_CHANGED,self._state_changed))
        self._unsubs.append(self.hass.bus.async_listen(er.EVENT_ENTITY_REGISTRY_UPDATED,self._entity_registry_changed))
        self._unsubs.append(async_track_time_interval(self.hass,self._periodic_rescan,timedelta(minutes=15)))

    async def async_stop(self)->None:
        while self._unsubs:
            self._unsubs.pop()()

    @callback
    def _periodic_rescan(self, _now)->None:
        self.hass.async_create_task(self._async_rescan(import_now=True))

    @callback
    def _entity_registry_changed(self, _event: Event)->None:
        self.hass.async_create_task(self._async_rescan(import_now=True))

    async def _async_rescan(self,*,import_now:bool)->None:
        registry=er.async_get(self.hass)
        effective_device_id = self.device_id or self._bound_device_id
        if effective_device_id is None:
            devices = discover_companion_devices(self.hass)
            if len(devices) == 1:
                effective_device_id = next(iter(devices)); self._bound_device_id = effective_device_id; self._needs_device_selection = False
            elif len(devices) > 1:
                self._entity_map = {}; self._needs_device_selection = True; return
            else:
                self._entity_map = {}; self._needs_device_selection = False; return
        mapping={}
        for entry in registry.entities.values():
            if entry.platform!="mobile_app" or entry.domain!="sensor": continue
            if entry.device_id!=effective_device_id: continue
            uid=_metric_unique_id(entry)
            if uid: mapping[entry.entity_id]=uid
        self._entity_map=mapping
        if import_now:
            for entity_id,uid in mapping.items():
                state=self.hass.states.get(entity_id)
                if state: await self._async_import_state(state,uid,registry.async_get(entity_id))

    @property
    def bound_device_id(self) -> str | None:return self._bound_device_id
    @property
    def needs_device_selection(self) -> bool:return self._needs_device_selection
    @property
    def sensor_count(self) -> int:return len(self._entity_map)

    @callback
    def _state_changed(self,event:Event)->None:
        entity_id=event.data.get("entity_id"); uid=self._entity_map.get(entity_id)
        if not uid:return
        state=event.data.get("new_state")
        if state is None:return
        registry=er.async_get(self.hass)
        self.hass.async_create_task(self._async_import_state(state,uid,registry.async_get(entity_id)))

    async def _async_import_state(self,state,uid:str,entry:er.RegistryEntry|None)->None:
        if state.state in (STATE_UNKNOWN,STATE_UNAVAILABLE,"",None):return
        try:value=float(state.state)
        except (TypeError,ValueError):return
        known=COMPANION_METRICS.get(uid)
        type_id=known.type_id if known else f"companion.{uid}"
        domain=known.domain if known else "other"
        unit=(known.unit if known else None) or state.attributes.get("unit_of_measurement")
        aggregation=known.aggregation if known else "latest"
        privacy=known.privacy_class if known else "wellness"
        display=known.name if known else state.attributes.get("friendly_name",uid.replace('_',' ').title())
        stamp=state.last_updated.isoformat()
        digest=hashlib.sha256(f"{state.entity_id}|{stamp}|{state.state}".encode()).hexdigest()[:32]
        source={"name":"Home Assistant Companion","device_name":entry.device_id if entry else None,"bundle_identifier":"io.robbie.HomeAssistant"}
        item={"sample_uuid":f"companion:{digest}","type_id":type_id,"object_kind":"quantity","domain":domain,"display_name":display,"start":stamp,"end":stamp,"numeric_value":value,"unit":unit,"aggregation_kind":aggregation,"privacy_class":privacy,"source":source,"metadata":{"entity_id":state.entity_id}}
        await self.runtime.store.async_ingest([item]); await self.runtime.coordinator.async_refresh_from_store()
