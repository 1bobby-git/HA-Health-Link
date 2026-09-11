# HealthLink — Final PRD v1.0

## 1. Product definition

**Product:** HealthLink  
**Repository:** `HA-Health-Link`  
**Home Assistant domain:** `health_link`  
**Distribution:** HACS custom integration, with HACS default-store readiness as a release goal  
**Positioning:** Local-first Apple Health/HealthKit context engine for Home Assistant.

HealthLink exists because simply copying Apple Health numbers into Home Assistant is not enough. Apple Health knows the user's body; Home Assistant knows the user's home, environment and routines. HealthLink joins both contexts and turns them into useful personal-baseline sensors, timelines, observational insights and safe automations.

HealthLink is a wellness/context product. It must never present itself as a medical device, diagnosis engine or substitute for professional care.

## 2. User-facing promise

A normal user must be able to install and use HealthLink without YAML, database knowledge, webhook construction, HealthKit class names or manual entity-ID entry.

The default onboarding is:

1. Install HealthLink from HACS.
2. Add HealthLink under Home Assistant → Settings → Devices & services.
3. On iPhone, enable the desired Apple Health sensors in the **official Home Assistant iOS app**.
4. HealthLink automatically discovers those `mobile_app` health sensors and starts importing them.
5. Open **HealthLink** in the Home Assistant sidebar.

If there is one eligible iPhone, HealthLink binds it automatically. If there are multiple iPhones, HealthLink pauses automatic import and asks for a one-time device choice so household members' health data can never be silently mixed.

## 3. Data-source architecture

### 3.1 Standard mode — no extra HealthLink iOS app

```text
Apple Health / HealthKit
        ↓
official Home Assistant iOS Companion app
        ↓
Home Assistant mobile_app health_* sensors
        ↓
HealthLink HACS integration
        ↓
private local store
        ↓
baselines / composer / timeline / insights / automations
```

This is the recommended path and the one ordinary users should see first.

### 3.2 Why a server-only HACS integration cannot directly open HealthKit

Home Assistant Core normally runs on Linux. Apple's HealthKit data access is an Apple-platform API requiring HealthKit entitlement and user authorization on the Apple device. There is no general-purpose public LAN/iCloud REST endpoint that lets a Linux Home Assistant server directly read the iPhone Health database.

Therefore full native HealthKit access requires an Apple-platform transport.

### 3.3 Full-catalog strategy

Priority order:

1. Use official Home Assistant iOS health sensors wherever they already expose enough data.
2. Prefer contributing additional HealthKit object support and normalized transport upstream to `home-assistant/iOS`, preserving a one-app user experience.
3. Keep the standalone HealthLink iOS Bridge only as an advanced fallback for object types or transport capabilities that cannot be delivered through the official Companion app.
4. Apple Shortcuts and Health export import can be optional limited/manual fallbacks, never the primary continuous sync design.

The HA integration side must stay ready to accept normalized quantity, category, workout, route, ECG, heartbeat series, audiogram, clinical/FHIR, medication, assessment, state-of-mind and future HealthKit object families.

## 4. Primary differentiators

### 4.1 Health Composer

Users can combine HealthKit and Home Assistant data into a new Home Assistant sensor without writing code.

Example:

```text
HRV ─┐
     ├─ personal baseline transform ─┐
RHR ─┘                              │
Deep sleep ─────────────────────────┤
Bedroom CO₂ ────────────────────────┤ → user-defined context sensor
Bedroom temperature ────────────────┘
```

The formula engine must use a restricted AST interpreter. `eval` and `exec` are prohibited.

Supported safe building blocks should grow toward arithmetic, average, ratio, clamp, normalize, coalesce, conditionals, baseline-relative transforms, rolling operations and correlations.

### 4.2 Personal Baseline Engine

HealthLink compares the user with their own history instead of applying universal health thresholds.

Required windows: 7, 28, 90 and 365 days.  
Required robust statistics: median, MAD, relative change, percentile and robust z-score where sufficient data exists.

Derived context values must publish a confidence/completeness indicator. They must use labels such as `above_baseline`, `within_baseline`, `below_baseline` and `insufficient_data`, not `healthy`, `sick`, `normal` or `abnormal`.

### 4.3 Health + Home Timeline

HealthLink Studio must allow an administrator to place selected health samples and permitted Home Assistant history on one time axis.

Typical use cases:

- sleep stages versus bedroom CO₂/temperature/humidity;
- HRV versus prior workout load;
- activity versus occupancy/location context;
- sleep summary versus HVAC and window state changes.

### 4.4 Context Insights

HealthLink can calculate observational relationships between health outcomes and HA environment metrics.

Output requirements:

- number of matched samples;
- correlation coefficient where statistically possible;
- direction/strength label;
- observed preferred range where enough data exists;
- explicit no-causation language.

The system must never state that a home condition caused a medical or physiological result from correlation alone.

### 4.5 Adaptive Home foundations

HealthLink should expose derived context values usable in Home Assistant automations, such as personal recovery-below-baseline or data-stale state.

Automatic self-optimization must remain off by default. Any future automatic environment actuation requires explicit opt-in, bounded actuator ranges, minimum sample counts, cooldowns, rollback conditions and confidence thresholds.

## 5. Universal Health Store

Raw/high-frequency health data must not be spammed into Home Assistant Recorder.

HealthLink keeps a per-profile SQLite database under Home Assistant's private config area with WAL mode. The store must support:

- normalized scalar samples;
- category/event samples;
- structured objects;
- chunked high-frequency series;
- source provenance;
- local-date aggregation using the HA timezone;
- per-type exposure state;
- sync sequence/replay state;
- Composer definitions;
- audit events.

Only metrics deliberately exposed as Home Assistant entities enter the ordinary entity/Recorder layer.

## 6. HealthKit object model

The normalized ingest envelope must be able to represent at minimum:

- quantity samples;
- category samples and duration events;
- characteristics/profile information where Apple allows access;
- correlations;
- activity summaries;
- workouts;
- workout routes;
- heartbeat series;
- ECG;
- audiograms/hearing records;
- state of mind;
- scored assessments;
- clinical/FHIR records;
- vision prescriptions;
- medications and dose events;
- future Apple data types without redesigning the HA storage model.

Structured/high-frequency objects must be queried through private HealthLink APIs and summarized for HA entities rather than placed wholesale into entity attributes.

## 7. Source intelligence

HealthKit data can originate from Apple Watch, iPhone, third-party apps and accessories. HealthLink must preserve source provenance and avoid naive double-counting.

Required provenance fields where available include source/app name, bundle identifier, device name, product type and source revision/version.

For official Companion aggregate/snapshot sensors, HealthLink must treat the received value according to its aggregation semantics rather than sum repeated state updates.

## 8. Home Assistant entities

Default entity count must stay deliberately small. Initial derived pack:

- last sync;
- sync latency;
- data confidence;
- steps today;
- active energy today;
- exercise time today;
- latest sleep duration/deep/REM/efficiency;
- recovery context and confidence;
- HRV/resting-HR/sleep/activity versus personal baseline;
- data stale;
- recovery below baseline.

Additional raw metrics are opt-in through HealthLink Studio. Sensitive metrics require an additional privacy opt-in.

No live `sleeping` binary sensor may be inferred from a daily sleep summary unless the input source provides reliable live episode semantics.

## 9. HealthLink Studio

A sidebar panel provides the main user experience. It is administrator-only because it exposes sensitive health context and advanced controls.

Required tabs:

### Today
- setup guidance when no data exists;
- steps, sleep, deep sleep, sleep efficiency;
- personal recovery context and confidence;
- last sync and catalog/store status.

### Health data
- searchable HealthKit catalog;
- domain, sample count, last sample;
- one-click create/hide HA entity;
- privacy-aware handling of sensitive metrics.

### Timeline
- choose one HealthLink metric;
- optionally choose a numeric HA entity;
- choose time window;
- render one chronological event stream.

### Create sensor
- choose HealthKit input A;
- choose HealthKit or HA input B;
- choose safe calculation;
- name/unit;
- create a persistent HA sensor definition.

### Insights
- choose health outcome and HA environment metric;
- choose window and desired direction;
- show observational correlation and preferred observed range;
- always display no-causation disclaimer.

### Connection
- standard mode clearly states that no separate HealthLink iOS app is required;
- shows official Companion sensor count/status;
- tells the user exactly where to enable Apple Health sensors;
- advanced full transport is visibly optional;
- Bridge pairing secret is visible to administrators only.

## 10. Security and privacy

Defaults:

- no HealthLink cloud relay;
- no telemetry;
- sensitive entity exposure OFF;
- write-back OFF;
- self-optimizing control OFF;
- Studio/raw APIs admin-only;
- health values omitted from diagnostics;
- Bridge secrets omitted from diagnostics;
- exports outside `/config/www` and restrictive permissions where supported.

Bridge requests use HMAC-SHA256 over timestamp, monotonic sequence, nonce and body digest. Reject stale timestamps, invalid signatures and non-increasing sequences. Webhook error responses must not leak payload contents or secrets.

Public issue templates must warn users not to attach raw HealthKit exports, ECG/FHIR content, medication names, webhook paths or secrets.

## 11. Services/actions

Initial actions:

- `health_link.recalculate`
- `health_link.refresh_baseline`
- `health_link.sync_request`
- `health_link.backfill_request`
- `health_link.enable_metric`
- `health_link.disable_metric`
- `health_link.export`
- `health_link.purge`

Destructive or sensitive operations must require administrator context when invoked by a logged-in user.

## 12. Multi-user model

Each HealthLink config entry represents one private health profile. Do not silently mix iPhones. Multi-user support must remain profile-isolated at storage, entity, sync and UI layers.

Future visibility classes may include private/owner-only, household summary and automation-only, but must never weaken HA's existing permission model.

## 13. Performance requirements

- All SQLite I/O off the event loop.
- WAL and indexed time/type queries.
- Maximum inbound batch size.
- Maximum webhook body size.
- Maximum Studio query limits.
- High-frequency series chunking.
- No unbounded health payload in HA entity attributes.
- Immediate entity-registry discovery plus low-frequency rescan only as recovery fallback.

## 14. HACS/release requirements

Repository must contain exactly one integration under `custom_components/health_link`, `manifest.json`, `hacs.json`, translations, README, license, issue template, tests and GitHub Actions for HACS/Hassfest/tests.

Before HACS default-store submission:

1. repository name is exactly `HA-Health-Link`;
2. repository is Public;
3. manifest documentation/issue URLs resolve;
4. HACS validation passes without ignores;
5. Hassfest passes;
6. unit/smoke tests pass against supported Home Assistant version;
7. brand assets are submitted/accepted as required;
8. GitHub Release matches manifest version.

## 15. Definition of done for v0.1

v0.1 is complete when a user can install through HACS custom repositories, add HealthLink entirely through UI, enable Apple Health sensors in the official HA iPhone app, see them imported without manual entity configuration, use baseline/Studio/Composer/Timeline/Insights, and uninstall/reload without orphaned runtime resources.

The release must not claim full native HealthKit catalog collection until an Apple-platform transport has actually shipped and been device-tested. The preferred future transport is the official Home Assistant iOS app; standalone HealthLink Bridge remains optional fallback.

## 16. Future phases

1. Expand official Companion-supported HealthKit catalog upstream.
2. Add normalized rich-object transport to official Companion where accepted.
3. Add full workout episode model and route viewer.
4. Add ECG/heartbeat series explorer without Recorder spam.
5. Add deeper source overlap/dedup intelligence.
6. Add guarded environment experiments and rollback-aware optimization.
7. Add explicitly authorized per-type HealthKit write-back where Apple permits it.
8. Add richer profile privacy/household sharing policies without exposing private raw health content.

Every future phase inherits the core rule: **the ordinary user path must remain easier than the technology underneath it.**
