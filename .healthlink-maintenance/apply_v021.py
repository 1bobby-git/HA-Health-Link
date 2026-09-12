from pathlib import Path
import json

ROOT = Path('.')

# 1) Keep duplicate Apple Health summary entities enabled by default.
p = ROOT / 'custom_components/health_link/sensor.py'
s = p.read_text()
needle = 'entity_registry_enabled_default=False,'
count = s.count(needle)
assert count == 7, f'expected 7 duplicate-summary defaults, found {count}'
s = s.replace(needle, '')
p.write_text(s)

# 2) Make Studio a separate feature panel and actively clear the legacy panel
# registration which older versions could have associated with integration config.
p = ROOT / 'custom_components/health_link/__init__.py'
s = p.read_text()
old = '_PANEL_PATH = "health-link"\n_STATIC_URL = "/health_link_static"'
new = '_PANEL_PATH = "health-link-studio"\n_LEGACY_PANEL_PATH = "health-link"\n_STATIC_URL = "/health_link_static"'
assert old in s
s = s.replace(old, new, 1)
old = '''    if domain_data.get(_DATA_PANEL_READY):
        return
    await panel_custom.async_register_panel('''
new = '''    if domain_data.get(_DATA_PANEL_READY):
        return
    # v0.1.x briefly used the custom panel as the integration configuration
    # destination. Remove that registration explicitly before adding Studio as
    # a normal sidebar-only feature panel. The integration gear must stay on
    # Home Assistant's native Options Flow.
    frontend.async_remove_panel(hass, _LEGACY_PANEL_PATH, warn_if_unknown=False)
    frontend.async_remove_panel(hass, _PANEL_PATH, warn_if_unknown=False)
    await panel_custom.async_register_panel('''
assert old in s
s = s.replace(old, new, 1)
old = '''            frontend.async_remove_panel(hass, _PANEL_PATH, warn_if_unknown=False)
            hass.data.get(DOMAIN, {}).pop(_DATA_PANEL_READY, None)'''
new = '''            frontend.async_remove_panel(hass, _PANEL_PATH, warn_if_unknown=False)
            frontend.async_remove_panel(hass, _LEGACY_PANEL_PATH, warn_if_unknown=False)
            hass.data.get(DOMAIN, {}).pop(_DATA_PANEL_READY, None)'''
assert old in s
s = s.replace(old, new, 1)
assert 'config_panel_domain=' not in s
p.write_text(s)

# 3) Version bump.
p = ROOT / 'custom_components/health_link/manifest.json'
data = json.loads(p.read_text())
assert data['version'] == '0.2.0'
data['version'] = '0.2.1'
p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')

p = ROOT / 'custom_components/health_link/const.py'
s = p.read_text()
assert 'VERSION:Final="0.2.0"' in s
p.write_text(s.replace('VERSION:Final="0.2.0"', 'VERSION:Final="0.2.1"', 1))

# 4) Changelog and README clarify the UX contract.
p = ROOT / 'CHANGELOG.md'
s = p.read_text()
anchor = '## [0.2.0] - 2026-09-12\n'
assert anchor in s
entry = '''## [0.2.1] - 2026-09-12

### Changed
- Keep the Apple Health summary entities (steps, active energy, exercise time, sleep duration/deep/REM/efficiency) enabled by default even when equivalent Mobile App entities also exist. HealthLink intentionally keeps them because they belong to the HealthLink profile and can be used consistently with its derived context and automations.
- The integration settings gear is native Home Assistant configuration only. HealthLink Studio is no longer allowed to act as the integration configuration destination.
- Move the sidebar feature panel to `/health-link-studio` and explicitly remove the legacy `/health-link` panel registration during setup so older cached/runtime registrations cannot keep hijacking the integration settings route.

### UX
- HealthLink Studio remains available for reports, timelines, insights and Composer. Device selection, baselines, personal goals, privacy and retention are configured only through Home Assistant's native Options Flow.

'''
s = s.replace(anchor, entry + anchor, 1)
p.write_text(s)

p = ROOT / 'README.md'
s = p.read_text()
marker = '> HealthLink는 웰니스/컨텍스트 분석용 통합이며 의료기기, 진단 시스템, 치료 판단 도구가 아닙니다.\n'
assert marker in s
note = '''\n> **설정과 Studio는 분리됩니다.** 통합 카드의 톱니바퀴는 Home Assistant 네이티브 설정(연결 iPhone, 기준선, 목표, 개인정보, 보존기간)을 엽니다. `HealthLink Studio`는 보고서·타임라인·인사이트·Composer를 사용하는 기능 화면이며 통합 설정 페이지가 아닙니다.\n> Mobile App의 Apple 건강 센서와 값이 겹쳐도 HealthLink의 기본 요약 센서는 숨기지 않습니다. 동일 원천 데이터를 HealthLink 프로필·파생 컨텍스트·자동화에서 일관되게 참조하기 위한 의도적인 중복입니다.\n'''
s = s.replace(marker, marker + note, 1)
p.write_text(s)

# 5) Regression tests are source-contract tests intentionally independent of HA internals.
p = ROOT / 'tests/test_native_settings_contract.py'
p.write_text('''from pathlib import Path\n\nROOT = Path(__file__).resolve().parents[1]\n\ndef test_duplicate_summary_entities_stay_enabled_by_default():\n    source = (ROOT / "custom_components/health_link/sensor.py").read_text()\n    assert "entity_registry_enabled_default=False" not in source\n    for key in (\n        "steps_today", "active_energy_today", "exercise_time_today",\n        "last_sleep_duration", "last_sleep_deep", "last_sleep_rem",\n        "last_sleep_efficiency",\n    ):\n        assert f'key="{key}"' in source\n\ndef test_settings_gear_is_not_custom_panel_config():\n    source = (ROOT / "custom_components/health_link/__init__.py").read_text()\n    assert 'config_panel_domain=' not in source\n    assert '_PANEL_PATH = "health-link-studio"' in source\n    assert '_LEGACY_PANEL_PATH = "health-link"' in source\n    assert 'async_remove_panel(hass, _LEGACY_PANEL_PATH' in source\n\ndef test_native_options_flow_remains_available():\n    source = (ROOT / "custom_components/health_link/config_flow.py").read_text()\n    assert "async_get_options_flow" in source\n    assert "class HealthLinkOptionsFlow(OptionsFlowWithReload)" in source\n''')

print('HealthLink v0.2.1 native-settings patch applied')
