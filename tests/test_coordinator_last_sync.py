"""A timezone-naive last_sync must never break the coordinator snapshot.

Live writes are always UTC-aware, but a migrated or externally-edited meta row
could be naive. Subtracting a naive value from an aware ``now`` raises
TypeError, which previously escaped the ValueError-only guard and broke every
derived entity.
"""
from __future__ import annotations

import asyncio
from contextlib import closing
from types import SimpleNamespace as NS

from homeassistant.core import HomeAssistant

from custom_components.health_link.coordinator import HealthLinkCoordinator
from custom_components.health_link.storage import HealthLinkStore


def _seed(store: HealthLinkStore, last_sync: str) -> None:
    with closing(store._connect()) as con, con:
        con.execute(
            "INSERT INTO meta(profile_id,key,value) VALUES(?,?,?) "
            "ON CONFLICT(profile_id,key) DO UPDATE SET value=excluded.value",
            (store.profile_id, "last_sync", last_sync),
        )


def _snapshot(tmp_path, last_sync: str) -> dict:
    async def run() -> dict:
        hass = HomeAssistant(str(tmp_path))
        store = HealthLinkStore(hass, tmp_path / "profile.db", "profile")
        await store.async_initialize(
            config_entry_id="profile", display_name="Synthetic", timezone_name="UTC"
        )
        _seed(store, last_sync)
        entry = NS(entry_id="profile", options={"stale_hours": 24})
        # Exercise the snapshot logic directly without HA's DataUpdateCoordinator
        # setup, which requires a real ConfigEntry. _build_snapshot only reads
        # self.store, self.entry and self.hass.
        coordinator = HealthLinkCoordinator.__new__(HealthLinkCoordinator)
        coordinator.store = store
        coordinator.entry = entry
        coordinator.hass = hass
        return await coordinator._build_snapshot()

    return asyncio.run(run())


def test_naive_last_sync_does_not_break_snapshot(tmp_path):
    snapshot = _snapshot(tmp_path, "2020-01-01T00:00:00")
    # An old naive timestamp is treated as UTC, so latency is a large positive
    # number and the profile is correctly reported as stale.
    assert snapshot["sync_latency_seconds"] is not None
    assert snapshot["sync_latency_seconds"] > 0
    assert snapshot["data_stale"] is True


def test_garbage_last_sync_is_tolerated(tmp_path):
    snapshot = _snapshot(tmp_path, "not-a-timestamp")
    assert snapshot["sync_latency_seconds"] is None
    assert snapshot["data_stale"] is True
