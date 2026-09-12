import inspect
from custom_components.health_link import sensor, services

def test_healthlink_specific_sensors_are_enabled_and_raw_duplicates_are_not_new_defaults():
    by_key={d.key:d for d in sensor.DESCRIPTIONS}
    assert by_key["steps_today"].entity_registry_enabled_default is False
    assert by_key["last_sleep_duration"].entity_registry_enabled_default is False
    assert by_key["steps_goal_progress"].entity_registry_enabled_default is True
    assert by_key["daily_focus"].entity_registry_enabled_default is True

def test_services_register_real_response_actions():
    src=inspect.getsource(services.async_register_services)
    for name in ("get_daily_report","get_trends","set_goal","evaluate_routine","record_routine","get_routine_history","analyze_environment"):
        assert f'"{name}"' in src
    assert "SupportsResponse.ONLY" in src
