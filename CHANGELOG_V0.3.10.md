# HealthLink v0.3.10 — Home Assistant 검사(hassfest) 통과

## 적용 내용

- 매일 실행되는 Validate(hassfest) 검사가 다시 통과하도록 고쳤습니다.
  - `defusedxml`은 Home Assistant가 직접 쓰는 패키지라서, 정확한 버전 고정(`defusedxml==0.7.1`) 대신 최소 버전(`defusedxml>=0.7.1`)으로 적었습니다. Home Assistant가 이 패키지를 올려도 설치가 충돌하지 않습니다.
  - 통합은 설정 항목(config entry)으로만 설정되므로 `CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)`을 선언했습니다. `configuration.yaml`에 설정을 적는 방식은 원래 지원하지 않았고, 이번에도 바뀌지 않습니다.

## 검증

- 두 규칙을 고정하는 테스트를 추가했습니다.
- GitHub Actions의 Tests(Home Assistant 2026.8.0, 2026.9.1)와 Validate(hassfest, HACS) 결과로 확인합니다.
- 엔티티 ID, 고유 ID, 설정 항목 데이터, 서비스 이름, 센서 값·단위는 그대로입니다.

## 업데이트

HACS에서 v0.3.10을 받은 뒤 Home Assistant를 다시 시작하세요. 통합을 삭제하거나 프로필을 다시 등록할 필요는 없습니다.
