"""Authenticated HealthLink Bridge ingest endpoint."""
from __future__ import annotations

import json
import logging
from typing import Any

from aiohttp import web
from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_BRIDGE_SECRET,CONF_PROFILE_ID,DOMAIN,EVENT_DATA_UPDATED,MAX_BATCH_ITEMS,SCHEMA_VERSION
from .ingest.security import SignatureError, verify_signed_request
from .models import HealthLinkRuntimeData

_LOGGER = logging.getLogger(__name__)
_MAX_BODY_BYTES = 8 * 1024 * 1024


def async_register_bridge_webhook(hass: HomeAssistant, entry: ConfigEntry) -> None:
    runtime: HealthLinkRuntimeData = entry.runtime_data
    webhook.async_register(hass,DOMAIN,f"HealthLink — {entry.title}",runtime.webhook_id,_handle_bridge_webhook,local_only=False,allowed_methods={"POST"})


def async_unregister_bridge_webhook(hass: HomeAssistant, entry: ConfigEntry) -> None:
    runtime: HealthLinkRuntimeData = entry.runtime_data
    if runtime.webhook_id:webhook.async_unregister(hass, runtime.webhook_id)


async def _handle_bridge_webhook(hass: HomeAssistant, webhook_id: str, request: web.Request) -> web.Response:
    entry = next((item for item in hass.config_entries.async_entries(DOMAIN) if getattr(item,"runtime_data",None) and item.runtime_data.webhook_id == webhook_id),None)
    if entry is None:return web.json_response({"ok": False}, status=404)
    runtime: HealthLinkRuntimeData = entry.runtime_data
    if request.content_length is not None and request.content_length > _MAX_BODY_BYTES:return web.json_response({"ok": False, "error": "payload_too_large"}, status=413)
    body = await request.read()
    if len(body) > _MAX_BODY_BYTES:return web.json_response({"ok": False, "error": "payload_too_large"}, status=413)
    try:signed = verify_signed_request(request.headers, body, entry.data[CONF_BRIDGE_SECRET])
    except SignatureError as err:
        _LOGGER.warning("Rejected Bridge request: %s", err);return web.json_response({"ok": False, "error": "authentication_failed"}, status=401)
    last_sequence = await runtime.store.async_last_sequence(signed.bridge_id)
    if signed.sequence <= last_sequence:return web.json_response({"ok": True, "duplicate": True, "sequence": signed.sequence})
    try:payload: dict[str, Any] = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError):return web.json_response({"ok": False, "error": "invalid_json"}, status=400)
    if payload.get("schema_version") != SCHEMA_VERSION:return web.json_response({"ok": False, "error": "schema_version_unsupported", "supported": SCHEMA_VERSION},status=409)
    if payload.get("profile_id") != entry.data[CONF_PROFILE_ID]:return web.json_response({"ok": False, "error": "profile_mismatch"}, status=403)
    if str(payload.get("bridge_id") or "") != signed.bridge_id:return web.json_response({"ok": False, "error": "bridge_mismatch"}, status=403)
    try:payload_sequence = int(payload.get("sequence", -1))
    except (TypeError, ValueError):return web.json_response({"ok": False, "error": "invalid_sequence"}, status=400)
    if payload_sequence != signed.sequence:return web.json_response({"ok": False, "error": "sequence_mismatch"}, status=400)
    items = payload.get("items")
    if not isinstance(items, list) or len(items) > MAX_BATCH_ITEMS:return web.json_response({"ok": False, "error": "invalid_batch"}, status=400)
    try:result = await runtime.store.async_ingest(items, sequence=signed.sequence)
    except ValueError:return web.json_response({"ok": False, "error": "invalid_item"}, status=400)
    await runtime.store.async_commit_sequence(signed.bridge_id, signed.sequence, signed.nonce)
    await runtime.coordinator.async_refresh_from_store()
    hass.bus.async_fire(EVENT_DATA_UPDATED,{"config_entry_id": entry.entry_id,"profile_id": entry.data[CONF_PROFILE_ID],"bridge_id": signed.bridge_id,"sequence": signed.sequence,**result})
    return web.json_response({"ok": True, "sequence": signed.sequence, **result})
