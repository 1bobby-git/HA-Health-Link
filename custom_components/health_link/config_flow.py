"""UI-first setup flow for HealthLink."""
from __future__ import annotations

from typing import Any, override
import secrets
import uuid

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlowWithReload
from homeassistant.core import callback

from .companion import discover_companion_devices
from .const import CONF_BASELINE_WINDOW,CONF_BRIDGE_SECRET,CONF_COMPANION_DEVICE_ID,CONF_ENABLE_COMPOSER,CONF_ENABLE_CONTEXT,CONF_ENABLE_SENSITIVE,CONF_PROFILE_ID,CONF_PROFILE_NAME,CONF_RAW_RETENTION_DAYS,CONF_SELF_OPTIMIZING,CONF_SOURCE_MODE,CONF_STALE_HOURS,CONF_WEBHOOK_ID,CONF_WRITE_BACK,DEFAULT_BASELINE_WINDOW,DEFAULT_ENABLE_COMPOSER,DEFAULT_ENABLE_CONTEXT,DEFAULT_ENABLE_SENSITIVE,DEFAULT_RAW_RETENTION_DAYS,DEFAULT_SELF_OPTIMIZING,DEFAULT_SOURCE_MODE,DEFAULT_STALE_HOURS,DEFAULT_WRITE_BACK,DOMAIN

class HealthLinkConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION=1;MINOR_VERSION=1
    @staticmethod
    @callback
    @override
    def async_get_options_flow(config_entry:ConfigEntry)->"HealthLinkOptionsFlow":return HealthLinkOptionsFlow()
    async def async_step_user(self,user_input:dict[str,Any]|None=None)->ConfigFlowResult:
        errors={};devices=discover_companion_devices(self.hass)
        if user_input is not None:
            profile_name=str(user_input[CONF_PROFILE_NAME]).strip()
            if not profile_name:errors[CONF_PROFILE_NAME]="profile_name_required"
            else:
                await self.async_set_unique_id(f"health-link-{uuid.uuid4()}")
                selected=next(iter(devices)) if len(devices)==1 and CONF_COMPANION_DEVICE_ID not in user_input else user_input.get(CONF_COMPANION_DEVICE_ID)
                data={CONF_PROFILE_ID:f"p_{secrets.token_hex(12)}",CONF_PROFILE_NAME:profile_name,CONF_COMPANION_DEVICE_ID:selected,CONF_WEBHOOK_ID:secrets.token_hex(32),CONF_BRIDGE_SECRET:secrets.token_urlsafe(48)}
                options={CONF_SOURCE_MODE:DEFAULT_SOURCE_MODE,CONF_ENABLE_SENSITIVE:DEFAULT_ENABLE_SENSITIVE,CONF_RAW_RETENTION_DAYS:DEFAULT_RAW_RETENTION_DAYS,CONF_BASELINE_WINDOW:DEFAULT_BASELINE_WINDOW,CONF_STALE_HOURS:DEFAULT_STALE_HOURS,CONF_ENABLE_COMPOSER:DEFAULT_ENABLE_COMPOSER,CONF_ENABLE_CONTEXT:DEFAULT_ENABLE_CONTEXT,CONF_SELF_OPTIMIZING:DEFAULT_SELF_OPTIMIZING,CONF_WRITE_BACK:DEFAULT_WRITE_BACK}
                return self.async_create_entry(title=profile_name,data=data,options=options)
        language=str(getattr(self.hass.config,"language","") or "").lower(); default_name="내 건강" if language.startswith("ko") else "My Health"
        schema={vol.Required(CONF_PROFILE_NAME,default=default_name):str}
        if len(devices)>1:schema[vol.Required(CONF_COMPANION_DEVICE_ID,default=next(iter(devices)))]=vol.In(devices)
        return self.async_show_form(step_id="user",data_schema=vol.Schema(schema),errors=errors,description_placeholders={"device_count":str(len(devices))})

class HealthLinkOptionsFlow(OptionsFlowWithReload):
    async def async_step_init(self,user_input=None):self._options=dict(self.config_entry.options);return await self.async_step_general(user_input)
    async def async_step_general(self,user_input=None):
        if user_input is not None:self._options.update(user_input);return await self.async_step_privacy()
        language=str(getattr(self.hass.config,"language","") or "").lower()
        labels={"auto":"자동 (권장)","companion":"Home Assistant Companion만","bridge":"HealthLink Bridge만","both":"Companion + Bridge"} if language.startswith("ko") else {"auto":"Automatic (recommended)","companion":"Home Assistant Companion only","bridge":"HealthLink Bridge only","both":"Companion + Bridge"}
        fields={vol.Optional(CONF_SOURCE_MODE,default=self._options.get(CONF_SOURCE_MODE,DEFAULT_SOURCE_MODE)):vol.In(labels),vol.Optional(CONF_BASELINE_WINDOW,default=self._options.get(CONF_BASELINE_WINDOW,DEFAULT_BASELINE_WINDOW)):vol.All(vol.Coerce(int),vol.In([7,28,90,365])),vol.Optional(CONF_STALE_HOURS,default=self._options.get(CONF_STALE_HOURS,DEFAULT_STALE_HOURS)):vol.All(vol.Coerce(int),vol.Range(min=1,max=168)),vol.Optional(CONF_ENABLE_COMPOSER,default=self._options.get(CONF_ENABLE_COMPOSER,DEFAULT_ENABLE_COMPOSER)):bool,vol.Optional(CONF_ENABLE_CONTEXT,default=self._options.get(CONF_ENABLE_CONTEXT,DEFAULT_ENABLE_CONTEXT)):bool}
        devices=discover_companion_devices(self.hass)
        if len(devices)>1:
            current=self._options.get(CONF_COMPANION_DEVICE_ID,self.config_entry.data.get(CONF_COMPANION_DEVICE_ID));current=current if current in devices else next(iter(devices));fields[vol.Required(CONF_COMPANION_DEVICE_ID,default=current)]=vol.In(devices)
        return self.async_show_form(step_id="general",data_schema=vol.Schema(fields))
    async def async_step_privacy(self,user_input=None):
        if user_input is not None:self._options.update(user_input);return self.async_create_entry(title="",data=self._options)
        return self.async_show_form(step_id="privacy",data_schema=vol.Schema({vol.Optional(CONF_RAW_RETENTION_DAYS,default=self._options.get(CONF_RAW_RETENTION_DAYS,DEFAULT_RAW_RETENTION_DAYS)):vol.All(vol.Coerce(int),vol.Range(min=7,max=3650)),vol.Optional(CONF_ENABLE_SENSITIVE,default=self._options.get(CONF_ENABLE_SENSITIVE,DEFAULT_ENABLE_SENSITIVE)):bool,vol.Optional(CONF_SELF_OPTIMIZING,default=self._options.get(CONF_SELF_OPTIMIZING,DEFAULT_SELF_OPTIMIZING)):bool,vol.Optional(CONF_WRITE_BACK,default=self._options.get(CONF_WRITE_BACK,DEFAULT_WRITE_BACK)):bool}))
