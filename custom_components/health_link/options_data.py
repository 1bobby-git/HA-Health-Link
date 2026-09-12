"""Native Home Assistant options for data exposure and file imports."""
from __future__ import annotations

import asyncio
import uuid

import voluptuous as vol
from homeassistant.helpers.selector import FileSelector, FileSelectorConfig, SelectSelector, SelectSelectorConfig

from .const import DEFAULT_EXPOSED_TYPE_IDS, DOMAIN
from .data_features import exposable, import_uploaded, sensitive, set_exposure
from .health_import import HealthImportError
from .profile_summary import profile_loaded


def _import_jobs(hass):
    """Keep an import task attached to Home Assistant, not to one browser flow."""
    if getattr(hass, "data", None) is None:
        hass.data = {}
    return hass.data.setdefault(DOMAIN, {}).setdefault("option_import_jobs", {})


class HealthDataOptionsMixin:
    """Extends the existing native settings; never redirects to Studio."""

    async def async_step_metrics(self, user_input=None):
        entry = self.config_entry
        if not profile_loaded(entry):
            return self.async_abort(reason="profile_unavailable")
        catalog = await entry.runtime_data.store.async_catalog()
        choices = {item["type_id"]: item for item in catalog
                   if exposable(item) and item["type_id"] not in DEFAULT_EXPOSED_TYPE_IDS}
        if not choices:
            return self.async_abort(reason="no_discovered_metrics")
        errors = {}
        if user_input is not None:
            selected = user_input.get("exposed_metrics", [])
            allow = bool(user_input.get("enable_sensitive", False))
            if not isinstance(selected, list) or any(type_id not in choices for type_id in selected):
                errors["base"] = "invalid_metric_selection"
            elif not allow and any(sensitive(choices[type_id]) for type_id in selected):
                errors["base"] = "sensitive_disabled"
            else:
                await set_exposure(entry.runtime_data.store, selected, choices)
                await entry.runtime_data.store.async_audit("native_metric_exposure")
                return self.async_create_entry(title="", data={**entry.options, "enable_sensitive": allow,
                                                               "exposure_revision": uuid.uuid4().hex})
        enabled = bool(entry.options.get("enable_sensitive", False))
        options = [{"value": type_id,
                    "label": f"{item.get('domain', 'other')} · {item.get('display_name') or type_id}"
                             + (" · 민감 / sensitive" if sensitive(item) else "")}
                   for type_id, item in choices.items()]
        selected = [type_id for type_id, item in choices.items() if item.get("exposed") and (enabled or not sensitive(item))]
        return self.async_show_form(step_id="metrics", errors=errors, data_schema=vol.Schema({
            vol.Optional("exposed_metrics", default=selected): SelectSelector(SelectSelectorConfig(options=options, multiple=True, mode="dropdown")),
            vol.Optional("enable_sensitive", default=enabled): bool,
        }))

    async def async_step_import_data(self, user_input=None):
        if not profile_loaded(self.config_entry):
            return self.async_abort(reason="profile_unavailable")

        # A browser/WebSocket reconnect must not orphan a long-running import.
        # Reopening this menu attaches to the already running (or just-finished)
        # Home Assistant task instead of starting the same file again.
        jobs = _import_jobs(self.hass)
        existing = jobs.get(self.config_entry.entry_id)
        if existing is not None:
            self._health_import_task = existing
            return await self.async_step_import_progress()

        errors = {}
        if user_input is not None:
            if user_input.get("confirm_profile") is not True:
                errors["confirm_profile"] = "confirm_profile_required"
            elif user_input.get("include_sensitive") and not self.config_entry.options.get("enable_sensitive", False):
                errors["include_sensitive"] = "sensitive_disabled"
            else:
                # ECG-only is deliberately the default. Apple export.zip can contain
                # years of export.xml history, which is unrelated to ECG waveform
                # import and can take a long time to parse on a small HA host.
                scope = user_input.get("scope", "ecg")
                task = self.hass.async_create_task(import_uploaded(
                    self.hass, self.config_entry, user_input["file_id"],
                    include_sensitive=user_input.get("include_sensitive", False), scope=scope))
                jobs[self.config_entry.entry_id] = task
                self._health_import_task = task
                return await self.async_step_import_progress()
        return self.async_show_form(step_id="import_data", errors=errors,
            description_placeholders={"profile": self.config_entry.title}, data_schema=vol.Schema({
                vol.Required("file_id"): FileSelector(FileSelectorConfig(accept=".zip,.xml,.json,.csv")),
                vol.Optional("scope", default="ecg"): SelectSelector(SelectSelectorConfig(options=[
                    {"value": "ecg", "label": "ECG만 · 빠름/권장 / ECG only · fast/recommended"},
                    {"value": "all", "label": "전체 건강 원본 + ECG · 대용량/느림 / Full Health export + ECG · large/slow"}], mode="dropdown")),
                vol.Optional("include_sensitive", default=False): bool,
                vol.Required("confirm_profile", default=False): bool,
            }))

    async def async_step_import_progress(self, user_input=None):
        jobs = _import_jobs(self.hass)
        task = getattr(self, "_health_import_task", None) or jobs.get(self.config_entry.entry_id)
        if task is None:
            return await self.async_step_import_data()
        self._health_import_task = task
        if not task.done():
            return self.async_show_progress(step_id="import_progress", progress_action="importing_health_data", progress_task=task)
        try:
            self._health_import_result = task.result()
            self._health_import_error = None
        except asyncio.CancelledError:
            self._health_import_result = {}
            self._health_import_error = "import_cancelled"
        except HealthImportError as err:
            self._health_import_result = {}
            self._health_import_error = str(err)
        except Exception:
            self._health_import_result = {}
            self._health_import_error = "invalid_import_file"
        return self.async_show_progress_done(next_step_id="import_result")

    async def async_step_import_result(self, user_input=None):
        jobs = _import_jobs(self.hass)
        if self._health_import_error:
            jobs.pop(self.config_entry.entry_id, None)
            return self.async_abort(reason="health_import_failed", description_placeholders={"error": self._health_import_error})
        if user_input is not None:
            jobs.pop(self.config_entry.entry_id, None)
            # Saving a revision invokes OptionsFlowWithReload without replacing
            # goals, linked phones, profile identity, entity IDs or stored history.
            return self.async_create_entry(title="", data={**self.config_entry.options, "import_revision": uuid.uuid4().hex})
        result = self._health_import_result
        return self.async_show_form(step_id="import_result", data_schema=vol.Schema({}),
            description_placeholders={key: str(result.get(key, 0)) for key in
                ("inserted", "updated", "ecg_new", "skipped_sensitive", "skipped_unsupported")})
