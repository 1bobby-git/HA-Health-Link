"""Zero-friction import of official Home Assistant iOS Apple Health sensors."""
from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import timedelta
import hashlib
import logging
from typing import Any

from homeassistant.components.recorder import get_instance, history
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

from .const import COMPANION_METRICS, CONF_COMPANION_DEVICE_IDS, DOMAIN
from .profile_support import discover_ios_devices, devices_in_use

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
    """List registered iOS devices, even before Apple Health Labs is enabled."""
    return discover_ios_devices(hass)


def _normalize_device_ids(device_ids: str | Iterable[str] | None) -> frozenset[str]:
    """Normalize one or many Companion device ids."""
    if device_ids is None:
        return frozenset()
    if isinstance(device_ids, str):
        return frozenset({device_ids}) if device_ids else frozenset()
    return frozenset(str(device_id) for device_id in device_ids if device_id)


class CompanionImporter:
    """Mirror official iOS Apple Health sensor updates into the universal store."""

    def __init__(
        self,
        hass: HomeAssistant,
        runtime,
        device_ids: str | Iterable[str] | None,
    ) -> None:
        self.hass = hass
        self.runtime = runtime
        self.device_ids = _normalize_device_ids(device_ids)
        self._bound_device_ids: set[str] = set(self.device_ids)
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
            self.hass.bus.async_listen(
                EVENT_STATE_CHANGED, self._state_changed,
                event_filter=self._state_reported_filter,
            )
        )
        # Health sensors can legitimately report the same value again at a later time.
        # EVENT_STATE_REPORTED preserves those samples even when the state text is unchanged.
        # Home Assistant requires a callback event_filter for this high-volume event.
        self._unsubs.append(
            self.hass.bus.async_listen(
                EVENT_STATE_REPORTED,
                self._state_reported,
                event_filter=self._state_reported_filter,
            )
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
        effective_device_ids = set(self.device_ids or self._bound_device_ids)
        profile_entry = self.runtime.coordinator.entry
        if not effective_device_ids:
            devices = discover_companion_devices(self.hass)
            available = set(devices) - devices_in_use(
                self.hass, devices, exclude_entry_id=profile_entry.entry_id
            )
            # An explicit empty options selection means disconnected. Never undo it.
            explicit_empty = profile_entry.options.get(CONF_COMPANION_DEVICE_IDS) == []
            profiles = self.hass.config_entries.async_entries(DOMAIN)
            if not explicit_empty and len(profiles) == 1 and len(available) == 1:
                effective_device_ids = available
                # Persist the choice before any await, so reloads cannot change people.
                self.hass.config_entries.async_update_entry(
                    profile_entry,
                    data={**profile_entry.data, CONF_COMPANION_DEVICE_IDS: sorted(available)},
                )
            else:
                self._entity_map = {}
                self._pending.clear()
                self._needs_device_selection = bool(devices)
                return
        if devices_in_use(
            self.hass, effective_device_ids, exclude_entry_id=profile_entry.entry_id
        ):
            self._entity_map = {}
            self._pending.clear()
            self._needs_device_selection = True
            return
        self._bound_device_ids = set(effective_device_ids)
        self._needs_device_selection = False

        mapping: dict[str, str] = {}
        for entry in registry.entities.values():
            if entry.platform != "mobile_app" or entry.domain != "sensor":
                continue
            if entry.device_id not in effective_device_ids:
                continue
            uid = _metric_unique_id(entry)
            if uid:
                mapping[entry.entity_id] = uid
        self._entity_map = mapping
        self._pending = {key: item for key, item in self._pending.items() if key in mapping}

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

    async def async_refresh_now(self) -> dict[str, int]:
        """Rescan current HA Apple Health entity states; this does not wake iOS."""
        before = (await self.runtime.store.async_status()).get("sample_count", 0)
        await self._async_rescan(import_now=True)
        after = (await self.runtime.store.async_status()).get("sample_count", 0)
        return {"imported": max(0, int(after) - int(before)), "sensor_count": self.sensor_count}

    async def async_import_recorder_history(self, days: int = 30) -> dict[str, int]:
        """Backfill HealthLink from HA Recorder history of bound Apple Health sensors."""
        await self._async_rescan(import_now=False)
        entity_ids = list(self._entity_map)
        if not entity_ids:
            return {"imported": 0, "entities": 0, "days": days}
        from datetime import datetime, timezone
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=max(1, min(int(days), 3650)))
        states = await get_instance(self.hass).async_add_executor_job(
            history.get_significant_states, self.hass, start, end, entity_ids, None, True, False, False, True, False
        )
        registry = er.async_get(self.hass)
        items = []
        # Keep a call-local UUID set because historical rows can repeat.
        seen: set[str] = set()
        for entity_id, values in states.items():
            uid = self._entity_map.get(entity_id)
            entry = registry.async_get(entity_id)
            if not uid:
                continue
            for state in values:
                item = self._state_to_item(state, uid, entry)
                if item is not None and item["sample_uuid"] not in seen:
                    seen.add(item["sample_uuid"]); items.append(item)
        result = await self.runtime.store.async_ingest(items) if items else {"inserted": 0, "updated": 0, "deleted": 0}
        if items:
            await self.runtime.coordinator.async_refresh_from_store()
        return {"imported": int(result.get("inserted", 0)), "updated": int(result.get("updated", 0)), "entities": len(entity_ids), "days": days}

    @property
    def bound_device_ids(self) -> tuple[str, ...]:
        """Return all Companion devices currently bound to this health profile."""
        return tuple(sorted(self._bound_device_ids))

    @property
    def bound_device_id(self) -> str | None:
        """Legacy single-device view used by older config entries."""
        return next(iter(self._bound_device_ids)) if len(self._bound_device_ids) == 1 else None

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
    def _state_reported_filter(self, event_data: dict[str, Any]) -> bool:
        """Accept state_reported only for Health sensors imported by this profile."""
        entity_id = event_data.get("entity_id")
        return isinstance(entity_id, str) and entity_id in self._entity_map

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
            "metadata": {
                "entity_id": state.entity_id,
                "companion_device_id": entry.device_id if entry else None,
                "time_semantics": "home_assistant_reported_at",
                "healthkit_sample_timestamp_available": False,
            },
        }
