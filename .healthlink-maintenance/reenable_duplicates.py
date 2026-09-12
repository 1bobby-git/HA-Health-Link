from pathlib import Path

ROOT = Path('.')
p = ROOT / 'custom_components/health_link/sensor.py'
s = p.read_text()
assert 'entity_registry_enabled_default=False' not in s

old = 'from homeassistant.helpers.entity_platform import AddEntitiesCallback\nfrom homeassistant.helpers.update_coordinator import CoordinatorEntity'
new = 'from homeassistant.helpers.entity_platform import AddEntitiesCallback\nfrom homeassistant.helpers import entity_registry as er\nfrom homeassistant.helpers.update_coordinator import CoordinatorEntity'
assert old in s
s = s.replace(old, new, 1)

old = '''CORE_TYPES={
    "HKQuantityTypeIdentifierStepCount","HKQuantityTypeIdentifierActiveEnergyBurned",
    "HKQuantityTypeIdentifierAppleExerciseTime","companion.health_sleep_duration",
    "companion.health_sleep_deep","companion.health_sleep_rem",
}

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    runtime:HealthLinkRuntimeData=entry.runtime_data
'''
new = '''CORE_TYPES={
    "HKQuantityTypeIdentifierStepCount","HKQuantityTypeIdentifierActiveEnergyBurned",
    "HKQuantityTypeIdentifierAppleExerciseTime","companion.health_sleep_duration",
    "companion.health_sleep_deep","companion.health_sleep_rem",
}

# v0.2.0 temporarily changed these entities to disabled-by-default. Restore only
# entries disabled by the integration itself; a user's explicit disabled choice
# must always win.
DUPLICATE_SUMMARY_KEYS=frozenset({
    "steps_today","active_energy_today","exercise_time_today",
    "last_sleep_duration","last_sleep_deep","last_sleep_rem",
    "last_sleep_efficiency",
})

def _reenable_integration_disabled_summaries(hass: HomeAssistant, entry: ConfigEntry) -> None:
    registry=er.async_get(hass)
    for key in DUPLICATE_SUMMARY_KEYS:
        entity_id=registry.async_get_entity_id("sensor",DOMAIN,f"{entry.entry_id}_{key}")
        if not entity_id:
            continue
        registry_entry=registry.async_get(entity_id)
        if registry_entry and registry_entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION:
            registry.async_update_entity(entity_id,disabled_by=None)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    _reenable_integration_disabled_summaries(hass,entry)
    runtime:HealthLinkRuntimeData=entry.runtime_data
'''
assert old in s
s = s.replace(old, new, 1)
p.write_text(s)

p = ROOT / 'tests/test_native_settings_contract.py'
s = p.read_text()
s += '''\n\ndef test_upgrade_restores_only_integration_disabled_summaries(monkeypatch):\n    from types import SimpleNamespace as NS\n    from homeassistant.helpers import entity_registry as er\n    from custom_components.health_link import sensor\n\n    integration = NS(disabled_by=er.RegistryEntryDisabler.INTEGRATION)\n    user = NS(disabled_by=er.RegistryEntryDisabler.USER)\n    entries = {\n        "sensor.integration_disabled": integration,\n        "sensor.user_disabled": user,\n    }\n    ids = {\n        "profile_steps_today": "sensor.integration_disabled",\n        "profile_last_sleep_duration": "sensor.user_disabled",\n    }\n    updates = []\n\n    class Registry:\n        def async_get_entity_id(self, domain, platform, unique_id):\n            assert domain == "sensor" and platform == "health_link"\n            return ids.get(unique_id)\n        def async_get(self, entity_id):\n            return entries.get(entity_id)\n        def async_update_entity(self, entity_id, **changes):\n            updates.append((entity_id, changes))\n\n    monkeypatch.setattr(sensor.er, "async_get", lambda hass: Registry())\n    sensor._reenable_integration_disabled_summaries(NS(), NS(entry_id="profile"))\n    assert updates == [("sensor.integration_disabled", {"disabled_by": None})]\n'''
p.write_text(s)

p = ROOT / 'CHANGELOG.md'
s = p.read_text()
needle = '- Keep the Apple Health summary entities (steps, active energy, exercise time, sleep duration/deep/REM/efficiency) enabled by default even when equivalent Mobile App entities also exist. HealthLink intentionally keeps them because they belong to the HealthLink profile and can be used consistently with its derived context and automations.\n'
assert needle in s
replacement = needle + '- On upgrade from v0.2.0, re-enable those summary entities only when Home Assistant marked them disabled by the integration; entities explicitly disabled by the user remain disabled.\n'
s = s.replace(needle, replacement, 1)
p.write_text(s)
print('safe duplicate summary migration staged')
