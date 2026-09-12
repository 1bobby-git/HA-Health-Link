"""Administrator-only WebSocket API for HealthLink Studio."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
from typing import Any

import voluptuous as vol

from homeassistant.auth.permissions import filter_entity_ids_by_permission
from homeassistant.auth.permissions.const import POLICY_READ
from homeassistant.components import webhook, websocket_api
from homeassistant.components.recorder import get_instance, history
from homeassistant.components.websocket_api import ActiveConnection
from homeassistant.core import HomeAssistant, callback

from .analytics.engine import align_previous, observed_best_range, pearson
from .composer.engine import ComposerError, SafeFormula
from .const import CONF_BRIDGE_SECRET, CONF_PROFILE_ID, DOMAIN
from .models import HealthLinkRuntimeData
from .profile_summary import profile_loaded, profile_summary

_ID_RE=re.compile(r"^[a-z0-9_\-]{1,64}$")

def _entries(hass:HomeAssistant)->list[Any]:return [e for e in hass.config_entries.async_entries(DOMAIN) if profile_loaded(e)]
def _entry(hass:HomeAssistant,msg:dict[str,Any]):
    entries=_entries(hass);wanted=msg.get("config_entry_id")
    if wanted:
        found=next((e for e in entries if e.entry_id==wanted),None)
        if found is None:raise ValueError("HealthLink profile not found")
        return found
    if len(entries)==1:return entries[0]
    raise ValueError("config_entry_id is required when multiple profiles exist")
def _send_profile_error(connection,msg,err)->None:connection.send_error(msg["id"],"profile_not_found",str(err))

def _entry_summary(entry)->dict[str,Any]:
    return profile_summary(entry)

@callback
def async_register_websocket_api(hass:HomeAssistant)->None:
    for command in (ws_status,ws_catalog,ws_samples,ws_structured_get,ws_series_get,ws_metric_exposure,ws_composer_list,ws_composer_validate,ws_composer_save,ws_composer_delete,ws_pairing_info,ws_timeline,ws_insight_correlation,ws_optimizer_observe):websocket_api.async_register_command(hass,command)

@websocket_api.websocket_command({vol.Required("type"):"health_link/status"})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_status(hass,connection,msg):connection.send_result(msg["id"],[_entry_summary(e) for e in hass.config_entries.async_entries(DOMAIN)])

@websocket_api.websocket_command({vol.Required("type"):"health_link/catalog/list",vol.Optional("config_entry_id"):str})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_catalog(hass,connection,msg):
    try:e=_entry(hass,msg)
    except ValueError as err:_send_profile_error(connection,msg,err);return
    connection.send_result(msg["id"],await e.runtime_data.store.async_catalog())

@websocket_api.websocket_command({vol.Required("type"):"health_link/samples/query",vol.Optional("config_entry_id"):str,vol.Required("type_id"):str,vol.Optional("hours",default=24):vol.All(vol.Coerce(int),vol.Range(min=1,max=8760)),vol.Optional("limit",default=1000):vol.All(vol.Coerce(int),vol.Range(min=1,max=10000))})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_samples(hass,connection,msg):
    try:e=_entry(hass,msg)
    except ValueError as err:_send_profile_error(connection,msg,err);return
    end=datetime.now(timezone.utc);start=end-timedelta(hours=msg["hours"])
    connection.send_result(msg["id"],await e.runtime_data.store.async_series(msg["type_id"],start.isoformat(),end.isoformat(),msg["limit"]))

@websocket_api.websocket_command({vol.Required("type"):"health_link/structured/get",vol.Optional("config_entry_id"):str,vol.Required("object_uuid"):str})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_structured_get(hass,connection,msg):
    try:e=_entry(hass,msg)
    except ValueError as err:_send_profile_error(connection,msg,err);return
    result=await e.runtime_data.store.async_structured_object(msg["object_uuid"])
    if result is None:connection.send_error(msg["id"],"object_not_found","Structured object not found");return
    connection.send_result(msg["id"],result)

@websocket_api.websocket_command({vol.Required("type"):"health_link/series/get",vol.Optional("config_entry_id"):str,vol.Required("series_uuid"):str,vol.Optional("limit",default=256):vol.All(vol.Coerce(int),vol.Range(min=1,max=2048))})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_series_get(hass,connection,msg):
    try:e=_entry(hass,msg)
    except ValueError as err:_send_profile_error(connection,msg,err);return
    chunks=await e.runtime_data.store.async_series_chunks(msg["series_uuid"],limit=msg["limit"]);connection.send_result(msg["id"],{"series_uuid":msg["series_uuid"],"chunks":chunks})

@websocket_api.websocket_command({vol.Required("type"):"health_link/catalog/expose",vol.Optional("config_entry_id"):str,vol.Required("type_id"):str,vol.Required("exposed"):bool})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_metric_exposure(hass,connection,msg):
    try:e=_entry(hass,msg)
    except ValueError as err:_send_profile_error(connection,msg,err);return
    runtime=e.runtime_data
    if msg["exposed"] and not e.options.get("enable_sensitive",False):
        metric=next((x for x in await runtime.store.async_catalog() if x.get("type_id")==msg["type_id"]),None)
        if metric and metric.get("privacy_class") not in {None,"wellness","standard"}:connection.send_error(msg["id"],"sensitive_disabled","Enable sensitive metric exposure in HealthLink options first");return
    if not await runtime.store.async_set_exposed(msg["type_id"],msg["exposed"]):connection.send_error(msg["id"],"metric_not_found","HealthKit metric not found");return
    await runtime.store.async_audit("expose_metric" if msg["exposed"] else "hide_metric",actor=connection.user.id,object_type=msg["type_id"])
    connection.send_result(msg["id"],{"ok":True,"reload_required":True});await hass.config_entries.async_reload(e.entry_id)

@websocket_api.websocket_command({vol.Required("type"):"health_link/composer/list",vol.Optional("config_entry_id"):str})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_composer_list(hass,connection,msg):
    try:e=_entry(hass,msg)
    except ValueError as err:_send_profile_error(connection,msg,err);return
    connection.send_result(msg["id"],await e.runtime_data.store.async_list_composers())

def _validate_definition(definition:dict[str,Any])->tuple[bool,str|None]:
    formula=str(definition.get("formula") or "");inputs=definition.get("inputs")
    if not isinstance(inputs,dict) or not inputs:return False,"At least one input is required"
    if len(inputs)>20:return False,"Too many inputs"
    for key,source in inputs.items():
        if not _ID_RE.fullmatch(str(key)):return False,f"Invalid input name: {key}"
        if not isinstance(source,dict) or source.get("source") not in {"healthkit","ha"}:return False,f"Invalid source for {key}"
        if source.get("source")=="healthkit" and not source.get("type_id"):return False,f"HealthKit type is required for {key}"
        if source.get("source")=="ha" and not source.get("entity_id"):return False,f"Entity is required for {key}"
    try:SafeFormula(formula)
    except ComposerError as err:return False,str(err)
    return True,None

@websocket_api.websocket_command({vol.Required("type"):"health_link/composer/validate",vol.Required("definition"):dict})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_composer_validate(hass,connection,msg):
    valid,error=_validate_definition(msg["definition"]);connection.send_result(msg["id"],{"valid":valid,"error":error})

@websocket_api.websocket_command({vol.Required("type"):"health_link/composer/save",vol.Optional("config_entry_id"):str,vol.Required("definition_id"):str,vol.Required("name"):str,vol.Required("definition"):dict})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_composer_save(hass,connection,msg):
    did=msg["definition_id"]
    if not _ID_RE.fullmatch(did):connection.send_error(msg["id"],"invalid_id","Use lowercase letters, numbers, _ or -");return
    valid,error=_validate_definition(msg["definition"])
    if not valid:connection.send_error(msg["id"],"invalid_definition",error or "Invalid definition");return
    try:e=_entry(hass,msg)
    except ValueError as err:_send_profile_error(connection,msg,err);return
    await e.runtime_data.store.async_save_composer(did,msg["name"][:96],msg["definition"]);await e.runtime_data.store.async_audit("composer_save",actor=connection.user.id,object_type=did)
    connection.send_result(msg["id"],{"ok":True,"reload_required":True});await hass.config_entries.async_reload(e.entry_id)

@websocket_api.websocket_command({vol.Required("type"):"health_link/composer/delete",vol.Optional("config_entry_id"):str,vol.Required("definition_id"):str})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_composer_delete(hass,connection,msg):
    try:e=_entry(hass,msg)
    except ValueError as err:_send_profile_error(connection,msg,err);return
    removed=await e.runtime_data.store.async_delete_composer(msg["definition_id"]);await e.runtime_data.store.async_audit("composer_delete",actor=connection.user.id,object_type=msg["definition_id"])
    connection.send_result(msg["id"],{"ok":True,"removed":removed})
    if removed:await hass.config_entries.async_reload(e.entry_id)

@websocket_api.websocket_command({vol.Required("type"):"health_link/pairing/info",vol.Optional("config_entry_id"):str})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_pairing_info(hass,connection,msg):
    try:e=_entry(hass,msg)
    except ValueError as err:_send_profile_error(connection,msg,err);return
    runtime=e.runtime_data;connection.send_result(msg["id"],{"profile_id":e.data[CONF_PROFILE_ID],"webhook_path":webhook.async_generate_path(runtime.webhook_id),"bridge_secret":e.data[CONF_BRIDGE_SECRET],"schema_version":1,"warning":"Treat this pairing secret like a password. It is displayed only to administrators."})

async def _ha_history_numeric(hass:HomeAssistant,connection:ActiveConnection,entity_ids:list[str],start:datetime,end:datetime)->dict[str,list[tuple[str,float]]]:
    allowed=filter_entity_ids_by_permission(connection.user,entity_ids,POLICY_READ)
    if not allowed:return {}
    states=await get_instance(hass).async_add_executor_job(history.get_significant_states,hass,start,end,allowed,None,True,False,False,True,False)
    result={}
    for entity_id,values in states.items():
        points=[]
        for state in values:
            try:points.append((state.last_updated.isoformat(),float(state.state)))
            except (AttributeError,TypeError,ValueError):continue
        result[entity_id]=points
    return result

@websocket_api.websocket_command({vol.Required("type"):"health_link/timeline/query",vol.Optional("config_entry_id"):str,vol.Required("type_id"):str,vol.Optional("entity_ids",default=[]):[str],vol.Optional("hours",default=24):vol.All(vol.Coerce(int),vol.Range(min=1,max=2160))})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_timeline(hass,connection,msg):
    try:e=_entry(hass,msg)
    except ValueError as err:_send_profile_error(connection,msg,err);return
    end=datetime.now(timezone.utc);start=end-timedelta(hours=msg["hours"])
    health=await e.runtime_data.store.async_series(msg["type_id"],start.isoformat(),end.isoformat(),5000);home=await _ha_history_numeric(hass,connection,msg.get("entity_ids",[])[:10],start,end)
    events=[{"time":r.get("timestamp"),"source":"healthkit","id":msg["type_id"],"value":r.get("value"),"unit":r.get("unit")} for r in health]
    for entity_id,points in home.items():events.extend({"time":stamp,"source":"home_assistant","id":entity_id,"value":value} for stamp,value in points)
    events.sort(key=lambda x:x.get("time") or "");connection.send_result(msg["id"],{"start":start.isoformat(),"end":end.isoformat(),"events":events[-5000:]})

@websocket_api.websocket_command({vol.Required("type"):"health_link/insights/correlation",vol.Optional("config_entry_id"):str,vol.Required("type_id"):str,vol.Required("entity_id"):str,vol.Optional("days",default=30):vol.All(vol.Coerce(int),vol.Range(min=1,max=365))})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_insight_correlation(hass,connection,msg):
    try:e=_entry(hass,msg)
    except ValueError as err:_send_profile_error(connection,msg,err);return
    end=datetime.now(timezone.utc);start=end-timedelta(days=msg["days"]);rows=await e.runtime_data.store.async_series(msg["type_id"],start.isoformat(),end.isoformat(),10000)
    health_points=[(r["timestamp"],r["value"]) for r in rows if r.get("value") is not None];home=await _ha_history_numeric(hass,connection,[msg["entity_id"]],start,end);result=pearson(align_previous(health_points,home.get(msg["entity_id"],[])))
    connection.send_result(msg["id"],{"pairs":result.pairs,"correlation":result.correlation,"strength":result.strength,"direction":result.direction,"note":"Observed association only. This does not establish medical or causal effect."})

@websocket_api.websocket_command({vol.Required("type"):"health_link/optimizer/observe",vol.Optional("config_entry_id"):str,vol.Required("outcome_type_id"):str,vol.Required("environment_entity_id"):str,vol.Optional("days",default=60):vol.All(vol.Coerce(int),vol.Range(min=7,max=365)),vol.Optional("goal",default="high"):vol.In(["high","low"])})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_optimizer_observe(hass,connection,msg):
    try:e=_entry(hass,msg)
    except ValueError as err:_send_profile_error(connection,msg,err);return
    end=datetime.now(timezone.utc);start=end-timedelta(days=msg["days"]);rows=await e.runtime_data.store.async_series(msg["outcome_type_id"],start.isoformat(),end.isoformat(),10000)
    hp=[(r["timestamp"],r["value"]) for r in rows if r.get("value") is not None];home=await _ha_history_numeric(hass,connection,[msg["environment_entity_id"]],start,end);pairs=align_previous(hp,home.get(msg["environment_entity_id"],[]));best=observed_best_range(pairs,goal=msg["goal"]);association=pearson(pairs)
    connection.send_result(msg["id"],{"preferred_observed_range":best,"pairs":association.pairs,"correlation":association.correlation,"note":"Observational only; not a medical recommendation or independent automatic-control trigger."})
