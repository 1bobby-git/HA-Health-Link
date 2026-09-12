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
from .options_data import HealthDataOptionsMixin
from .profile_support import (
    normalize_device_ids as _normalize_device_ids,
    entry_device_ids as _entry_companion_device_ids,
    devices_in_use as _devices_in_use,
)
from .const import (
    CONF_BASELINE_WINDOW,
    CONF_BRIDGE_SECRET,
    CONF_COMPANION_DEVICE_ID,
    CONF_COMPANION_DEVICE_IDS,
    CONF_ENABLE_COMPOSER,
    CONF_ENABLE_CONTEXT,
    CONF_GOAL_STEPS,
    CONF_GOAL_EXERCISE_MINUTES,
    CONF_GOAL_ACTIVE_ENERGY,
    CONF_GOAL_WATER_ML,
    CONF_GOAL_SLEEP_MINUTES,
    DEFAULT_GOAL_STEPS,
    DEFAULT_GOAL_EXERCISE_MINUTES,
    DEFAULT_GOAL_ACTIVE_ENERGY,
    DEFAULT_GOAL_WATER_ML,
    DEFAULT_GOAL_SLEEP_MINUTES,
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
                if CONF_COMPANION_DEVICE_IDS not in user_input and len(available) == 1:
                    selected = [next(iter(available))]

                if available and not selected:
                    errors[CONF_COMPANION_DEVICE_IDS] = "select_device"
                elif any(device_id not in devices for device_id in selected):
                    errors[CONF_COMPANION_DEVICE_IDS] = "device_not_found"
                elif _devices_in_use(self.hass, selected):
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
        if available:
            schema[
                vol.Required(CONF_COMPANION_DEVICE_IDS, default=list(available) if len(available) == 1 else [])
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


class HealthLinkOptionsFlow(HealthDataOptionsMixin, OptionsFlowWithReload):
    """Expose only options that are useful and implemented for end users."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        self._options = dict(self.config_entry.options)
        return self.async_show_menu(step_id="init", menu_options=["general", "metrics", "import_data"])

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

        # Keep previously selected, temporarily offline devices visible in options.
        from homeassistant.helpers import device_registry as dr
        registry = dr.async_get(self.hass)
        for device_id in current_ids:
            if device_id not in selectable:
                device = registry.async_get(device_id)
                selectable[device_id] = (device.name_by_user or device.name) if device else device_id

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
            elif any(device_id not in selectable for device_id in selected):
                errors[CONF_COMPANION_DEVICE_IDS] = "device_not_found"
            else:
                self._options.update(user_input)
                self._options[CONF_COMPANION_DEVICE_IDS] = selected
                self._options.pop(CONF_COMPANION_DEVICE_ID, None)
                return await self.async_step_goals()

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

    async def async_step_goals(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Optional user-defined wellness goals; zero means disabled."""
        if user_input is not None:
            self._options.update(user_input)
            return await self.async_step_privacy()
        def goal_field(key: str, default: float, maximum: float):
            return vol.Optional(key, default=self._options.get(key, default)), vol.All(vol.Coerce(float), vol.Range(min=0, max=maximum))
        fields = {}
        for key, default, maximum in (
            (CONF_GOAL_STEPS, DEFAULT_GOAL_STEPS, 100000),
            (CONF_GOAL_EXERCISE_MINUTES, DEFAULT_GOAL_EXERCISE_MINUTES, 1440),
            (CONF_GOAL_ACTIVE_ENERGY, DEFAULT_GOAL_ACTIVE_ENERGY, 10000),
            (CONF_GOAL_WATER_ML, DEFAULT_GOAL_WATER_ML, 20000),
            (CONF_GOAL_SLEEP_MINUTES, DEFAULT_GOAL_SLEEP_MINUTES, 1440),
        ):
            field, validator = goal_field(key, default, maximum); fields[field] = validator
        return self.async_show_form(step_id="goals", data_schema=vol.Schema(fields))

    async def async_step_privacy(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._options.update(user_input)
            # Re-check on final save: another profile may have claimed a phone
            # while this two-step dialog was open.
            selected = _normalize_device_ids(self._options.get(CONF_COMPANION_DEVICE_IDS))
            if _devices_in_use(self.hass, selected, exclude_entry_id=self.config_entry.entry_id):
                return await self.async_step_general({CONF_COMPANION_DEVICE_IDS: selected})
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
