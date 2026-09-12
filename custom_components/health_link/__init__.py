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
    CONF_COMPANION_DEVICE_IDS,
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
from . import data_features as _data_features
from .data_features import register_data_services
from .ecg_import_fast import read_file as _fast_health_read_file
from .storage import HealthLinkStore
from .webhook import async_register_bridge_webhook, async_unregister_bridge_webhook
from .websocket import async_register_websocket_api

# data_features resolves ``read_file`` at call time. Point it at the scoped
# parser so both the native Options Flow and service action get the same fast,
# localized ECG-only behavior without changing the full-health import path.
_data_features.read_file = _fast_health_read_file

_LOGGER = logging.getLogger(__name__)
_PANEL_PATH = "health-link-studio"
_LEGACY_PANEL_PATH = "health-link"
_STATIC_URL = "/health_link_static"
_DATA_STATIC_READY = "frontend_static_ready"
_DATA_PANEL_READY = "frontend_panel_ready"
_DATA_WS_READY = "ws_ready"
_CONFIG_MINOR_VERSION = 3


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up global HealthLink facilities."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    async_register_services(hass)
    register_data_services(hass)
    if not domain_data.get(_DATA_WS_READY):
        async_register_websocket_api(hass)
        domain_data[_DATA_WS_READY] = True
    return True


async def _async_setup_frontend(hass: HomeAssistant) -> None:
    """Register HealthLink Studio once as a normal sidebar panel."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if not domain_data.get(_DATA_STATIC_READY):
        static_dir = Path(__file__).parent / "frontend"
        await hass.http.async_register_static_paths(
            [StaticPathConfig(_STATIC_URL, str(static_dir), cache_headers=True)]
        )
        domain_data[_DATA_STATIC_READY] = True
    if domain_data.get(_DATA_PANEL_READY):
        return
    # v0.1.x briefly used the custom panel as the integration configuration
    # destination. Remove that registration explicitly before adding Studio as
    # a normal sidebar-only feature panel. The integration gear must stay on
    # Home Assistant's native Options Flow.
    frontend.async_remove_panel(hass, _LEGACY_PANEL_PATH, warn_if_unknown=False)
    frontend.async_remove_panel(hass, _PANEL_PATH, warn_if_unknown=False)
    await panel_custom.async_register_panel(
        hass=hass,
        frontend_url_path=_PANEL_PATH,
        webcomponent_name="health-link-panel",
        sidebar_title="HealthLink",
        sidebar_icon="mdi:heart-pulse",
        module_url=f"{_STATIC_URL}/health-link-panel-modern.js?v={VERSION}",
        require_admin=True,
        handle_safe_area=True,
    )
    domain_data[_DATA_PANEL_READY] = True


def _configured_companion_device_ids(entry: ConfigEntry) -> list[str] | None:
    """Return configured multi-device ids with legacy single-device fallback."""
    configured = entry.options.get(CONF_COMPANION_DEVICE_IDS)
    if configured is None:
        configured = entry.data.get(CONF_COMPANION_DEVICE_IDS)
    if configured is not None:
        if isinstance(configured, str):
            return [configured] if configured else []
        return [str(device_id) for device_id in configured if device_id]

    legacy = entry.options.get(CONF_COMPANION_DEVICE_ID) or entry.data.get(
        CONF_COMPANION_DEVICE_ID
    )
    return [str(legacy)] if legacy else None


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
    runtime = HealthLinkRuntimeData(
        store=store,
        coordinator=coordinator,
        webhook_id=entry.data[CONF_WEBHOOK_ID],
    )
    entry.runtime_data = runtime

    source_mode = entry.options.get(CONF_SOURCE_MODE, DEFAULT_SOURCE_MODE)

    # The normal user path is the official Home Assistant Companion app. Do not
    # expose an internet-reachable Bridge endpoint unless Bridge mode was
    # explicitly selected by an existing advanced configuration.
    if source_mode in {"bridge", "both"}:
        async_register_bridge_webhook(hass, entry)

    if source_mode in {"auto", "companion", "both"}:
        importer = CompanionImporter(
            hass,
            runtime,
            _configured_companion_device_ids(entry),
        )
        runtime.companion = importer
        await importer.async_start()

    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await _async_setup_frontend(hass)
    _LOGGER.info("HealthLink profile %s loaded", entry.title)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a HealthLink health profile."""
    runtime: HealthLinkRuntimeData = entry.runtime_data
    if runtime.companion is not None:
        await runtime.companion.async_stop()

    # Unregister is intentionally unconditional. It is safe when not present and
    # guarantees that changing away from Bridge mode cannot leave an old endpoint.
    async_unregister_bridge_webhook(hass, entry)
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        for unsub in runtime.unload_callbacks:
            unsub()
        remaining = [
            other
            for other in hass.config_entries.async_entries(DOMAIN)
            if other.entry_id != entry.entry_id
            and getattr(other, "runtime_data", None)
        ]
        if not remaining:
            frontend.async_remove_panel(hass, _PANEL_PATH, warn_if_unknown=False)
            frontend.async_remove_panel(hass, _LEGACY_PANEL_PATH, warn_if_unknown=False)
            hass.data.get(DOMAIN, {}).pop(_DATA_PANEL_READY, None)
    return unloaded


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate older HealthLink config entries without losing the selected iPhone."""
    if entry.version > 1:
        return False

    if entry.version == 1 and entry.minor_version < _CONFIG_MINOR_VERSION:
        data = dict(entry.data)
        options = dict(entry.options)
        if (
            CONF_COMPANION_DEVICE_IDS not in data
            and CONF_COMPANION_DEVICE_IDS not in options
        ):
            legacy = options.get(CONF_COMPANION_DEVICE_ID) or data.get(
                CONF_COMPANION_DEVICE_ID
            )
            data[CONF_COMPANION_DEVICE_IDS] = [str(legacy)] if legacy else []
        hass.config_entries.async_update_entry(
            entry,
            data=data,
            options=options,
            minor_version=_CONFIG_MINOR_VERSION,
        )
    return True
