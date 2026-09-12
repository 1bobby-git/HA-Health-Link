# 건강 원본·ECG 사용 안내 — v0.3.0

## 무엇이 달라지는가

기존 Mobile App/Apple 건강 센서(Labs) 수집, HealthLink 요약 센서, 목표·보고서·자동화는 그대로입니다. 추가 기능은 **실제 발견한 건강 항목의 네이티브 노출 선택**과 **로컬 건강 원본 가져오기**, **ECG 기록·파형 조회**입니다. 별도 HealthLink iOS 앱과 RDC는 필요하지 않습니다.

ECG는 현재 공식 HA iOS Labs 센서가 자동으로 보내지 않습니다. 센서 이름을 추가하는 것만으로 ECG가 수집되지는 않습니다. ECG 원본을 직접 가져와야 하며, HealthLink는 Apple Health에 쓰거나 Watch의 ECG 측정을 시작하지 않습니다.

## 1. 이미 수집한 건강 항목을 더 보기

`설정 → 기기 및 서비스 → HealthLink → 해당 프로필 설정 → 건강 항목 노출`

실제 들어온 숫자·범주형 항목을 선택합니다. 심박·HRV·체중·물 섭취 등은 해당 iPhone의 Labs 활성화와 HealthKit 읽기 권한 및 기록이 있어야 나타납니다. 기존 걸음·활동·수면 요약 센서는 이 메뉴와 무관하게 유지됩니다. 사용자가 직접 끈 엔티티를 강제로 켜지 않습니다.

민감 항목은 별도 허용이 필요합니다. 일반 HA 엔티티로 노출한 건강 값과 이미지에는 HA의 통상적인 접근 정책이 적용됩니다. 프로필이 나뉘어 있다는 것만으로 로그인 사용자별 비공개 대시보드가 보장되지는 않습니다. 공유 서버에서는 노출 전에 접근 권한을 확인하세요. 관리자용 조회 서비스와 파일 가져오기는 관리자 계정 또는 HA 내부 자동화만 사용할 수 있습니다.

## 2. 건강 내보내기 파일 가져오기

Apple 건강에서 본인의 데이터를 내보낸 뒤 다음 메뉴를 사용합니다.

`해당 프로필 설정 → 건강 원본·ECG 가져오기 → 파일 선택 → 본인 자료 확인 → 제출`

지원 입력:

| 형식 | 처리하는 자료 | 구분 |
|---|---|---|
| Apple `export.zip` | 내부 `export.xml`의 수치·범주·운동 기록, `electrocardiograms` 폴더의 지원 CSV | ZIP을 디스크에 풀지 않고 읽음 |
| Apple `export.xml` | `Record` 수치·범주 및 `Workout` 기록 | `Me`의 생년월일·이름 등은 가져오지 않음 |
| ECG CSV | Recorded Date / Sample Rate / Lead / Unit 메타데이터 뒤의 단일 전압열 | 영어 메타데이터, 소수점 마침표·쉼표 지원 |
| ECG JSON | 아래 문서화된 ECG 형식 또는 `data.ecg` 형식 | 날짜·단위·샘플 수 검증 |
| HealthLink JSON | `records` 배열에 명시한 HealthKit 수치·범주 기록 | 단축어·다른 송신기가 이미 읽은 자료의 입력용 |

파일 제한: 업로드 100 MB, ZIP 비압축 크기 합계 512 MB, 최대 10,000개 ZIP 항목, 최대 1,000,000개 처리 항목. JSON은 32 MB, ECG 한 기록은 120,000개 전압값, 한 가져오기는 총 2,000,000개 전압값까지입니다. 제한을 넘으면 작은 파일로 나누어야 합니다. 현재 범위 밖의 FHIR·PDF·경로 파일·비공개 Apple 내부 데이터는 가져왔다고 표시하지 않습니다. 지원하지 않는 `Record` 유형은 제외 개수를 표시합니다.

전체 파싱과 검증은 임시 로컬 SQLite에서 진행하고, 성공한 자료만 실제 프로필 저장소에 하나의 트랜잭션으로 반영합니다. 형식 오류가 있으면 일부만 들어온 상태를 남기지 않습니다. 업로드 원본과 임시 자료는 처리 후 제거됩니다. 동일 자료를 다시 가져와도 안정적인 식별자로 중복 등록을 막습니다.

원본 기록은 `apple_export.*`로 구분하고 출처·단위별 시계열을 분리합니다. **Apple Watch의 원본 100걸음에 iPhone의 하루 합계 8,000걸음을 더하지 않습니다.** 원본 값·단위는 파일에 기록된 의미로 보존되며, 현재 버전에서는 Labs의 하루 합계·개인 목표 수치를 원본 가져오기가 대체하지 않습니다. 수면 단계 기록도 실제 구간으로 보관하지만 Apple의 수면 합산·중복 제거 알고리즘을 재현했다고 주장하지 않습니다.

## 3. ECG 보기

ECG를 가져오기 전에 `기기·목표·개인정보 설정`에서 민감 건강 항목을 허용합니다. 파일 가져오기에서도 `ECG 등 민감 자료 포함`을 선택하고, 완료 후 `건강 항목 노출`에서 `심전도 원본 기록`을 선택합니다.

프로필 기기에 다음 엔티티가 추가됩니다.

- ECG 기록 수, 마지막 측정 시각, 원본 분류 결과, 평균 심박, 파형 측정 수, 기록 길이: 6개 센서.
- ECG 파형 미리보기: HA 기본 이미지 엔티티. 기본 대시보드의 이미지/그림 요소에서 선택할 수 있습니다.

파형은 전체 값을 센서 속성에 넣지 않고 로컬 저장소에서 필요할 때 조회합니다. 이미지도 HA 이미지 엔티티의 인증 경로로 제공하며 공개 `www` 폴더에 저장하지 않습니다. 미리보기는 자동 크기 조절된 참고 이미지이며 표준 의료용 ECG 출력물이나 진단용 화면이 아닙니다.

분류·평균 심박·증상 정보가 파일에 없으면 빈 값으로 둡니다. 정상으로 판정하거나 전압에서 심박·질병을 임의로 추론하지 않습니다. 저장된 기록을 가져오는 기능이지 상시 심전도 감시가 아닙니다.

### 지원 ECG JSON 예시 — 합성 자료

```json
{
  "ecg": [{
    "start": "2026-09-10T12:00:00+09:00",
    "end": "2026-09-10T12:00:01+09:00",
    "source": "Synthetic example",
    "samplingFrequency": 4,
    "numberOfVoltageMeasurements": 4,
    "voltageMeasurements": [
      {"voltage": 0, "units": "uV"},
      {"voltage": 120, "units": "uV"},
      {"voltage": -80, "units": "uV"},
      {"voltage": 30, "units": "uV"}
    ]
  }]
}
```

전압 단위는 V/mV/uV/µV/μV를 명시해야 합니다. 내부와 조회 결과에서는 mV로 정규화합니다. 점별 `date` 또는 `time_since_start`를 제공할 수 있으며, 없으면 파일의 명시적인 `samplingFrequency`로 시간 간격을 계산합니다. 날짜에 시간대가 없거나 단위를 모르면 추측하지 않고 거부합니다.

`classification`, `averageHeartRate`, `symptomsStatus`, `lead`는 입력에 있을 때 보존합니다. Apple ECG CSV의 이름·생년월일은 저장하지 않습니다. 다른 언어·다른 CSV 레이아웃은 검증 없이 자동 해석하지 않습니다.

## 4. 네이티브 자동화 동작

`설정 → 자동화 및 장면 → 자동화 → 동작 추가` 또는 개발자 도구의 동작 화면에서 사용합니다.

| 동작 | 역할 |
|---|---|
| `health_link.list_available_metrics` | 실제 수집한 항목·노출 상태 조회 |
| `health_link.import_health_file` | HA 파일 선택기로 업로드한 파일 가져오기 |
| `health_link.import_health_samples` | 문서화된 원본 JSON 전달(최대 2 MB) |
| `health_link.get_ecg_records` | ECG 목록과 다음 페이지 위치 반환 |
| `health_link.get_ecg` | 특정 기록의 메타데이터 조회 |
| `health_link.get_ecg_waveform` | 파형 페이지 조회, 1회 최대 4,096개 점 |

모두 응답 데이터를 반환합니다. 여러 건강 프로필이 있으면 `config_entry_id`를 반드시 지정해야 합니다. ECG 조회는 해당 프로필의 민감 자료 허용이 필요합니다.

단축어가 지원하는 건강 샘플을 읽어 아래와 같은 `data.records`를 `import_health_samples`에 보내도록 연동할 수 있습니다. HealthLink가 기본 단축어에 없는 ECG 읽기 기능을 새로 만드는 것은 아닙니다.

```yaml
action: health_link.import_health_samples
data:
  config_entry_id: YOUR_HEALTHLINK_ENTRY_ID
  confirm_profile: true
  data:
    records:
      - type: HKQuantityTypeIdentifierStepCount
        sourceName: My Shortcut
        start: "2026-09-10T12:00:00+09:00"
        end: "2026-09-10T12:01:00+09:00"
        value: 123
        unit: count
response_variable: import_result
```

원본 내보내기 기반 기능은 `health_link_records_imported`, 새로운 ECG가 실제로 추가됐을 때는 `health_link_ecg_imported` 이벤트를 발생시킵니다. 이벤트에는 프로필 ID와 개수 등 최소 정보만 포함하며 파형·분류·이름을 포함하지 않습니다. `historical_import: true`인 과거 기록 도착을 실시간 응급 상황으로 취급하지 마세요.

`blueprints/automation/health_link/ecg_imported.yaml`은 프로필을 고르고 기록 도착 뒤 실행할 동작을 직접 선택하는 블루프린트입니다. 조명·알림 등 어떠한 동작도 사용자 설정 없이 자동 실행하지 않습니다.

## 데이터 소스와 검증 범위

Apple 공개 ECG API: https://developer.apple.com/documentation/healthkit/hkelectrocardiogram

HA File upload: https://www.home-assistant.io/integrations/file_upload/

ECG JSON 제공자 형식: https://help.healthyapps.dev/en/health-auto-export/export-format/ecg/

CSV 레이아웃 확인 자료: https://huggingface.co/datasets/fabriciojm/apple-ecg-examples/blob/main/ecg_2025-01-15.csv

회귀 테스트에는 개인의 실제 파일이 아닌 합성 자료만 사용합니다. 실제 사용자 iPhone의 모든 언어·OS별 내보내기 형식에서 검증된 것은 아닙니다. 미지원 형식은 오류로 알려주며 기록을 임의로 조정하지 않습니다.
