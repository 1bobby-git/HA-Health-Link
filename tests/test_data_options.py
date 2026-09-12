"""Native form, waveform privacy and import lifecycle regression tests."""
import asyncio
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from custom_components.health_link.options_data import HealthDataOptionsMixin
from custom_components.health_link.data_features import _finish_worker
from custom_components.health_link.health_import import ECG_TYPE


class Flow(HealthDataOptionsMixin):
    def __init__(self, entry):
        self.config_entry = entry
        self.async_show_form = Mock(side_effect=lambda **kw: {"type": "form", **kw})
        self.async_create_entry = Mock(side_effect=lambda **kw: {"type": "create_entry", **kw})
        self.async_abort = Mock(side_effect=lambda **kw: {"type": "abort", **kw})


def test_native_exposure_requires_sensitive_consent_and_preserves_existing_options(monkeypatch):
    from custom_components.health_link import options_data
    async def run():
        store = NS(async_catalog=AsyncMock(return_value=[{
            "type_id": ECG_TYPE, "object_kind": "ecg", "domain": "heart",
            "privacy_class": "sensitive", "display_name": "ECG", "exposed": 0,
        }]), async_audit=AsyncMock())
        entry = NS(entry_id="profile-a", title="A", state=ConfigEntryState.LOADED,
                   disabled_by=None, runtime_data=NS(store=store),
                   options={"companion_device_ids": ["phone-a"], "goal_steps": 6000})
        persist = AsyncMock()
        monkeypatch.setattr(options_data, "set_exposure", persist)
        flow = Flow(entry)
        form = await flow.async_step_metrics()
        assert form["step_id"] == "metrics"
        rejected = await flow.async_step_metrics({"exposed_metrics": [ECG_TYPE], "enable_sensitive": False})
        assert rejected["errors"]["base"] == "sensitive_disabled"
        persist.assert_not_awaited()
        saved = await flow.async_step_metrics({"exposed_metrics": [ECG_TYPE], "enable_sensitive": True})
        assert saved["type"] == "create_entry"
        assert saved["data"]["goal_steps"] == 6000
        assert saved["data"]["companion_device_ids"] == ["phone-a"]
        assert saved["data"]["enable_sensitive"] is True
        persist.assert_awaited_once_with(store, [ECG_TYPE], {ECG_TYPE: (await store.async_catalog())[0]})
    asyncio.run(run())


def test_import_form_requires_profile_confirmation_before_starting_work():
    async def run():
        entry = NS(title="A", state=ConfigEntryState.LOADED, disabled_by=None,
                   options={}, runtime_data=NS())
        flow = Flow(entry)
        flow.hass = NS(async_create_task=Mock())
        result = await flow.async_step_import_data({"file_id": "file-a", "confirm_profile": False})
        assert result["errors"]["confirm_profile"] == "confirm_profile_required"
        flow.hass.async_create_task.assert_not_called()
    asyncio.run(run())


def test_executor_cancellation_keeps_import_lock_until_work_finishes():
    async def run():
        future = asyncio.get_running_loop().create_future()
        lock = asyncio.Lock()
        async def work():
            async with lock:
                return await _finish_worker(future)
        task = asyncio.create_task(work())
        await asyncio.sleep(0)
        task.cancel()
        await asyncio.sleep(0)
        assert lock.locked()
        assert not future.cancelled()
        future.set_result("done")
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not lock.locked()
    asyncio.run(run())


def test_native_ecg_image_instantiates_and_clears_cache_after_privacy_revocation(tmp_path, monkeypatch):
    from custom_components.health_link.image import HealthLinkECGImage
    from homeassistant.components import image as image_module
    monkeypatch.setattr(image_module, "get_async_client", lambda *args, **kwargs: NS())
    async def run():
        hass = HomeAssistant(str(tmp_path))
        coordinator = NS(last_update_success=True, data={"ecg": {"latest": {
            "object_uuid": "example", "point_count": 2,
        }}})
        runtime = NS(coordinator=coordinator, store=NS(profile_id="a", _run=AsyncMock(return_value={
            "points": [[0, 0], [1, 0.1]],
        })))
        entry = NS(entry_id="a", title="A", options={"enable_sensitive": True})
        image = HealthLinkECGImage(hass, runtime, entry)
        image.hass = hass
        assert image.available
        first = await image.async_image()
        assert first.startswith(b"\x89PNG")
        assert image._image_bytes == first
        entry.options = {"enable_sensitive": False}
        assert not image.available
        assert await image.async_image() is None
        assert image._image_bytes is None
    asyncio.run(run())


def test_live_companion_update_is_coalesced_while_import_commits(monkeypatch):
    from custom_components.health_link import companion
    async def run():
        lock = asyncio.Lock()
        await lock.acquire()
        hass = NS(data={"health_link": {"import_locks": {"a": lock}}})
        runtime = NS(coordinator=NS(entry=NS(entry_id="a")), store=NS(async_ingest=AsyncMock()))
        importer = companion.CompanionImporter(hass, runtime, ["phone-a"])
        importer._pending = {"sensor.health_steps": (NS(), "health_steps", None)}
        schedule = Mock(return_value=lambda: None)
        monkeypatch.setattr(companion, "async_call_later", schedule)
        await importer._async_flush_pending()
        assert "sensor.health_steps" in importer._pending
        schedule.assert_called_once()
        runtime.store.async_ingest.assert_not_awaited()
        lock.release()
        await importer.async_stop()
    asyncio.run(run())
