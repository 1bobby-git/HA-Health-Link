"""HealthLink — local-first Apple Health and Home Assistant context platform."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .companion import CompanionImporter
from .const import (
    CONF_COMPANION_DEVICE_ID,
    CONF_PROFILE_ID,
    CONF_PROFILE_NAME,
    CONF_SOURCE_MODE,
    CONF_WEBHOOK_ID,
    DEFAULT_SOURCE_MODE,
    DOMAIN,
    PLATFORMS,
    VERSION,
)
from .coordinator import HealthLinkCoordinator
from .models import HealthLinkRuntimeData
from .services import async_register_services
from .storage import HealthLinkStore
from .webhook import async_register_bridge_webhook, async_unregister_bridge_webhook
from .websocket import async_register_websocket_api

_LOGGER = logging.getLogger(__name__)
_PANEL_PATH = "health-link"
_STATIC_URL = "/health_link_static"
_DATA_STATIC_READY = "frontend_static_ready"
_DATA_PANEL_READY = "frontend_panel_ready"
_DATA_WS_READY = "ws_ready"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up global HealthLink facilities."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    async_register_services(hass)
    if not domain_data.get(_DATA_WS_READY):
        async_register_websocket_api(hass)
        domain_data[_DATA_WS_READY] = True
    return True


async def _async_setup_frontend(hass: HomeAssistant) -> None:
    domain_data = hass.data.setdefault(DOMAIN, {})
    if not domain_data.get(_DATA_STATIC_READY):
        static_dir = Path(__file__).parent / "frontend"
        await hass.http.async_register_static_paths(
            [StaticPathConfig(_STATIC_URL, str(static_dir), cache_headers=True)]
        )
        domain_data[_DATA_STATIC_READY] = True
    if domain_data.get(_DATA_PANEL_READY):
        return
    await panel_custom.async_register_panel(
        hass=hass,
        frontend_url_path=_PANEL_PATH,
        webcomponent_name="health-link-panel",
        sidebar_title="HealthLink",
        sidebar_icon="mdi:heart-pulse",
        module_url=f"{_STATIC_URL}/health-link-panel.js?v={VERSION}",
        require_admin=True,
        config_panel_domain=DOMAIN,
        handle_safe_area=True,
    )
    domain_data[_DATA_PANEL_READY] = True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a HealthLink health profile."""
    profile_id = entry.data[CONF_PROFILE_ID]
    profile_name = entry.data.get(CONF_PROFILE_NAME, entry.title)
    db_path = Path(hass.config.path("health_link", f"{profile_id}.db"))
    store = HealthLinkStore(hass, db_path, profile_id)
    await store.async_initialize(
        config_entry_id=entry.entry_id,
        display_name=profile_name,
        timezone_name=hass.config.time_zone,
    )
    coordinator = HealthLinkCoordinator(hass, store, entry)
    runtime = HealthLinkRuntimeData(store=store, coordinator=coordinator, webhook_id=entry.data[CONF_WEBHOOK_ID])
    entry.runtime_data = runtime
    async_register_bridge_webhook(hass, entry)
    source_mode = entry.options.get(CONF_SOURCE_MODE, DEFAULT_SOURCE_MODE)
    if source_mode in {"auto", "companion", "both"}:
        importer = CompanionImporter(hass, runtime, entry.options.get(CONF_COMPANION_DEVICE_ID, entry.data.get(CONF_COMPANION_DEVICE_ID)))
        runtime.companion = importer
        await importer.async_start()
    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await _async_setup_frontend(hass)
    _LOGGER.info("HealthLink profile %s loaded", entry.title)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    runtime: HealthLinkRuntimeData = entry.runtime_data
    if runtime.companion is not None:
        await runtime.companion.async_stop()
    async_unregister_bridge_webhook(hass, entry)
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        for unsub in runtime.unload_callbacks:
            unsub()
        remaining = [other for other in hass.config_entries.async_entries(DOMAIN) if other.entry_id != entry.entry_id and getattr(other, "runtime_data", None)]
        if not remaining:
            frontend.async_remove_panel(hass, _PANEL_PATH, warn_if_unknown=False)
            hass.data.get(DOMAIN, {}).pop(_DATA_PANEL_READY, None)
    return unloaded


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if entry.version > 1:
        return False
    return True
