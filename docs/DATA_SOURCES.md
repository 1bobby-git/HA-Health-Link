# HealthLink data sources and transport strategy

HealthLink is a **Home Assistant HACS integration**. The normal installation does not require a separate HealthLink iPhone app.

## Standard mode — recommended

```text
Apple Health / HealthKit
        ↓
official Home Assistant iOS Companion app
        ↓
mobile_app health_* sensor entities
        ↓
HealthLink HACS integration
        ↓
local store → baselines → Composer → context/timeline/automation
```

The user enables Apple Health sensors in the official Home Assistant iOS app. HealthLink discovers the resulting `mobile_app` sensor entities automatically and starts importing them. No YAML, webhook URL, token, or manual entity ID is required.

HealthLink listens for entity-registry changes, so newly enabled Apple Health sensors are discovered immediately. A periodic rescan remains only as a recovery fallback.

### What standard mode can use

HealthLink can use the Apple Health sensors exposed by the installed version of the official Home Assistant iOS app. Current known IDs receive HealthKit-aware names, domains and aggregation rules, and future `health_*` Companion sensors can also be discovered dynamically.

## Why Home Assistant Core cannot directly read HealthKit

Apple Health data is not exposed as a normal LAN or iCloud REST API that a Linux Home Assistant server can query. Direct HealthKit reads require Apple platform HealthKit APIs, a HealthKit entitlement, and per-type user authorization on the Apple device.

Therefore a server-only HACS integration cannot independently open the iPhone Health database.

## Full HealthKit expansion policy

Some HealthKit objects are richer than normal Home Assistant scalar sensor states, including raw ECG, heartbeat series, workout routes, structured workouts, audiograms, clinical/FHIR records, medication events and other structured samples.

HealthLink follows this order:

1. **Use existing official Home Assistant iOS health sensors** wherever they already provide enough information.
2. **Prefer upstream support in the official Home Assistant iOS app** for additional HealthKit types and richer normalized transport. This preserves a one-app user experience.
3. **Use manual/Shortcut or file import only as limited optional fallbacks** for scenarios that do not require reliable continuous synchronization.

The HealthLink repository intentionally does **not** ship a standalone `ios/HealthLinkBridge` application or source scaffold. If the official Companion app cannot support a future requirement, a separate native transport may be evaluated as a separate project, but it is not part of the current HACS component and must never be presented as required for normal use.

The Home Assistant side can retain its normalized server-side ingest/storage model for future structured objects without forcing users to install another iOS app.

## Alternatives and limitations

| Method | Extra HealthLink app | Automatic | Full HealthKit | Primary path |
|---|---:|---:|---:|---:|
| Official Home Assistant iOS sensors | No | Yes | Depends on Companion coverage | **Yes** |
| Additional support upstreamed to Home Assistant iOS | No | Yes | Target: public HealthKit types where Apple APIs allow | **Preferred expansion** |
| Apple Shortcuts | No | Partial | No | No |
| Apple Health XML export/import | No | No | Historical export only | No |
| iPhone/iCloud database scraping | No | No reliable public API | Unsupported/fragile | **Never** |

## User-experience rule

A standard HealthLink user should only need to:

1. Install HealthLink from HACS.
2. Add the HealthLink integration in Home Assistant.
3. Enable desired Apple Health sensors in the official Home Assistant iPhone app.

Everything else should be automatic. Users must not be required to build an iOS app, use Xcode, sideload software, construct webhooks, edit YAML, or manually enter sensor IDs for the standard path.
