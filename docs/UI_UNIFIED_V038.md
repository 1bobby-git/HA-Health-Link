# Studio v0.3.8 — 공통 웹 UI와 아이콘 검수

이 문서는 v0.3.6/0.3.7의 Wallet 기준 수치와 과거 검수 기록을 대체하는 최신 UI 적용 기준이다. 사용자 제공 `HA_Component_Web_UI_Design_System_v1.0.md`를 기준으로 한다. 건강 데이터 동작을 재설계하는 변경이 아니다.

## HA Shell과 컴포넌트의 경계

HealthLink는 `panel_custom` 방식이다. Supervisor Ingress 전용 `ha-panel-app`을 복제하거나 부모 DOM을 조작하지 않는다. 커스텀 패널에 전달되는 `narrow`와 hass의 사이드바/키오스크 상태를 읽고, HA가 등록한 실제 `ha-top-app-bar-fixed` 요소를 사용한다. 그 내부 메뉴는 HA의 `ha-menu-button`이다. 생산 코드에서 HA 요소를 재정의하지 않는다.

좁은 상태 또는 사이드바 항상 숨김 상태에서 제목 바를 표시하고 키오스크에서는 표시하지 않는다. 870/871은 사용자 재현 화면의 조건이지 Shell의 임계값으로 하드코딩한 값이 아니다. 컴포넌트 컨테이너가 사이드바 때문에 좁아져도 HA의 narrow 값이 false이면 제목 바를 추가하지 않는다. HA 헤더 높이는 `--header-height`를 따른다.

v0.3.7의 host 안전 영역 처리를 유지한다. 소유한 네이티브 헤더 인스턴스에만 inset 0을 전달하여 중복 소비를 막는다. 바깥 HA나 body의 CSS는 변경하지 않는다. 모달은 독립된 최상위 레이어이므로 기존 raw viewport inset을 사용한다. 화면 전환은 폼이나 본문 DOM을 재생성하지 않는다.

참조한 공식 구현: home-assistant/frontend 태그 `20260826.6`의 `ha-top-app-bar-fixed.ts`, `ha-menu-button.ts`, `hass-loading-screen.ts`, `ha-panel-custom.ts`. 실제 HA에서의 메뉴 컨텍스트 전달과 모바일 플랫폼별 렌더링은 추가 실기기 확인이 필요하다.

## 디자인과 아이콘

최종 스타일 계층은 base STYLES → 원본 로고/흰색 요약/안전 영역 → `health-link-studio-unified.css.js`이다. 마지막 파일이 공통 디자인 수치의 기준이다. 주요 카드 16px, 일반 카드 14px, 버튼 10px, 본문 15px/1.6, 탭 14px/46px, 헤더 72/62/58px, 로고 높이 36/32/28px, 최대 폭 1248px과 여백 40/28/20/16px을 사용한다. 부모 Shell 기준과 컴포넌트 반응형 기준을 혼동하지 않는다.

설정 등에 사용되던 임의의 선 도형을 Pictogrammers의 원본 MDI 경로로 교체했다. 도형을 stroke로 그리지 않고 `fill=currentColor`, `stroke=none`으로 표시한다. SVG는 독립된 20px 정사각형이며 44px 조작 영역 중앙에 놓인다. 제목/대체 이름은 버튼·링크에 제공하고 장식 SVG는 aria-hidden으로 중복 읽기를 막는다. SVG 자체의 포인터 이벤트는 꺼서 도형 위를 눌러도 원래 조작 요소가 클릭된다. 헤더의 연결 끊김 문구가 길어져도 아이콘을 밀어내지 않도록 줄바꿈을 허용한다.

`frontend/licenses/MDI.txt`에 출처와 Apache-2.0 전문을 포함했다. 외부 아이콘 폰트나 원격 이미지 요청을 추가하지 않는다. 승인된 PNG 원본은 변경하지 않았다.

## 안내와 한글 표기 범위

기존 미배포 후보의 ECG 안내와 프런트엔드 표시 테이블을 포함했다. ID, 원본 출처, 사용자 조합 센서 이름을 번역해 덮어쓰지 않는다. 알려지지 않은 항목 이름은 원래 값을 안전하게 표시한다. 영어와 한글 검색을 모두 지원한다.

HA 엔티티 기본 이름과 네이티브 Options Flow 라벨을 바꾸는 별도 Python 작업은 이 릴리스에 포함하지 않았다. 해당 표시 테이블 파일의 저장 요청이 도구의 보안 상태 확인 단계에서 거절되어, 의존하는 backend 변경도 함께 제외했다. `sensor.py`, `options_data.py`, 저장소 및 API는 v0.3.7 그대로다. 실행 중 존재하지 않는 Python 모듈을 import하는 코드가 남지 않도록 했다.

## 실행한 로컬 검수

- `python tests/frontend/studio_browser_checks.py`: 26개 통과.
- `python tests/frontend/unified_browser_checks.py`: 12개 통과.
- `python tests/frontend/branding_browser_checks.py`: 8개 통과.
- `python tests/frontend/safe_area_browser_checks.py`: 8개 통과.
- `node --test tests/test_studio_branding.cjs tests/test_studio_unified.cjs`: 12개 통과.
- 원본 PNG 해시, JavaScript 구문과 수정 Python 파일 컴파일 확인.

추가 스크립트의 load_tests는 상속된 기본 테스트를 반복 실행하지 않는다. 870/871 상태 전환, 좁은 컴포넌트/넓은 Shell, 상하 안전 영역, 두 테마와 연결 끊김, 아이콘 중심/도형/44px 타깃, 초안 유지, 키보드·고대비, 한글/영문 검색, 권한 변경 없는 ECG 안내를 검사한다.

`native_header_fixture.js`는 테스트 환경에만 등록하는 대체 구현이다. 운영 코드에서 import하지 않는다. 따라서 화면 캡처는 실제 HealthLink 모듈과 합성 데이터의 검수 화면이며, 사용자 HA 설치 또는 실제 네이티브 HA/iOS 동작 검증을 의미하지 않는다. 전체 저장소 Python/Node 회귀 검증은 최종 PR CI로 확인한다. 실제 기기 설치·재시작은 실행하지 않는다.
