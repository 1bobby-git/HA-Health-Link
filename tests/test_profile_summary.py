"""Configured profiles remain visible without exposing stale health data."""
from types import SimpleNamespace as NS
from homeassistant.config_entries import ConfigEntryState
from custom_components.health_link.profile_summary import profile_loaded, profile_summary


def make_entry(state, runtime=None):
    return NS(entry_id="waiting", title="가족 건강", data={"profile_id": "p_family", "companion_device_ids": ["phone-b"]},
              options={}, state=state, runtime_data=runtime, disabled_by=None)


def test_failed_profile_is_listed_without_health_values():
    e = make_entry(ConfigEntryState.SETUP_ERROR, NS(coordinator=NS(data={"steps_today": 7777})))
    result = profile_summary(e)
    assert result["title"] == "가족 건강"
    assert result["available"] is False
    assert "steps_today" not in result
    assert result["companion_device_ids"] == ["phone-b"]
    assert not profile_loaded(e)


def test_multiphone_summary_and_bridge_state_are_accurate():
    runtime = NS(store=NS(profile_id="p_family"), webhook_id="allocated-but-not-registered",
                 coordinator=NS(data={"steps_today": 20}),
                 companion=NS(sensor_count=4, needs_device_selection=False,
                              bound_device_id=None, bound_device_ids=("phone-b", "phone-c")))
    result = profile_summary(make_entry(ConfigEntryState.LOADED, runtime))
    assert result["available"]
    assert result["companion_device_count"] == 2
    assert result["companion_device_ids"] == ["phone-b", "phone-c"]
    assert result["bridge_ready"] is False


def test_status_lists_all_entries_and_keeps_admin_guard():
    import inspect
    from custom_components.health_link.websocket import ws_status
    source = inspect.getsource(ws_status)
    assert "require_admin" in source
    assert "hass.config_entries.async_entries(DOMAIN)" in source
