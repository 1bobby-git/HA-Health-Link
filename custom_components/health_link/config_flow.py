"""UI-first setup flow for HealthLink."""
from __future__ import annotations

from collections.abc import Iterable
import secrets
from typing import Any, override
import uuid

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .companion import discover_companion_devices
from .const import (
    CONF_BASELINE_WINDOW,
    CONF_BRIDGE_SECRET,
    CONF_COMPANION_DEVICE_ID,
    CONF_COMPANION_DEVICE_IDS,
    CONF_ENABLE_COMPOSER,
    CONF_ENABLE_CONTEXT,
    CONF_ENABLE_SENSITIVE,
    CONF_PROFILE_ID,
    CONF_PROFILE_NAME,
    CONF_RAW_RETENTION_DAYS,
    CONF_SELF_OPTIMIZING,
    CONF_SOURCE_MODE,
    CONF_STALE_HOURS,
    CONF_WEBHOOK_ID,
    CONF_WRITE_BACK,
    DEFAULT_BASELINE_WINDOW,
    DEFAULT_ENABLE_COMPOSER,
    DEFAULT_ENABLE_CONTEXT,
    DEFAULT_ENABLE_SENSITIVE,
    DEFAULT_RAW_RETENTION_DAYS,
    DEFAULT_SELF_OPTIMIZING,
    DEFAULT_SOURCE_MODE,
    DEFAULT_STALE_HOURS,
    DEFAULT_WRITE_BACK,
    DOMAIN,
)


def _normalize_device_ids(value: Any) -> list[str]:
    """Normalize one or many Companion device ids while keeping order stable."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, Iterable):
        return list(dict.fromkeys(str(item) for item in value if item))
    return []


def _entry_companion_device_ids(entry: ConfigEntry) -> set[str]:
    """Return all persisted or currently auto-bound Companion devices for an entry."""
    for container in (entry.options, entry.data):
        configured = _normalize_device_ids(container.get(CONF_COMPANION_DEVICE_IDS))
        if configured:
            return set(configured)

    legacy = entry.options.get(CONF_COMPANION_DEVICE_ID) or entry.data.get(
        CONF_COMPANION_DEVICE_ID
    )
    if legacy:
        return {str(legacy)}

    runtime = getattr(entry, "runtime_data", None)
    companion = getattr(runtime, "companion", None) if runtime is not None else None
    bound_many = getattr(companion, "bound_device_ids", None)
    if bound_many:
        return {str(device_id) for device_id in bound_many}
    bound_one = getattr(companion, "bound_device_id", None)
    return {str(bound_one)} if bound_one else set()


def _devices_in_use(
    hass: HomeAssistant,
    device_ids: Iterable[str],
    *,
    exclude_entry_id: str | None = None,
) -> set[str]:
    """Return requested devices already assigned to another HealthLink profile."""
    requested = {str(device_id) for device_id in device_ids}
    conflicts: set[str] = set()
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.entry_id == exclude_entry_id:
            continue
        conflicts.update(requested & _entry_companion_device_ids(entry))
    return conflicts


def _device_selector(devices: dict[str, str], *, multiple: bool) -> SelectSelector:
    """Build a friendly iPhone selector."""
    return SelectSelector(
        SelectSelectorConfig(
            options=[
                SelectOptionDict(value=device_id, label=name)
                for device_id, name in devices.items()
            ],
            multiple=multiple,
            mode=SelectSelectorMode.DROPDOWN,
        )
    )


class HealthLinkConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle HealthLink setup with the simplest possible default path."""

    VERSION = 1
    MINOR_VERSION = 3

    @staticmethod
    @callback
    @override
    def async_get_options_flow(config_entry: ConfigEntry) -> "HealthLinkOptionsFlow":
        return HealthLinkOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create one personal profile backed by one or more Companion iPhones."""
        errors: dict[str, str] = {}
        devices = discover_companion_devices(self.hass)
        used_elsewhere = _devices_in_use(self.hass, devices)
        available = {
            device_id: name
            for device_id, name in devices.items()
            if device_id not in used_elsewhere
        }

        if user_input is not None:
            profile_name = str(user_input[CONF_PROFILE_NAME]).strip()
            if not profile_name:
                errors[CONF_PROFILE_NAME] = "profile_name_required"
            else:
                selected = _normalize_device_ids(
                    user_input.get(CONF_COMPANION_DEVICE_IDS)
                )
                if not selected and len(available) == 1:
                    selected = [next(iter(available))]

                if _devices_in_use(self.hass, selected):
                    errors[CONF_COMPANION_DEVICE_IDS] = "device_already_used"
                else:
                    profile_id = f"p_{secrets.token_hex(12)}"
                    await self.async_set_unique_id(f"profile:{profile_id}")
                    data = {
                        CONF_PROFILE_ID: profile_id,
                        CONF_PROFILE_NAME: profile_name,
                        CONF_COMPANION_DEVICE_IDS: selected,
                        CONF_WEBHOOK_ID: secrets.token_hex(32),
                        CONF_BRIDGE_SECRET: secrets.token_urlsafe(48),
                    }
                    options = {
                        CONF_SOURCE_MODE: DEFAULT_SOURCE_MODE,
                        CONF_ENABLE_SENSITIVE: DEFAULT_ENABLE_SENSITIVE,
                        CONF_RAW_RETENTION_DAYS: DEFAULT_RAW_RETENTION_DAYS,
                        CONF_BASELINE_WINDOW: DEFAULT_BASELINE_WINDOW,
                        CONF_STALE_HOURS: DEFAULT_STALE_HOURS,
                        CONF_ENABLE_COMPOSER: DEFAULT_ENABLE_COMPOSER,
                        CONF_ENABLE_CONTEXT: DEFAULT_ENABLE_CONTEXT,
                        CONF_SELF_OPTIMIZING: DEFAULT_SELF_OPTIMIZING,
                        CONF_WRITE_BACK: DEFAULT_WRITE_BACK,
                    }
                    return self.async_create_entry(
                        title=profile_name,
                        data=data,
                        options=options,
                    )

        language = str(getattr(self.hass.config, "language", "") or "").lower()
        default_name = "내 건강" if language.startswith("ko") else "My Health"
        schema: dict[Any, Any] = {
            vol.Required(CONF_PROFILE_NAME, default=default_name): str
        }
        if len(available) > 1:
            schema[
                vol.Required(CONF_COMPANION_DEVICE_IDS, default=[])
            ] = _device_selector(available, multiple=True)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema),
            errors=errors,
            description_placeholders={
                "device_count": str(len(devices)),
                "available_device_count": str(len(available)),
            },
        )


class HealthLinkOptionsFlow(OptionsFlowWithReload):
    """Expose only options that are useful and implemented for end users."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        self._options = dict(self.config_entry.options)
        return await self.async_step_general(user_input)

    async def async_step_general(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        current_ids = _entry_companion_device_ids(self.config_entry)
        all_devices = discover_companion_devices(self.hass)
        selectable = {
            device_id: name
            for device_id, name in all_devices.items()
            if device_id in current_ids
            or not _devices_in_use(
                self.hass,
                [device_id],
                exclude_entry_id=self.config_entry.entry_id,
            )
        }

        if user_input is not None:
            selected = _normalize_device_ids(
                user_input.get(CONF_COMPANION_DEVICE_IDS, current_ids)
            )
            conflicts = _devices_in_use(
                self.hass,
                selected,
                exclude_entry_id=self.config_entry.entry_id,
            )
            if conflicts:
                errors[CONF_COMPANION_DEVICE_IDS] = "device_already_used"
            else:
                self._options.update(user_input)
                self._options[CONF_COMPANION_DEVICE_IDS] = selected
                self._options.pop(CONF_COMPANION_DEVICE_ID, None)
                return await self.async_step_privacy()

        fields: dict[Any, Any] = {
            vol.Optional(
                CONF_BASELINE_WINDOW,
                default=self._options.get(
                    CONF_BASELINE_WINDOW, DEFAULT_BASELINE_WINDOW
                ),
            ): vol.All(vol.Coerce(int), vol.In([7, 28, 90, 365])),
            vol.Optional(
                CONF_STALE_HOURS,
                default=self._options.get(CONF_STALE_HOURS, DEFAULT_STALE_HOURS),
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=168)),
            vol.Optional(
                CONF_ENABLE_COMPOSER,
                default=self._options.get(
                    CONF_ENABLE_COMPOSER, DEFAULT_ENABLE_COMPOSER
                ),
            ): bool,
            vol.Optional(
                CONF_ENABLE_CONTEXT,
                default=self._options.get(
                    CONF_ENABLE_CONTEXT, DEFAULT_ENABLE_CONTEXT
                ),
            ): bool,
        }

        if selectable:
            default_selected = [
                device_id for device_id in current_ids if device_id in selectable
            ]
            fields[
                vol.Optional(CONF_COMPANION_DEVICE_IDS, default=default_selected)
            ] = _device_selector(selectable, multiple=True)

        return self.async_show_form(
            step_id="general",
            data_schema=vol.Schema(fields),
            errors=errors,
        )

    async def async_step_privacy(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._options.update(user_input)
            return self.async_create_entry(title="", data=self._options)

        return self.async_show_form(
            step_id="privacy",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_RAW_RETENTION_DAYS,
                        default=self._options.get(
                            CONF_RAW_RETENTION_DAYS, DEFAULT_RAW_RETENTION_DAYS
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=7, max=3650)),
                    vol.Optional(
                        CONF_ENABLE_SENSITIVE,
                        default=self._options.get(
                            CONF_ENABLE_SENSITIVE, DEFAULT_ENABLE_SENSITIVE
                        ),
                    ): bool,
                }
            ),
        )
