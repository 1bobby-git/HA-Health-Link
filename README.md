<p align="center">
  <img src="assets/healthlink-logo-wide.png" alt="HealthLink 로고" width="700">
</p>

<p align="center">
  <a href="https://github.com/1bobby-git/HA-Health-Link/stargazers"><img src="https://img.shields.io/github/stars/1bobby-git/HA-Health-Link?style=flat-square&logo=github&label=Stars" alt="GitHub Stars"></a>
  <a href="https://github.com/1bobby-git/HA-Health-Link/releases"><img src="https://img.shields.io/github/v/release/1bobby-git/HA-Health-Link?style=flat-square&label=Release" alt="Latest Release"></a>
  <a href="https://github.com/1bobby-git/HA-Health-Link/blob/main/LICENSE"><img src="https://img.shields.io/github/license/1bobby-git/HA-Health-Link?style=flat-square&label=License" alt="License"></a>
  <a href="https://github.com/1bobby-git/HA-Health-Link/commits/main"><img src="https://img.shields.io/github/last-commit/1bobby-git/HA-Health-Link?style=flat-square&label=Updated" alt="Last Commit"></a>
</p>

# HealthLink

**Apple 건강(HealthKit) 데이터와 Home Assistant의 집·환경 데이터를 연결하는 로컬 우선 건강 컨텍스트 통합입니다.**

HealthLink는 건강 데이터를 Home Assistant에 단순 복사하는 데서 끝나지 않습니다. 개인 기준선, 건강+집 타임라인, Health Composer, 관측형 인사이트를 이용해 **내 몸의 변화와 집 환경의 관계를 이해하고 자동화에 활용**할 수 있게 합니다.

> HealthLink는 웰니스/컨텍스트 분석용 통합이며 의료기기, 진단 시스템, 치료 판단 도구가 아닙니다.

> **설정과 Studio는 분리됩니다.** 통합 카드의 톱니바퀴는 Home Assistant 네이티브 설정(연결 iPhone, 기준선, 목표, 개인정보, 보존기간)을 엽니다. `HealthLink Studio`는 보고서·타임라인·인사이트·Composer를 사용하는 기능 화면이며 통합 설정 페이지가 아닙니다.
> Mobile App의 Apple 건강 센서와 값이 겹쳐도 HealthLink의 기본 요약 센서는 숨기지 않습니다. 동일 원천 데이터를 HealthLink 프로필·파생 컨텍스트·자동화에서 일관되게 참조하기 위한 의도적인 중복입니다.

---

## 왜 HealthLink가 필요한가요?

- **별도 HealthLink iPhone 앱 불필요**: 기본 사용은 공식 Home Assistant iOS Companion 앱만 사용합니다.
- **YAML 불필요**: Apple 건강 센서를 자동 탐색합니다.
- **다중 iPhone 지원**: 같은 사람의 여러 iPhone을 한 건강 프로필에 묶거나, 가족별로 HealthLink 프로필을 따로 만들 수 있습니다.
- **개인 기준선**: HRV, 안정 심박, 수면, 활동을 고정 임계값이 아니라 사용자의 최근 7/28/90/365일 패턴과 비교합니다.
- **Health Composer**: HealthKit 데이터와 임의의 Home Assistant 엔티티를 조합해 새 센서를 만들 수 있습니다.
- **건강 + 집 타임라인**: 수면·심박·활동과 온도·습도·CO₂·조명 같은 집 상태를 같은 시간축에서 확인합니다.
- **관측형 인사이트**: 예를 들어 깊은 수면과 침실 CO₂, HRV와 실내 온도의 관계를 분석합니다. 인과관계로 단정하지 않습니다.
- **Recorder 보호**: 원본 건강 데이터는 HealthLink 전용 로컬 SQLite/WAL 저장소에 보관하고 필요한 값만 HA 엔티티로 노출합니다.
- **로컬 우선 개인정보 보호**: 외부 분석 서버나 클라우드 중계가 필요하지 않습니다.
- **민감정보 기본 비공개**: 민감 건강 항목은 사용자가 직접 허용하기 전까지 일반 HA 센서로 노출하지 않습니다.

---

## 데이터는 어디서 가져오나요?

HealthLink의 현재 기본 데이터 소스는 **공식 Home Assistant iOS 앱의 `Apple 건강 센서 (Labs)` 기능**입니다. 이 기능이 iPhone의 HealthKit을 읽어 Home Assistant `mobile_app` 건강 센서로 전송하고, HealthLink가 그 센서를 자동 수집합니다.

```text
Apple Watch / iPhone / Apple 건강 앱
                ↓
             HealthKit
                ↓
공식 Home Assistant iOS 앱
Apple 건강 센서 (Labs)
                ↓
Home Assistant mobile_app health_* 센서
                ↓
             HealthLink
                ↓
개인 기준선 / Composer / 타임라인 / 인사이트 / 자동화
```

HealthLink HACS 컴포넌트 자체가 iPhone HealthKit DB를 직접 여는 것은 아닙니다. Home Assistant Core는 일반적으로 Linux/HAOS에서 실행되고 Apple HealthKit API에 직접 접근할 수 없기 때문에 **HealthKit 읽기 역할은 공식 Home Assistant iOS 앱이 담당**합니다.

따라서 **별도 HealthLink 앱은 필요 없지만, 실시간 Apple Health/HealthKit 데이터를 받으려면 공식 Home Assistant iOS Companion 앱은 필요합니다.** HealthLink는 Companion 앱이 노출하는 `health_*` 센서를 자동으로 찾으며, 공식 앱에 새 건강 센서가 추가되어도 동적으로 탐색하도록 설계되어 있습니다.

### Home Assistant 로고 표시 방식

Home Assistant 2026.3 이상에서는 커스텀 통합이 `custom_components/health_link/brand/` 폴더에 포함한 `icon.png`와 `logo.png`를 **로컬 Brands Proxy API**(`/api/brands/integration/health_link/...`)를 통해 표시합니다. HealthLink는 승인된 정사각형 아이콘과 가로형 로고를 이 방식으로 제공합니다.

---

# 설치 방법

## 1. HACS로 설치 — 권장

아래 버튼을 누르면 Home Assistant에서 HealthLink HACS 저장소를 바로 열 수 있습니다.

[![Open your Home Assistant instance and show the HACS repository.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=1bobby-git&repository=HA-Health-Link&category=integration)

버튼을 사용할 수 없는 경우 수동으로 HACS에 추가합니다.

1. **HACS → Integrations** 이동
2. 우측 상단 메뉴 → **Custom repositories**
3. Repository에 `https://github.com/1bobby-git/HA-Health-Link` 입력
4. Category는 **Integration** 선택
5. **HealthLink** 설치
6. Home Assistant 재시작

## 2. 통합 추가

재시작 후 아래 버튼으로 HealthLink 설정을 바로 시작할 수 있습니다.

[![Open your Home Assistant instance and start setting up the integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=health_link)

또는 다음 경로를 이용합니다.

**설정 → 기기 및 서비스 → 통합 추가 → HealthLink**

## 3. iPhone에서 Apple 건강 센서 활성화

1. iPhone에서 **Home Assistant 앱** 실행
2. **설정 → 센서 → Apple 건강 센서 (Labs)** 이동
3. 사용할 건강 센서 활성화
4. `모든 센서를 활성화하기`가 보이면 한 번에 활성화 가능
5. Home Assistant의 **HealthLink** 화면 확인

한 대의 iPhone만 감지되면 자동으로 연결합니다. 여러 대의 iPhone이 있으면 설정 화면에서 기기를 선택합니다.

- **한 사람이 iPhone 여러 대 사용**: 같은 HealthLink 프로필에서 여러 iPhone을 함께 선택할 수 있습니다.
- **가족 여러 명 사용**: 사람마다 HealthLink 프로필을 하나씩 추가하고 각 사람의 iPhone을 해당 프로필에 선택하는 것을 권장합니다.
- 이미 다른 HealthLink 프로필에 연결된 iPhone은 중복 선택할 수 없습니다.

새로 활성화한 건강 센서는 Home Assistant 재시작 없이 자동 탐색합니다.

## 4. 수동 설치

HACS를 사용하지 않는 경우 저장소의 `custom_components/health_link` 폴더를 아래 위치로 복사합니다.

```text
/config/custom_components/health_link
```

복사 후 Home Assistant를 재시작하고 **설정 → 기기 및 서비스 → 통합 추가 → HealthLink**를 선택합니다.

---

## 설정 화면과 HealthLink Studio의 차이

HealthLink는 별도 앱을 설치하지 않습니다. Home Assistant 안에 두 종류의 화면이 있습니다.

- **통합 설정(톱니바퀴)**: Home Assistant 표준 Options Flow. 연결할 iPhone, 기준선 기간, 데이터 보존기간, 개인정보 옵션을 변경합니다.
- **HealthLink Studio(사이드바)**: 건강 데이터 탐색, 타임라인, Health Composer, 인사이트를 제공하는 Home Assistant 내부 패널입니다.

즉 사이드바의 HealthLink Studio는 외부 앱이나 iOS 앱이 아니라 **HACS 컴포넌트가 Home Assistant 내부에 제공하는 화면**입니다.

---

## 주요 기능

### 개인 기준선

사용자의 과거 데이터를 기준으로 현재 상태를 비교합니다.

```text
HRV      평소 대비 -18%
안정심박 평소 대비 +9%
수면     평소 대비 -14%

→ 회복 컨텍스트: 평소보다 낮음
```

고정된 의학 임계값이 아니라 **개인의 평소 패턴 대비 변화**를 보여줍니다.

### Health Composer

HealthKit 데이터와 Home Assistant 엔티티를 조합해 사용자가 새로운 센서를 만들 수 있습니다.

```text
HRV + 깊은 수면 + 침실 CO₂ + 침실 온도
                    ↓
          사용자 정의 회복/환경 센서
```

수식은 제한된 안전 파서를 사용하며 `eval`/`exec`를 사용하지 않습니다.

### 건강 + 집 타임라인

예를 들어 다음 흐름을 같은 시간축에서 확인할 수 있습니다.

```text
23:18 수면 시작
01:42 침실 CO₂ 1,180 ppm
01:55 각성 증가
02:03 환기 시작
02:21 CO₂ 760 ppm
```

### 인사이트

HealthLink는 장기간 데이터를 이용해 관측 가능한 관계를 계산합니다.

- 침실 CO₂와 깊은 수면
- 실내 온도와 HRV
- 운동량과 다음 날 회복 컨텍스트
- 습도와 수면 결과

분석 결과는 **관측된 연관성**으로만 표시하며 의학적 인과관계로 표현하지 않습니다.

---

## HealthLink Studio

Home Assistant 사이드바에 **HealthLink** 화면이 추가됩니다.

| 화면 | 기능 |
|---|---|
| 오늘 | 걸음, 수면, 회복 컨텍스트, 신뢰도, 동기화 상태 |
| 건강 데이터 | 실제 수집된 건강 항목 탐색 및 HA 센서 노출 설정 |
| 타임라인 | 건강 데이터와 HA 환경 센서의 시간축 비교 |
| 센서 만들기 | Health Composer로 사용자 센서 생성 |
| 인사이트 | 상관관계 및 관측상 유리한 환경 범위 분석 |
| 연결 상태 | Companion 연결 및 데이터 상태 확인 |

---

## 기본 생성 센서

초기에는 불필요한 엔티티 폭증을 막기 위해 대표 센서만 생성합니다.

- `sensor.*_last_sync`
- `sensor.*_sync_latency`
- `sensor.*_data_confidence`
- `sensor.*_steps_today`
- `sensor.*_active_energy_today`
- `sensor.*_exercise_time_today`
- `sensor.*_last_sleep_duration`
- `sensor.*_last_sleep_deep`
- `sensor.*_last_sleep_rem`
- `sensor.*_last_sleep_efficiency`
- `sensor.*_recovery_context`
- `sensor.*_recovery_confidence`
- `sensor.*_hrv_vs_baseline`
- `sensor.*_resting_hr_vs_baseline`
- `sensor.*_sleep_vs_baseline`
- `sensor.*_activity_vs_baseline`
- `binary_sensor.*_data_stale`
- `binary_sensor.*_recovery_below_baseline`

추가 건강 항목은 **HealthLink → 건강 데이터**에서 필요한 항목만 선택해 HA 센서로 노출할 수 있습니다.

---

## 개인정보 보호

HealthLink는 건강 데이터 특성상 기본 설정을 보수적으로 구성합니다.

- 외부 클라우드 분석: **사용하지 않음**
- 민감 건강 항목 엔티티 노출: **기본 OFF**
- 원본 건강 데이터: HealthLink 전용 로컬 저장소
- Diagnostics에 원본 건강 수치 포함: **안 함**
- Bridge Webhook: 기본 Companion 모드에서는 **등록하지 않음**
- 자동 환경 제어: 아직 일반 설정에 노출하지 않음
- HealthKit 쓰기: 아직 일반 설정에 노출하지 않음

혈압, 혈당, SpO₂ 등 건강 수치는 표시·추세 확인에 사용할 수 있지만 약물 투여나 응급 판단 같은 안전 필수 자동화를 목적으로 설계하지 않습니다.

---

## 지원 범위와 한계

HealthLink가 기본적으로 사용할 수 있는 범위는 **설치된 공식 Home Assistant iOS Companion 앱의 Apple 건강 센서(Labs)가 HealthKit에서 노출하는 데이터**입니다.

공식 iOS 앱의 현재 HealthKit 카탈로그 자체도 HealthKit 전체가 아니라 단계적으로 확대되는 범위입니다. HealthLink 서버측 저장 구조는 향후 Workout, Route, ECG, Heartbeat Series 등 구조화 HealthKit 객체를 수용할 수 있게 설계되어 있지만, Linux의 HACS 통합만으로 iPhone HealthKit 전체를 직접 읽을 수는 없습니다.

전체 HealthKit 범위 확대는 별도 HealthLink iOS 앱을 사용자에게 요구하는 대신 **공식 Home Assistant iOS 앱 지원 확대를 우선**합니다. 이전 개발용 `ios/HealthLinkBridge` 스캐폴드는 일반 사용자에게 필요하지 않고 제품 방향과 맞지 않아 저장소에서 제거했습니다.

---

## 문제 해결

### HealthLink에 데이터가 보이지 않을 때

1. iPhone Home Assistant 앱에서 Apple 건강 센서(Labs)가 활성화되어 있는지 확인
2. Apple 건강 앱에서 Home Assistant의 HealthKit 읽기 권한 확인
3. Home Assistant의 `mobile_app` 통합이 정상인지 확인
4. HealthLink 화면에서 **다시 확인** 실행

### 여러 iPhone이 있을 때

**설정 → 기기 및 서비스 → HealthLink → 설정**에서 이 프로필에 연결할 iPhone을 선택합니다. 같은 사람의 여러 iPhone은 함께 선택할 수 있고, 다른 사람은 별도의 HealthLink 프로필로 분리하는 것을 권장합니다.

### 새 센서를 켰는데 바로 보이지 않을 때

대부분 즉시 탐색되며, 복구용 주기 재검색도 수행됩니다. Home Assistant 앱에서 센서 값이 실제로 생성되었는지도 확인하세요.

---

## 업데이트

HACS에서 새 버전이 표시되면 **Update** 후 Home Assistant를 재시작합니다.

현재 버전: **v0.2.0**

---

## 프로젝트 문서

- [최종 PRD](docs/HealthLink_PRD_v1.0.md)
- [데이터 소스 및 전송 정책](docs/DATA_SOURCES.md)
- [구현 상태](docs/STATUS.md)
- [변경 이력](CHANGELOG.md)

---

## 라이선스

MIT License


## v0.1.5: 다른 사용자·iPhone 목록과 로고 수정

HealthLink의 건강 프로필과 HA 로그인 계정은 별개입니다. 가족마다 **설정 → 기기 및 서비스 → HealthLink → 허브 추가**로 건강 프로필을 만들고 해당 사람의 iPhone을 선택하세요. HA 계정만 만들었고 iPhone 앱을 아직 같은 서버에 등록하지 않았다면 기기 목록에는 나타나지 않습니다.

등록된 iPhone은 Apple 건강 센서(Labs)를 켜기 전에도 선택할 수 있습니다. 건강 값 수집에는 각 iPhone의 센서 활성화와 HealthKit 읽기 권한이 필요합니다. 이미 다른 프로필이 사용 중인 기기는 중복 선택되지 않습니다. 연결을 해제한 기기를 기존 설정에서 되살려 가져오지 않습니다.

HealthLink 화면에 모든 등록된 프로필을 표시하고, 연결 대기·설정 실패 프로필도 숨기지 않습니다. 화면에 다시 들어오거나 브라우저로 돌아왔을 때 목록을 갱신하며, 화면이 보이는 동안 15초 간격으로도 갱신합니다. 센서 만들기 입력 중에는 입력 내용을 지우지 않습니다. 관리자 전용 건강 데이터 접근 정책은 변경하지 않았습니다.

배포 과정에서 손상된 PNG를 승인된 원본 이미지로 교체했습니다. 도형·서체·색상·간격은 변경하지 않았습니다. 통합 카드의 로고는 **로컬 Brands Proxy API**, HealthLink 화면도 `brands/access_token` 인증을 포함한 같은 API를 우선 사용합니다. 화면의 로컬 이미지 대체 경로도 포함됩니다. PNG 청크 CRC와 압축 데이터 검사로 잘린 이미지가 다시 배포되지 않게 합니다.

업데이트는 **HACS → HealthLink → v0.1.5 설치 → Home Assistant 재시작** 순서입니다. 기존 건강 프로필과 데이터베이스는 삭제하지 않습니다.


## v0.2.0 — Apple 건강을 "보는 센서"에서 "활용하는 컨텍스트"로

HealthLink는 공식 Home Assistant iOS의 **Apple 건강 센서(Labs)**가 HealthKit에서 읽어 HA에 전달한 값을 사용합니다. HealthLink가 iPhone HealthKit을 별도 경로로 직접 읽는 것은 아닙니다. 대신 다음 차이를 만듭니다.

- 기존 Mobile App 원본 센서는 그대로 두고, 새 설치에서는 중복 원본 HealthLink 엔티티를 기본 비활성화합니다.
- 사용자 개인 기준선, 같은 시간대 활동 비교, 목표 진행률, 오늘의 생활 포커스 같은 **HealthLink 전용 파생 센서**를 제공합니다.
- `get_daily_report`, `get_trends`, `set_goal`, `evaluate_routine`, `record_routine`, `get_routine_history`, `analyze_environment` 액션을 제공합니다.
- `sync_request`는 iPhone을 강제로 깨우는 기능으로 오해하지 않도록, 이미 HA에 전달된 최신 Apple 건강 엔티티를 즉시 다시 읽습니다.
- `backfill_request`는 공식 Apple 건강 센서가 HA Recorder에 남긴 과거 상태를 HealthLink의 개인 로컬 저장소로 가져와 분석 시작 시점을 앞당깁니다. Recorder에 기록이 없으면 가져올 수 없습니다.
- 목표값은 사용자가 직접 설정하며 HealthLink가 의료 권장량을 임의로 정하지 않습니다.
- HealthLink의 자동화 기능은 **판단/컨텍스트를 반환**하고, 실제 조명·HVAC·환기 등은 사용자가 만든 HA 자동화가 실행합니다. 자동 의료 판단이나 처방은 하지 않습니다.

예를 들어 저녁 자동화에서 `health_link.evaluate_routine`의 `evening_recovery` 결과가 `suggested: true`일 때만 사용자가 선택한 휴식 장면을 실행하고, 이후 `health_link.record_routine`으로 실행 여부를 기록할 수 있습니다.


### 시간 기반 건강↔집 분석의 정확성

현재 공식 Apple 건강 센서(Labs)는 HA 센서 값은 제공하지만 HealthLink가 필요한 **원본 HealthKit 샘플 시각/수면 episode 구간을 모든 항목에 전달하지는 않습니다.** 따라서 v0.2.0은 HA에 보고된 시각을 실제 측정 시각으로 가장하지 않습니다. 원본 시각이 없는 Labs 항목은 시간 정렬형 건강↔집 상관분석과 자동 환경 최적값 계산을 차단합니다. 대신 당일 누적 목표, 같은 시각대 활동 비교, 개인 보고값 기준선, HA 환경 구간 요약처럼 현재 입력만으로 의미가 분명한 기능을 제공합니다.
