"""One-time, hash-checked repair; removed from the resulting source commit."""
from __future__ import annotations
import base64
import hashlib
import io
import json
from pathlib import Path
import shutil
import runpy

ROOT = Path.cwd()
STAGE = ROOT / '.healthlink-repair'
COMP = ROOT / 'custom_components/health_link'
EXPECTED = {
 'companion.py':'02db4892603dc0f0bcea58a483b225e741bb4575',
 'config_flow.py':'02251c1a2b908acc51f8cc1fdcc9f6c5c597fbe1',
 '__init__.py':'9b422fa362fc2e996590f1ce8eb5ca2572663a45',
 'websocket.py':'da2146974337769380e713d24a9022b9a20e85a0',
 'frontend/health-link-panel.js':'10489bdcf063c7a6bcfe4f3d6ffc152276b57a25',
}

def git_sha(data):
 return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()

for name, sha in EXPECTED.items():
 assert git_sha((COMP/name).read_bytes())==sha, f'Unexpected concurrent change: {name}'


def replace(text, old, new):
 assert text.count(old)==1, f'Unsafe patch: {old[:100]!r}, matches={text.count(old)}'
 return text.replace(old,new)

p=COMP/'companion.py';s=p.read_text()
s=replace(s,'from .const import COMPANION_METRICS','from .const import COMPANION_METRICS, CONF_COMPANION_DEVICE_IDS, DOMAIN\nfrom .profile_support import discover_ios_devices, devices_in_use')
a=s.index('def discover_companion_devices(');b=s.index('\n\ndef _normalize_device_ids',a)
s=s[:a]+'''def discover_companion_devices(hass: HomeAssistant) -> dict[str, str]:
    """List registered iOS devices, even before Apple Health Labs is enabled."""
    return discover_ios_devices(hass)
'''+s[b:]
s=replace(s,'self.hass.bus.async_listen(EVENT_STATE_CHANGED, self._state_changed)', '''self.hass.bus.async_listen(
                EVENT_STATE_CHANGED, self._state_changed,
                event_filter=self._state_reported_filter,
            )''')
a=s.index('        if not effective_device_ids:');b=s.index('\n        mapping: dict[str, str]',a)
s=s[:a]+'''        profile_entry = self.runtime.coordinator.entry
        if not effective_device_ids:
            devices = discover_companion_devices(self.hass)
            available = set(devices) - devices_in_use(
                self.hass, devices, exclude_entry_id=profile_entry.entry_id
            )
            # An explicit empty options selection means disconnected. Never undo it.
            explicit_empty = profile_entry.options.get(CONF_COMPANION_DEVICE_IDS) == []
            profiles = self.hass.config_entries.async_entries(DOMAIN)
            if not explicit_empty and len(profiles) == 1 and len(available) == 1:
                effective_device_ids = available
                # Persist the choice before any await, so reloads cannot change people.
                self.hass.config_entries.async_update_entry(
                    profile_entry,
                    data={**profile_entry.data, CONF_COMPANION_DEVICE_IDS: sorted(available)},
                )
            else:
                self._entity_map = {}
                self._pending.clear()
                self._needs_device_selection = bool(devices)
                return
        if devices_in_use(
            self.hass, effective_device_ids, exclude_entry_id=profile_entry.entry_id
        ):
            self._entity_map = {}
            self._pending.clear()
            self._needs_device_selection = True
            return
        self._bound_device_ids = set(effective_device_ids)
        self._needs_device_selection = False
'''+s[b:]
s=replace(s,'        self._entity_map = mapping\n','''        self._entity_map = mapping
        self._pending = {key: item for key, item in self._pending.items() if key in mapping}
''')
s=replace(s,'            "metadata": {"entity_id": state.entity_id},','''            "metadata": {
                "entity_id": state.entity_id,
                "companion_device_id": entry.device_id if entry else None,
            },''')
p.write_text(s)

p=COMP/'config_flow.py';s=p.read_text()
s=replace(s,'from .companion import discover_companion_devices','''from .companion import discover_companion_devices
from .profile_support import (
    normalize_device_ids as _normalize_device_ids,
    entry_device_ids as _entry_companion_device_ids,
    devices_in_use as _devices_in_use,
)''')
a=s.index('\ndef _normalize_device_ids(');b=s.index('\ndef _device_selector(',a);s=s[:a]+s[b:]
s=replace(s,'        if len(available) > 1:\n','        if available:\n')
s=replace(s,'vol.Required(CONF_COMPANION_DEVICE_IDS, default=[])','vol.Required(CONF_COMPANION_DEVICE_IDS, default=list(available) if len(available) == 1 else [])')
s=replace(s,'''                if not selected and len(available) == 1:
                    selected = [next(iter(available))]

                if _devices_in_use(self.hass, selected):''','''                if CONF_COMPANION_DEVICE_IDS not in user_input and len(available) == 1:
                    selected = [next(iter(available))]

                if available and not selected:
                    errors[CONF_COMPANION_DEVICE_IDS] = "select_device"
                elif any(device_id not in devices for device_id in selected):
                    errors[CONF_COMPANION_DEVICE_IDS] = "device_not_found"
                elif _devices_in_use(self.hass, selected):''')
s=replace(s,'        if user_input is not None:\n            selected = _normalize_device_ids(','''        # Keep previously selected, temporarily offline devices visible in options.
        from homeassistant.helpers import device_registry as dr
        registry = dr.async_get(self.hass)
        for device_id in current_ids:
            if device_id not in selectable:
                device = registry.async_get(device_id)
                selectable[device_id] = (device.name_by_user or device.name) if device else device_id

        if user_input is not None:
            selected = _normalize_device_ids(''')
s=replace(s,'''            if conflicts:
                errors[CONF_COMPANION_DEVICE_IDS] = "device_already_used"
            else:''','''            if conflicts:
                errors[CONF_COMPANION_DEVICE_IDS] = "device_already_used"
            elif any(device_id not in selectable for device_id in selected):
                errors[CONF_COMPANION_DEVICE_IDS] = "device_not_found"
            else:''')
s=replace(s,'''        if user_input is not None:
            self._options.update(user_input)
            return self.async_create_entry(title="", data=self._options)''','''        if user_input is not None:
            self._options.update(user_input)
            # Re-check on final save: another profile may have claimed a phone
            # while this two-step dialog was open.
            selected = _normalize_device_ids(self._options.get(CONF_COMPANION_DEVICE_IDS))
            if _devices_in_use(self.hass, selected, exclude_entry_id=self.config_entry.entry_id):
                return await self.async_step_general({CONF_COMPANION_DEVICE_IDS: selected})
            return self.async_create_entry(title="", data=self._options)''')
p.write_text(s)

p=COMP/'websocket.py';s=p.read_text()
s=replace(s,'from .models import HealthLinkRuntimeData','from .models import HealthLinkRuntimeData\nfrom .profile_summary import profile_loaded, profile_summary')
s=replace(s,'def _entries(hass:HomeAssistant)->list[Any]:return [e for e in hass.config_entries.async_entries(DOMAIN) if getattr(e,"runtime_data",None)]','def _entries(hass:HomeAssistant)->list[Any]:return [e for e in hass.config_entries.async_entries(DOMAIN) if profile_loaded(e)]')
a=s.index('def _entry_summary(');b=s.index('\n@callback\ndef async_register_websocket_api',a)
s=s[:a]+'''def _entry_summary(entry)->dict[str,Any]:
    return profile_summary(entry)
'''+s[b:]
s=replace(s,'[_entry_summary(e) for e in _entries(hass)]','[_entry_summary(e) for e in hass.config_entries.async_entries(DOMAIN)]')
p.write_text(s)

runpy.run_path(str(STAGE/'edit_frontend.py'))
for name in ['profile_support.py','profile_summary.py']:
 shutil.copyfile(STAGE/name,COMP/name)
for name in ['test_profile_support.py','test_profile_summary.py','test_brand_assets.py','test_panel.cjs']:
 shutil.copyfile(STAGE/name,ROOT/'tests'/name)

# Preserve approved artwork pixel-for-pixel; release assets are standard PNG.
from PIL import Image
ART={
 'icon': {'size':(256,256),'pixel_sha':'a4fdcd57771e75acd59b6f3fb44732c178af5b39ecc24d8b15b8aa37dabd34f5','parts':6},
 'logo': {'size':(600,200),'pixel_sha':'3bebcae19526e885cc5562a581a14fe43be97480e37753bbdfbcd1ee2a89a79c','parts':9},
}
for kind,meta in ART.items():
 encoded=''.join((STAGE/f'{kind}.{n}.b64').read_text().strip() for n in range(meta['parts']))
 im=Image.open(io.BytesIO(base64.b64decode(encoded,validate=True))).convert('RGBA')
 assert im.size==meta['size']
 assert hashlib.sha256(im.tobytes()).hexdigest()==meta['pixel_sha'], f'Artwork transport mismatch: {kind}'
 output=COMP/'brand'/f'{kind}.png';output.parent.mkdir(parents=True,exist_ok=True)
 im.save(output,format='PNG',optimize=True)
 with Image.open(output) as check:
  assert check.convert('RGBA').tobytes()==im.tobytes()
 asset='healthlink-icon.png' if kind=='icon' else 'healthlink-logo-wide.png'
 shutil.copyfile(output,ROOT/'assets'/asset)
 if kind=='logo':
  (COMP/'frontend/brand').mkdir(exist_ok=True)
  shutil.copyfile(output,COMP/'frontend/brand/logo.png')

for name,lang in [('ko.json','ko'),('en.json','en')]:
 path=COMP/'translations'/name; data=json.loads(path.read_text())
 errors_ko={"select_device":"이 프로필에 연결할 본인의 iPhone을 선택하세요.","device_not_found":"선택한 기기를 현재 찾을 수 없습니다. 목록을 다시 확인하세요."}
 errors_en={"select_device":"Choose the iPhone(s) belonging to this profile.","device_not_found":"A selected device is no longer available. Check the list again."}
 for section in ['config','options']:
  data[section].setdefault('error',{}).update(errors_ko if lang=='ko' else errors_en)
 step=data['config']['step']['user']
 step['description']=(
  'Home Assistant에 등록된 iPhone을 찾습니다. Apple 건강 센서(Labs)를 아직 켜지 않은 기기도 표시됩니다. 감지된 기기: {device_count}개, 다른 프로필에 연결되지 않은 기기: {available_device_count}개. 사람마다 프로필을 만들고 같은 사람의 iPhone만 선택하세요. 기기가 없으면 프로필을 먼저 만든 후 설정에서 연결할 수 있습니다.' if lang=='ko' else
  'Registered iPhones are listed even before Apple Health Sensors (Labs) is enabled. Found: {device_count}; unassigned: {available_device_count}. Create a profile per person and select only their phones. If no phone is available, create a waiting profile and connect it later in settings.'
 )
 step.setdefault('data_description',{})['companion_device_ids']=(
  'HA 사용자 계정 목록이 아니라 등록된 iPhone 목록입니다. 건강 데이터 수집은 각 iPhone에서 Labs 센서와 읽기 권한을 허용한 후 시작됩니다.' if lang=='ko' else
  'This lists registered iPhones, not HA login accounts. Health collection starts only after Labs sensors and health read access are enabled on each phone.'
 )
 path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')

p=COMP/'manifest.json';data=json.loads(p.read_text());assert data['version']=='0.1.4';data['version']='0.1.5';p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
p=COMP/'const.py';p.write_text(replace(p.read_text(),'VERSION:Final="0.1.4"','VERSION:Final="0.1.5"'))
p=ROOT/'README.md';s=p.read_text();s=s.replace('현재 버전: **v0.1.4**','현재 버전: **v0.1.5**')
s+='''\n\n## v0.1.5: 다른 사용자·iPhone 목록과 로고 수정\n\nHealthLink의 건강 프로필과 HA 로그인 계정은 별개입니다. 가족마다 **설정 → 기기 및 서비스 → HealthLink → 허브 추가**로 건강 프로필을 만들고 해당 사람의 iPhone을 선택하세요. HA 계정만 만들었고 iPhone 앱을 아직 같은 서버에 등록하지 않았다면 기기 목록에는 나타나지 않습니다.\n\n등록된 iPhone은 Apple 건강 센서(Labs)를 켜기 전에도 선택할 수 있습니다. 건강 값 수집에는 각 iPhone의 센서 활성화와 HealthKit 읽기 권한이 필요합니다. 이미 다른 프로필이 사용 중인 기기는 중복 선택되지 않습니다. 연결을 해제한 기기를 기존 설정에서 되살려 가져오지 않습니다.\n\nHealthLink 화면에 모든 등록된 프로필을 표시하고, 연결 대기·설정 실패 프로필도 숨기지 않습니다. 화면에 다시 들어오거나 브라우저로 돌아왔을 때 목록을 갱신하며, 화면이 보이는 동안 15초 간격으로도 갱신합니다. 센서 만들기 입력 중에는 입력 내용을 지우지 않습니다. 관리자 전용 건강 데이터 접근 정책은 변경하지 않았습니다.\n\n배포 과정에서 손상된 PNG를 승인된 원본 이미지로 교체했습니다. 도형·서체·색상·간격은 변경하지 않았습니다. 통합 카드의 로고는 **로컬 Brands Proxy API**, HealthLink 화면도 `brands/access_token` 인증을 포함한 같은 API를 우선 사용합니다. 화면의 로컬 이미지 대체 경로도 포함됩니다. PNG 청크 CRC와 압축 데이터 검사로 잘린 이미지가 다시 배포되지 않게 합니다.\n\n업데이트는 **HACS → HealthLink → v0.1.5 설치 → Home Assistant 재시작** 순서입니다. 기존 건강 프로필과 데이터베이스는 삭제하지 않습니다.\n'''
p.write_text(s)
p=ROOT/'CHANGELOG.md';s=p.read_text();index=s.index('## [0.1.4]');s=s[:index]+'''## [0.1.5] - 2026-09-12

### Fixed
- Discover registered iOS devices before Apple Health Labs has any health entities.
- Show the selector even when exactly one unassigned iPhone remains.
- Keep waiting/failed health profiles visible and refresh the profile list on return and periodically while visible.
- Guard profile switching against stale asynchronous responses; preserve Composer forms during background status updates.
- Respect an explicitly cleared device selection; prevent auto-binding a second profile to an existing person's phone.
- Replace truncated brand PNG files with pixel-identical approved artwork; render Studio branding through authenticated local Brands Proxy API with a local image fallback.
- Add profile discovery/identity, frontend race, and full PNG integrity regression tests.
- Keep administrator-only access, per-profile storage and HA-native Options Flow unchanged.

'''+s[index:];p.write_text(s)
p=ROOT/'.github/workflows/tests.yml';s=p.read_text();s=replace(s,'      - run: node --check custom_components/health_link/frontend/health-link-panel.js','      - run: node --check custom_components/health_link/frontend/health-link-panel.js\n      - run: node --test tests/test_panel.cjs');p.write_text(s)
shutil.rmtree(STAGE)
# Workflow cleanup is committed through the maintainer connector after this run.
print('HealthLink v0.1.5 repair applied; approved artwork and source hashes verified.')
