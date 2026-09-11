"""Diagnostics for HealthLink. Health values are intentionally excluded."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, VERSION
from .models import HealthLinkRuntimeData


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    runtime: HealthLinkRuntimeData = entry.runtime_data
    status = await runtime.store.async_status()
    catalog = await runtime.store.async_catalog()
    by_domain: dict[str, int] = {}
    for item in catalog:
        domain = str(item.get("domain") or "other")
        by_domain[domain] = by_domain.get(domain, 0) + int(item.get("sample_count") or 0)
    return {
        "integration": {"domain": DOMAIN, "version": VERSION},
        "entry": {
            "title": entry.title,
            "source_mode": entry.options.get("source_mode", "auto"),
            "sensitive_entities_enabled": bool(entry.options.get("enable_sensitive", False)),
            "composer_enabled": bool(entry.options.get("enable_composer", True)),
            "context_enabled": bool(entry.options.get("enable_context", True)),
        },
        "store": {
            "db_size": status.get("db_size", 0),
            "sample_count": status.get("sample_count", 0),
            "type_count": status.get("type_count", 0),
            "exposed_count": status.get("exposed_count", 0),
            "source_count": status.get("source_count", 0),
            "last_sync": status.get("last_sync"),
            "sample_counts_by_domain": by_domain,
        },
        "privacy_note": "No raw health values, bridge secrets, medication names, ECG, FHIR, reproductive or state-of-mind content are included.",
    }
