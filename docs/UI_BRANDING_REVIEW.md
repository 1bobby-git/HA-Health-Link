# HealthLink Studio · 원본 로고 / 흰색 요약 카드 보완

## 이번 요청과 적용 범위

PR #14의 초기 UI(e392e8c)에 대한 사용자 후속 요청이다. 사용자가 지정한
`custom_components/health_link/brand/logo.png`를 헤더 로고로 사용하고,
Lotto 컴포넌트 스크린샷의 헤더 정렬·여백을 유지하면서 남색 요약을 흰색 카드로 바꾼다.
`UI_DESIGN.md`의 초기 남색 요약 규칙 및 로고 캡처 미검증 기록은 이 문서의 결과로 보완된다.
공통 가이드의 단일 남색 강조는 이번에 사용자가 명시적으로 변경한 예외다.

## 로고

- 기준 파일 Git blob SHA: `5647226142f5b85f69e3c6f280b9337d6dce7278`.
- 원본 크기: 600 × 200px. 원본 PNG 및 기존 frontend/brand/logo.png는 변경하지 않는다.
- HA가 `/health_link_brand/logo.png`에서 canonical `brand/logo.png` 파일을 직접 제공한다.
- 기존 `/health_link_static/brand/logo.png`는 동일 바이트의 로컬 예비 경로다. 외부 GitHub 요청이나 인증 토큰은 필요 없다.
- 초기 렌더부터 width/height를 지정하고 3:1 비율을 유지한다. 자르기·필터·호버 밝기 변조 없이 표시한다.
- PC/모바일 로고 폭은 공통 기준의 166/136/115px이다. 헤더 보조 문구는 `나의 건강, 한곳에`다.
- 일시적인 로고 실패가 이후 모든 갱신에 텍스트 대체 상태를 고정하던 문제를 수정했다. 두 로컬 경로가 실패할 때만 텍스트를 표시하며, 다음 렌더에서 복구한다.

## 요약 카드

`health-link-studio-branding.js`를 공통 뷰 스타일 뒤에 명시적으로 결합한다.
공통 디자인 토큰은 유지하고 HealthLink의 제품별 차이만 이 파일에 모았다.

| 영역 | 라이트 모드 |
|---|---|
| 요약 배경 | #ffffff, 남색 그라데이션 제거 |
| 제목·주요 숫자 | #191f28 |
| 설명·라벨·수신 시각 라벨 | #667182 |
| 수신 시각 값 | #191f28 |
| 보조 버튼 | #edf3ff 배경 + #2563eb 글자 |
| 미수신 안내 | #fff4dc 배경 + #805500 글자 |
| 구분 | 옅은 테두리·행 구분선, 숫자 사이 구분선 |

다크 모드는 흰 글자를 흰 카드에 남기는 방식이 아니라 기존 다크 카드 표면
#1b222c와 대응 텍스트 토큰으로 함께 전환한다. 남색 그라데이션은 어느 테마에서도 사용하지 않는다.
고대비 모드에서는 Canvas/CanvasText/Highlight를 사용한다.

## 검증

로컬 Chromium + Playwright, 실제 원본 로고 / 합성 건강 데이터로 실행했다.

| 명령 | 결과 |
|---|---|
| `python tests/frontend/studio_browser_checks.py` | 기존 26개 통과 |
| `python tests/frontend/branding_browser_checks.py` | 추가 8개 통과 |
| `node --test tests/test_studio_branding.cjs` | 추가 4개 통과 |
| 신규/수정 JS `node --check`, Python `py_compile` | 통과 |

기존 Node CI 진입점 `tests/test_panel.cjs`가 새 로고 테스트를 함께 실행한다.
브라우저 테스트의 HA 정적 URL은 실제 repo 원본 PNG로 매핑한다.
17개 폭(320~1440px)의 가로 넘침·헤더 버튼 겹침·로고 비율을 확인했다.
원본/예비 파일 해시 동일성, 이미지 로딩, 캐시된 재렌더, 양쪽 경로 실패/복구,
입력 중 테마 전환, forced-colors/reduced-motion도 확인했다.

밝은 요약 카드의 단색 대비 계산: 본문/흰색 16.56:1, 보조 설명/흰색 4.94:1,
보조 버튼 글자/배경 4.64:1, 미수신 안내 5.98:1.
두 테마 × 수신/미수신 상태의 요약 텍스트·버튼은 브라우저 계산 색상으로
각각 4.5:1 이상을 확인했다. 화면 전체의 접근성 인증을 뜻하지 않는다.
기준: https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html

독립 HTML 미리보기에는 동일 PNG 바이트를 내장했다. 인터넷이 없어도 로고가 표시되며,
미리보기 구동 검사에서 외부 HTTP 요청 0건, 페이지 JavaScript 오류 0건이었다.
작업용 브라우저는 로컬 file:// 탐색이 차단되어 HTML 내용을 직접 로드하여 검증했다.

## 변경하지 않은 것 / 미검증

건강 분석·DB·설정·권한·민감 항목 정책·기존 엔티티 및 API 요청은 바꾸지 않았다.
Python 변경은 원본 로고의 공개 정적 파일 경로와 UI 캐시 식별자(20260913.2)다.
건강 데이터가 공개되는 경로는 추가하지 않았다.

실제 사용자 HA 설치·재시작, Safari/VoiceOver/NVDA, 실기기 엔티티 반영은 미검증이다.
통합 버전은 0.3.5를 유지하며 이번 작업은 기존 PR 업데이트다. main 병합·새 릴리스는 수행하지 않는다.
