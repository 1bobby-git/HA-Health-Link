"""System health information for HealthLink."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from .const import DOMAIN, VERSION


async def async_get_system_health_info(hass: HomeAssistant) -> dict[str, object]:
    entries = hass.config_entries.async_entries(DOMAIN)
    return {"version": VERSION, "profiles": len(entries), "local_first": True}
