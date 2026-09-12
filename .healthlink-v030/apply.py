"""One-time hash-guarded integration wiring; removed after successful checks."""
from pathlib import Path
import hashlib
import json
import re
import shutil

ROOT = Path.cwd()
COMP = ROOT / 'custom_components/health_link'
EXPECTED = {
    '__init__.py': 'dfbe089fab07b32b33bb591c21e346777c9ec353',
    'config_flow.py': '3191b8983322483a4317b35ee35e63a5756815da',
    'coordinator.py': '1f9c2944a586dde1840fef9981e01401fbe1d41b',
    'sensor.py': '2d2cc49c42674585db58fbc4cbb994686a48cc9f',
    'storage/db.py': 'd01a21f1d633ca002100e759b8a7de5c795026e2',
    'services.py': 'a61da3ee6a8cf8b93b99ac2543723a5ad49a9e0e',
    'companion.py': '85795579f5e76782ab5cd287a5b8b65e4425378a',
}
for name, expected in EXPECTED.items():
    data = (COMP / name).read_bytes()
    actual = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
    assert actual == expected, f'Concurrent source change: {name}'


def change(name, old, new):
    path = COMP / name
    text = path.read_text()
    assert text.count(old) == 1, f'Unsafe patch: {name}: {old[:100]}'
    path.write_text(text.replace(old, new, 1))

change('__init__.py', 'from .services import async_register_services',
       'from .services import async_register_services\nfrom .data_features import register_data_services')
change('__init__.py', '    async_register_services(hass)\n',
       '    async_register_services(hass)\n    register_data_services(hass)\n')
change('config_flow.py', 'from .companion import discover_companion_devices',
       'from .companion import discover_companion_devices\nfrom .options_data import HealthDataOptionsMixin')
change('config_flow.py', 'class HealthLinkOptionsFlow(OptionsFlowWithReload):',
       'class HealthLinkOptionsFlow(HealthDataOptionsMixin, OptionsFlowWithReload):')
change('config_flow.py', '        self._options = dict(self.config_entry.options)\n        return await self.async_step_general(user_input)',
       '        self._options = dict(self.config_entry.options)\n        return self.async_show_menu(step_id="init", menu_options=["general", "metrics", "import_data"])')
change('coordinator.py', 'from .storage import HealthLinkStore',
       'from .storage import HealthLinkStore\nfrom .data_features import exposed_types, ecg_snapshot')
change('coordinator.py', '        exposed=await self.store.async_exposed_types()',
       '        exposed=await exposed_types(self.store, opts)')
change('coordinator.py', '        daily = build_daily_context(snapshot, opts)',
       '        snapshot["ecg"] = await ecg_snapshot(self.store, opts)\n        daily = build_daily_context(snapshot, opts)')
change('sensor.py', 'from .models import HealthLinkRuntimeData',
       'from .models import HealthLinkRuntimeData\nfrom .data_features import exposed_types, sensitive\nfrom .ecg_entities import ecg_enabled, ecg_sensors')
change('sensor.py', '    for info in await runtime.store.async_exposed_types():\n        if info["type_id"] not in CORE_TYPES:',
       '    for info in await exposed_types(runtime.store, entry.options):\n        if info["type_id"] not in CORE_TYPES and info.get("object_kind") in {"quantity", "category", "activity_summary"}:')
change('sensor.py', '    async_add_entities(entities)\n',
       '    if await ecg_enabled(runtime.store, entry.options):\n        entities.extend(ecg_sensors(runtime, entry))\n    async_add_entities(entities)\n')
change('sensor.py', '    def native_value(self):\n        row=(self.coordinator.data or {}).get("raw_metrics",{}).get(self.type_id)',
       '    def available(self):\n        return super().available and (self.entry.options.get("enable_sensitive", False) or not sensitive(self.info))\n    @property\n    def native_value(self):\n        row=(self.coordinator.data or {}).get("raw_metrics",{}).get(self.type_id)')
change('storage/db.py', '    def _ingest_sync(self,items:list[dict[str,Any]],sequence:int|None)->dict[str,int]:',
       '    def _ingest_sync(self,items:list[dict[str,Any]],sequence:int|None,*,update_sync:bool=True)->dict[str,int]:')
change('storage/db.py', '            con.execute("INSERT INTO meta(profile_id,key,value) VALUES(?,?,?) ON CONFLICT(profile_id,key) DO UPDATE SET value=excluded.value",(self.profile_id,"last_sync",now))',
       '            if update_sync:\n                con.execute("INSERT INTO meta(profile_id,key,value) VALUES(?,?,?) ON CONFLICT(profile_id,key) DO UPDATE SET value=excluded.value",(self.profile_id,"last_sync",now))')
change('storage/db.py', '        return int(a)+int(b)',
       '            c=con.execute("DELETE FROM series_chunks WHERE profile_id=? AND end_ts<?",(self.profile_id,cutoff)).rowcount\n        return int(a)+int(b)+int(c)')
change('companion.py', '        privacy = known.privacy_class if known else "wellness"',
       '        privacy = known.privacy_class if known else "sensitive"')
change('health_import.py', '            yield raw_record(dict(element.attrib))',
       '            if _TYPE.fullmatch(element.get("type", "")):\n                yield raw_record(dict(element.attrib))\n            else:\n                yield {"_skip": "unsupported_health_type"}')
# Reading private data through existing actions must enforce the same admin policy.
for handler, action, annotation in (
    ('recalculate', '_recalculate', 'None'),
    ('refresh_baseline', '_refresh_baseline', 'None'),
    ('sync_request', '_sync_request', 'dict[str, Any]'),
    ('daily_report', '_daily_report', 'dict[str, Any]'),
    ('trends', '_trends', 'dict[str, Any]'),
    ('evaluate_routine', '_evaluate_routine', 'dict[str, Any]'),
):
    old = f'    async def handle_{handler}(call: ServiceCall) -> {annotation}:\n'
    change('services.py', old, old + '        await _require_admin(hass, call)\n')
change('services.py', 'from .models import HealthLinkRuntimeData',
       'from .models import HealthLinkRuntimeData\nfrom .profile_summary import profile_loaded')
change('services.py', '[e for e in hass.config_entries.async_entries(DOMAIN) if getattr(e, "runtime_data", None)]',
       '[e for e in hass.config_entries.async_entries(DOMAIN) if profile_loaded(e)]')

path = COMP / 'manifest.json'; manifest = json.loads(path.read_text())
assert manifest['version'] == '0.2.1'
manifest['version'] = '0.3.0'
manifest['dependencies'] = sorted(set(manifest['dependencies']) | {'file_upload'})
manifest['requirements'] = ['defusedxml==0.7.1']
path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
change('const.py', 'VERSION:Final="0.2.1"', 'VERSION:Final="0.3.0"')
change('const.py', 'PLATFORMS:Final=["sensor","binary_sensor"]', 'PLATFORMS:Final=["sensor","binary_sensor","image"]')

path = ROOT / 'tests/test_native_settings_contract.py'
text = path.read_text().replace('class HealthLinkOptionsFlow(OptionsFlowWithReload)',
                               'class HealthLinkOptionsFlow(HealthDataOptionsMixin, OptionsFlowWithReload)')
path.write_text(text)

for language in ('en', 'ko'):
    path = COMP / 'translations' / f'{language}.json'; data = json.loads(path.read_text())
    ko = language == 'ko'; options = data.setdefault('options', {})
    steps = options.setdefault('step', {})
    steps['init'] = {'title': 'HealthLink 설정' if ko else 'HealthLink settings',
        'menu_options': {'general': '기기·목표·개인정보 설정' if ko else 'Devices, goals and privacy',
                         'metrics': '건강 항목 노출' if ko else 'Health metric exposure',
                         'import_data': '건강 원본·ECG 가져오기' if ko else 'Import health records and ECG'}}
    steps['metrics'] = {'title': '건강 항목 노출' if ko else 'Health metric exposure',
        'description': ('실제로 수집한 항목만 표시합니다. 기존 걸음·활동·수면 요약 센서는 그대로 유지됩니다. 민감 항목을 일반 HA 엔티티로 노출하면 HA의 접근 권한을 가진 다른 사용자도 볼 수 있으므로 공유 범위를 확인하세요.' if ko else
                        'Only discovered metrics are listed. Existing steps/activity/sleep summary sensors are preserved. Sensitive values exposed as normal HA entities may be visible to other HA users; verify your sharing and access settings.'),
        'data': {'exposed_metrics': '노출할 건강 항목' if ko else 'Metrics to expose', 'enable_sensitive': '민감 건강 항목 허용' if ko else 'Allow sensitive health metrics'}}
    steps['import_data'] = {'title': '건강 원본·ECG 가져오기' if ko else 'Import health records and ECG',
        'description': ('대상: {profile}. Apple 건강의 export.zip/export.xml, 지원하는 ECG CSV 또는 JSON을 선택하세요(최대 100 MB). ECG는 Labs가 자동 전송하지 않습니다. ECG·기타 민감 자료를 가져오려면 먼저 기기·목표·개인정보 설정에서 민감 건강 항목을 허용하세요. 선택한 파일은 로컬에서 처리 후 삭제되며, 가져온 기록은 이 프로필에 보관됩니다. 다른 가족의 파일을 선택하지 마세요.' if ko else
                        'Target: {profile}. Select Apple Health export.zip/export.xml, supported ECG CSV or JSON (100 MB maximum). Labs does not automatically send ECG. Enable sensitive data in privacy settings before importing ECG or other sensitive records. Files are processed locally and removed; records remain in this profile. Do not select another person\'s file.'),
        'data': {'file_id': '파일 선택' if ko else 'Select file', 'scope': '가져올 범위' if ko else 'Import scope',
                 'include_sensitive': 'ECG 등 민감 자료 포함' if ko else 'Include sensitive records including ECG',
                 'confirm_profile': '이 프로필 본인의 자료임을 확인함' if ko else 'I confirm these records belong to this profile'}}
    steps['import_result'] = {'title': '가져오기 결과' if ko else 'Import result',
        'description': ('신규 저장 항목(파형 조각 포함): {inserted}, 기존 항목 갱신: {updated}, 새 ECG: {ecg_new}, 민감 자료 제외: {skipped_sensitive}, 미지원 항목 제외: {skipped_unsupported}. 완료 후 건강 항목 노출 메뉴에서 원하는 센서를 선택하세요.' if ko else
                        'New stored items (including waveform chunks): {inserted}; updated: {updated}; new ECG records: {ecg_new}; excluded sensitive: {skipped_sensitive}; unsupported: {skipped_unsupported}. Finish, then select desired sensors under Health metric exposure.')}
    options.setdefault('progress', {})['importing_health_data'] = '건강 자료를 검증하고 로컬 저장소로 가져오는 중' if ko else 'Validating and importing health records locally'
    options.setdefault('error', {}).update({
        'confirm_profile_required': '본인 프로필의 자료인지 확인해 주세요.' if ko else 'Confirm the records belong to this profile.',
        'sensitive_disabled': '먼저 개인정보 설정에서 민감 건강 항목을 허용하세요.' if ko else 'Enable sensitive health metrics in privacy settings first.',
        'invalid_metric_selection': '현재 표시된 건강 항목을 선택해 주세요.' if ko else 'Choose a metric listed in this form.'})
    options.setdefault('abort', {}).update({
        'profile_unavailable': '프로필이 로드되지 않았습니다. 기존 설정을 확인한 뒤 다시 시도하세요.' if ko else 'Profile is not loaded. Check its setup and retry.',
        'no_discovered_metrics': '아직 추가로 노출할 건강 항목이 없습니다. iPhone에서 건강 센서를 켜거나 건강 원본 파일을 먼저 가져오세요.' if ko else 'No additional metrics are available. Enable iPhone health sensors or import a health export first.',
        'health_import_failed': '가져오지 못했습니다. 오류 코드: {error}. 파일 형식·크기·날짜·단위·민감자료 허용을 확인하세요.' if ko else 'Import failed. Error code: {error}. Check file format, size, timestamps, units and sensitive-data permission.'})
    entities = data.setdefault('entity', {})
    sensors = entities.setdefault('sensor', {})
    for key, korean, english in (
        ('ecg_record_count', 'ECG 기록 수', 'ECG record count'),
        ('ecg_last_recorded', '마지막 ECG 측정 시각', 'Last ECG recorded'),
        ('ecg_classification', 'ECG 원본 분류 결과', 'ECG source classification'),
        ('ecg_average_heart_rate', 'ECG 평균 심박', 'ECG average heart rate'),
        ('ecg_point_count', 'ECG 파형 측정 수', 'ECG voltage measurement count'),
        ('ecg_duration', 'ECG 기록 길이', 'ECG record duration'),
    ):
        sensors[key] = {'name': korean if ko else english}
    entities.setdefault('image', {})['ecg_waveform'] = {'name': 'ECG 파형 미리보기' if ko else 'ECG waveform preview'}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
if (COMP / 'strings.json').exists():
    shutil.copyfile(COMP / 'translations/en.json', COMP / 'strings.json')

path = COMP / 'services.yaml'
path.write_text(path.read_text() + (ROOT / '.healthlink-v030/services.yaml').read_text())
path = ROOT / 'README.md'; text = path.read_text()
text = re.sub(r'현재 버전: \*\*v[0-9.]+\*\*', '현재 버전: **v0.3.0**', text)
text += '\n\n## v0.3.0: 건강 원본과 ECG\n\n기존 센서·목표·분석·자동화·로고를 유지하며, **네이티브 설정 → 건강 항목 노출 / 건강 원본·ECG 가져오기**를 추가했습니다. 실제 수집된 추가 건강 지표를 선택할 수 있고 Apple 건강 내보내기 파일에서 수치·범주·운동 기록과 지원하는 ECG 자료를 로컬로 가져올 수 있습니다.\n\n**ECG는 현재 HA iOS Labs가 자동으로 보내지 않습니다.** 별도 HealthLink iOS 앱은 없으며, ECG를 보려면 실제 원본 파일을 가져온 후 민감 항목 허용 및 ECG 노출을 선택해야 합니다. 그러면 6개 ECG 요약 센서와 HA 기본 이미지 엔티티인 파형 미리보기를 사용할 수 있습니다. ECG 분류는 입력 자료의 분류이며 HealthLink가 판정하지 않습니다.\n\n[지원 형식·가져오기 절차·자동화 서비스](docs/HEALTH_DATA_IMPORT.md)에서 전체 제한과 사용 예를 확인하세요.\n'
path.write_text(text)
path = ROOT / 'CHANGELOG.md'; text = path.read_text(); anchor = '## [0.2.1]'
assert anchor in text
entry = '''## [0.3.0] - 2026-09-12

### Added
- Native options menu for discovered health metric exposure and local file import.
- Bounded streaming Apple Health XML/ZIP import of quantity, category and workout records, isolated from Companion aggregate series by source and unit.
- ECG JSON and supported Apple-export style English CSV import with explicit timestamp/unit/count validation.
- Six opt-in ECG summary sensors and a native authenticated HA image entity for a non-diagnostic waveform preview.
- Administrator-only catalogue, import, ECG list/detail and paginated waveform response actions; import-complete and new-ECG-record events.

### Fixed
- Historical imports no longer reset the live Companion freshness timestamp.
- Failed parses cannot partially change the live health database; reimports use stable record IDs.
- Sensitive exposure is checked again after permission changes; unknown future Labs metrics are conservative by default.
- Existing report/trend/routine actions now enforce administrator access; unloaded profiles are excluded.
- Purging expired health data also removes expired waveform chunks.

### Preserved
- Native integration settings, duplicate summary sensors, existing profile/entity IDs, approved logos and previous features.
- ECG is not automatically collected through Labs; no private Apple APIs, extra HealthLink iOS app or medical inference.

'''
path.write_text(text.replace(anchor, entry + anchor, 1))
shutil.rmtree(ROOT / '.healthlink-v030')
print('HealthLink v0.3.0 wiring applied; existing source hashes verified.')
