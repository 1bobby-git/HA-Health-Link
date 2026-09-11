"""Zero-friction import of official Home Assistant iOS Apple Health sensors."""
from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
import hashlib
import logging
from typing import Any

from homeassistant.const import (
    EVENT_STATE_CHANGED,
    EVENT_STATE_REPORTED,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_call_later, async_track_time_interval

from .const import COMPANION_METRICS

_LOGGER = logging.getLogger(__name__)
_FLUSH_DELAY_SECONDS = 1.0
_RESCAN_DELAY_SECONDS = 0.5


def _metric_unique_id(entry: er.RegistryEntry) -> str | None:
    """Return the normalized HealthKit metric id for a Companion sensor."""
    uid = str(entry.unique_id or "")
    if uid in COMPANION_METRICS:
        return uid
    for known in COMPANION_METRICS:
        if uid.endswith(known):
            return known
    if "health_" in uid:
        return uid[uid.rfind("health_") :]
    return None


def discover_companion_devices(hass: HomeAssistant) -> dict[str, str]:
    """Discover iOS Companion devices that currently expose Apple Health sensors."""
    registry = er.async_get(hass)
    devices: dict[str, str] = {}
    for entry in registry.entities.values():
        if entry.platform != "mobile_app" or entry.domain != "sensor" or not entry.device_id:
            continue
        if _metric_unique_id(entry):
            devices.setdefault(entry.device_id, entry.device_id)

    device_registry = dr.async_get(hass)
    for device_id in list(devices):
        device = device_registry.async_get(device_id)
        if device:
            devices[device_id] = device.name_by_user or device.name or device_id
    return devices


class CompanionImporter:
    """Mirror official iOS Apple Health sensor updates into the universal store."""

    def __init__(self, hass: HomeAssistant, runtime, device_id: str | None) -> None:
        self.hass = hass
        self.runtime = runtime
        self.device_id = device_id
        self._bound_device_id: str | None = device_id
        self._needs_device_selection = False
        self._entity_map: dict[str, str] = {}
        self._pending: dict[str, tuple[Any, str, er.RegistryEntry | None]] = {}
        self._last_sample_uuid: dict[str, str] = {}
        self._unsubs: list[Callable[[], None]] = []
        self._flush_unsub: Callable[[], None] | None = None
        self._rescan_unsub: Callable[[], None] | None = None

    async def async_start(self) -> None:
        """Start automatic discovery and ingestion."""
        await self._async_rescan(import_now=True)
        self._unsubs.append(
            self.hass.bus.async_listen(EVENT_STATE_CHANGED, self._state_changed)
        )
        # Health sensors can legitimately report the same value again at a later time.
        # EVENT_STATE_REPORTED preserves those samples even when the state text is unchanged.
        self._unsubs.append(
            self.hass.bus.async_listen(EVENT_STATE_REPORTED, self._state_reported)
        )
        self._unsubs.append(
            self.hass.bus.async_listen(
                er.EVENT_ENTITY_REGISTRY_UPDATED, self._entity_registry_changed
            )
        )
        self._unsubs.append(
            async_track_time_interval(
                self.hass, self._periodic_rescan, timedelta(minutes=15)
            )
        )

    async def async_stop(self) -> None:
        """Stop listeners and pending timers."""
        if self._flush_unsub is not None:
            self._flush_unsub()
            self._flush_unsub = None
        if self._rescan_unsub is not None:
            self._rescan_unsub()
            self._rescan_unsub = None
        self._pending.clear()
        while self._unsubs:
            self._unsubs.pop()()

    @callback
    def _periodic_rescan(self, _now) -> None:
        self.hass.async_create_task(self._async_rescan(import_now=True))

    @callback
    def _entity_registry_changed(self, _event: Event) -> None:
        """Coalesce registry bursts and discover newly enabled Health sensors quickly."""
        if self._rescan_unsub is not None:
            return
        self._rescan_unsub = async_call_later(
            self.hass, _RESCAN_DELAY_SECONDS, self._scheduled_rescan
        )

    @callback
    def _scheduled_rescan(self, _now) -> None:
        self._rescan_unsub = None
        self.hass.async_create_task(self._async_rescan(import_now=True))

    async def _async_rescan(self, *, import_now: bool) -> None:
        registry = er.async_get(self.hass)
        effective_device_id = self.device_id or self._bound_device_id
        if effective_device_id is None:
            devices = discover_companion_devices(self.hass)
            if len(devices) == 1:
                effective_device_id = next(iter(devices))
                self._bound_device_id = effective_device_id
                self._needs_device_selection = False
            elif len(devices) > 1:
                self._entity_map = {}
                self._needs_device_selection = True
                return
            else:
                self._entity_map = {}
                self._needs_device_selection = False
                return

        mapping: dict[str, str] = {}
        for entry in registry.entities.values():
            if entry.platform != "mobile_app" or entry.domain != "sensor":
                continue
            if entry.device_id != effective_device_id:
                continue
            uid = _metric_unique_id(entry)
            if uid:
                mapping[entry.entity_id] = uid
        self._entity_map = mapping

        if not import_now:
            return

        items = []
        for entity_id, uid in mapping.items():
            state = self.hass.states.get(entity_id)
            if state is None:
                continue
            item = self._state_to_item(state, uid, registry.async_get(entity_id))
            if item is not None:
                items.append(item)
        if items:
            await self.runtime.store.async_ingest(items)
            await self.runtime.coordinator.async_refresh_from_store()

    @property
    def bound_device_id(self) -> str | None:
        return self._bound_device_id

    @property
    def needs_device_selection(self) -> bool:
        return self._needs_device_selection

    @property
    def sensor_count(self) -> int:
        return len(self._entity_map)

    @callback
    def _state_changed(self, event: Event) -> None:
        self._queue_event_state(event)

    @callback
    def _state_reported(self, event: Event) -> None:
        self._queue_event_state(event)

    @callback
    def _queue_event_state(self, event: Event) -> None:
        entity_id = event.data.get("entity_id")
        uid = self._entity_map.get(entity_id)
        if not uid:
            return
        state = event.data.get("new_state")
        if state is None:
            return
        registry = er.async_get(self.hass)
        self._pending[entity_id] = (state, uid, registry.async_get(entity_id))
        if self._flush_unsub is None:
            self._flush_unsub = async_call_later(
                self.hass, _FLUSH_DELAY_SECONDS, self._scheduled_flush
            )

    @callback
    def _scheduled_flush(self, _now) -> None:
        self._flush_unsub = None
        self.hass.async_create_task(self._async_flush_pending())

    async def _async_flush_pending(self) -> None:
        pending = list(self._pending.values())
        self._pending.clear()
        items = [
            item
            for state, uid, entry in pending
            if (item := self._state_to_item(state, uid, entry)) is not None
        ]
        if not items:
            return
        await self.runtime.store.async_ingest(items)
        await self.runtime.coordinator.async_refresh_from_store()

    def _state_to_item(
        self, state, uid: str, entry: er.RegistryEntry | None
    ) -> dict[str, Any] | None:
        """Convert a Companion sensor state to the universal HealthLink envelope."""
        if state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE, "", None):
            return None
        try:
            value = float(state.state)
        except (TypeError, ValueError):
            return None

        known = COMPANION_METRICS.get(uid)
        type_id = known.type_id if known else f"companion.{uid}"
        domain = known.domain if known else "other"
        unit = (known.unit if known else None) or state.attributes.get(
            "unit_of_measurement"
        )
        aggregation = known.aggregation if known else "latest"
        privacy = known.privacy_class if known else "wellness"
        display = (
            known.name
            if known
            else state.attributes.get("friendly_name", uid.replace("_", " ").title())
        )

        reported = getattr(state, "last_reported", None) or state.last_updated
        stamp = reported.isoformat()
        digest = hashlib.sha256(
            f"{state.entity_id}|{stamp}|{state.state}".encode()
        ).hexdigest()[:32]
        sample_uuid = f"companion:{digest}"
        if self._last_sample_uuid.get(state.entity_id) == sample_uuid:
            return None
        self._last_sample_uuid[state.entity_id] = sample_uuid

        device_name = None
        if entry and entry.device_id:
            device = dr.async_get(self.hass).async_get(entry.device_id)
            if device:
                device_name = device.name_by_user or device.name or entry.device_id

        return {
            "sample_uuid": sample_uuid,
            "type_id": type_id,
            "object_kind": "quantity",
            "domain": domain,
            "display_name": display,
            "start": stamp,
            "end": stamp,
            "numeric_value": value,
            "unit": unit,
            "aggregation_kind": aggregation,
            "privacy_class": privacy,
            "source": {
                "name": "Home Assistant Companion",
                "device_name": device_name,
                "bundle_identifier": "io.robbie.HomeAssistant",
            },
            "metadata": {"entity_id": state.entity_id},
        }
