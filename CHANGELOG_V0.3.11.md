# HealthLink v0.3.11 — Home Assistant 2026.11 기기 목록 읽기 부담 줄이기

## 적용 내용

- iPhone·iPad(Companion 앱) 기기를 찾을 때 Home Assistant 2026.11부터 사용 중단 예정(deprecated)이 된 `DeviceEntry.config_entries` 값을 더 이상 읽지 않습니다.
  - 2026.11부터는 이 값을 읽을 때마다 Home Assistant가 호출 경로와 불러온 모듈 전체를 훑어 경고를 남깁니다. 기기가 많은 집에서는 이 작업이 Home Assistant를 눈에 띄게 느리게 만들 수 있습니다.
  - 이제는 모든 기기를 하나씩 훑는 대신, Companion 앱(`mobile_app`) 등록마다 그 등록에 속한 기기만 기기 레지스트리 색인(`async_entries_for_config_entry`)으로 바로 찾습니다.
- 보이는 기기 목록, 기기 이름, iPhone·iPad 판별 규칙은 그대로입니다. 여러 통합이 함께 쓰는 기기도 예전처럼 한 번만 표시됩니다.

## 검증

- `config_entries`, `config_entries_subentries`, `primary_config_entry`를 읽으면 바로 실패하는 가짜 기기로 회귀 테스트를 추가했습니다(단일 소유 기기, 여러 설정 항목이 함께 쓰는 기기, Companion 등록이 없는 경우).
- GitHub Actions의 Tests(Home Assistant 2026.8.0, 2026.9.1)와 Validate(hassfest, HACS) 결과로 확인합니다.
- 엔티티 ID, 고유 ID, 설정 항목 데이터, 서비스 이름, 센서 값·단위는 그대로입니다.

## 업데이트

HACS에서 v0.3.11을 받은 뒤 Home Assistant를 다시 시작하세요. 통합을 삭제하거나 프로필을 다시 등록할 필요는 없습니다.
