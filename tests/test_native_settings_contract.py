from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_duplicate_summary_entities_stay_enabled_by_default():
    source = (ROOT / "custom_components/health_link/sensor.py").read_text()
    assert "entity_registry_enabled_default=False" not in source
    for key in (
        "steps_today", "active_energy_today", "exercise_time_today",
        "last_sleep_duration", "last_sleep_deep", "last_sleep_rem",
        "last_sleep_efficiency",
    ):
        assert f'key="{key}"' in source

def test_settings_gear_is_not_custom_panel_config():
    source = (ROOT / "custom_components/health_link/__init__.py").read_text()
    assert 'config_panel_domain=' not in source
    assert '_PANEL_PATH = "health-link-studio"' in source
    assert '_LEGACY_PANEL_PATH = "health-link"' in source
    assert 'async_remove_panel(hass, _LEGACY_PANEL_PATH' in source

def test_native_options_flow_remains_available():
    source = (ROOT / "custom_components/health_link/config_flow.py").read_text()
    assert "async_get_options_flow" in source
    assert "class HealthLinkOptionsFlow(OptionsFlowWithReload)" in source
