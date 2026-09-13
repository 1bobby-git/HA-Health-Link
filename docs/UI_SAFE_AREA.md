# Studio 모바일 안전 영역 · v0.3.7

## 재현과 원인

사용자가 제공한 iPhone 화면에서 헤더 로고·메뉴·우측 버튼이 상태 표시줄과 다이내믹 아일랜드에 겹쳤다. v0.3.6은 `panel_custom`에 `handle_safe_area=True`로 등록했지만, 실제 헤더/스크롤 호스트에는 상단 inset 처리가 없었다. 이 옵션은 HA가 패딩을 추가하라는 뜻이 아니라 패널이 직접 처리한다는 선언이다.

공식 계약 확인:
- https://developers.home-assistant.io/blog/2026/07/31/frontend-component-updates-2026.8/#safe-area-handling
- https://github.com/home-assistant/frontend/blob/dev/src/panels/custom/ha-panel-custom.ts

현재 v0.3.6 프런트엔드/브랜딩/로고/설정 소스는 GitHub blob SHA와 일치하는 것을 확인한 로컬 사본으로 시험했다. 합성 HA 상단 inset 62px를 설정한 회귀 테스트는 수정 전 스크롤 영역 y=0으로 실패했고, 수정 후 y=62로 통과했다. 62px는 테스트 조건이지 제품에 고정한 iPhone 여백이 아니다.

## 소유권

`handle_safe_area=True`를 유지한다. 커스텀 요소 `:host`가 상하 inset을 한 번 소비하고, 내부 `.hc-root`는 줄어든 콘텐츠 영역 안에서 스크롤한다. 안전 영역이 스크롤과 함께 사라지지 않는다. `box-sizing:border-box`로 패딩만큼 전체 높이가 늘어나지 않도록 한다.

`--safe-area-inset-*`가 있으면 HA의 값을 사용하고, 없을 때만 `env(safe-area-inset-*,0px)`로 대체한다. HA가 전달한 명시적 0px를 덮어쓰지 않는다. 좌우에는 `--safe-area-content-inset-left/right`를 우선하여 사이드바가 소비한 쪽의 inset을 반복 적용하지 않는다. 내부 wrapper는 가이드의 40/28/20/16px 디자인 여백만 가진다.

네이티브 dialog는 뷰포트 최상위 레이어에 표시되므로 별도로 raw viewport inset을 한 번 소비한다. 모바일 sheet 헤더·푸터의 기존 env()를 중복 적용하지 않도록 기본 여백으로 재정의한다. HA/body의 DOM·스타일, 데이터 API, 엔티티, 저장 구조, 로고 파일은 변경하지 않는다.

## 회귀 검사

- `python tests/frontend/safe_area_browser_checks.py`: 34개 통과. 기존 Studio 26개 테스트를 상속하고 안전 영역 8개를 추가한다.
- 안전 영역이 있는 12개 폭(320,349,350,351,390,416,430,559,560,561,768,870px)을 라이트/다크 각각 검사한다. 기존 17개 폭의 기본 반응형 검사도 유지한다.
- 세로/가로 전환, 반복 갱신, 0px/47px/62px 전환, 좌우 소비 여부, 스크롤, dialog 초안·버튼, 메뉴 이벤트 및 44px 조작 영역을 검사한다.
- `node --test tests/test_studio_branding.cjs`: 기존 로고 4개 + 신규 안전 영역 3개 통과. 기존 CI 진입점 `tests/test_panel.cjs`가 branding 파일을 로드하므로 신규 검사도 연결된다.
- 수정된 JavaScript 구문 검사 통과. 저장소 전체 Python/Node/HACS/Hassfest 결과는 PR CI에서 별도로 확인한다.

실제 iPhone 앱·Safari 엔진·VoiceOver·키보드 표시 중 viewport resize는 미검증이다. Chromium에서 HA의 CSS 변수로 안전 영역을 재현한 결과를 실제 iOS 실기기 시험으로 표현하지 않는다. 원본 PNG SHA와 3:1 비율, 흰색 요약/다크 색상은 기존과 동일하다.
