# HealthLink data sources and transport strategy

HealthLink is first and foremost a **Home Assistant HACS integration**. It is not designed to require a second iPhone app for ordinary use.

## Standard mode — recommended, no extra app

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

HealthLink listens for entity-registry changes, so newly enabled Apple Health sensors are discovered immediately. A 15-minute rescan remains only as a recovery fallback.

### What standard mode can use

Anything the installed version of the official Home Assistant iOS app exposes as Apple Health sensors. HealthLink knows the current common IDs and also accepts future `health_*` sensors dynamically, so adding new official Companion metrics does not require a HealthLink release just to discover them.

## Why Home Assistant Core cannot directly read HealthKit

Apple Health data is not exposed as a normal LAN or iCloud REST API that a Linux Home Assistant server can query. Direct HealthKit reads require Apple platform HealthKit APIs, an application with the HealthKit entitlement, and per-type user authorization on the Apple device.

Therefore a server-only HACS integration cannot independently open the iPhone Health database.

## Full HealthKit mode — preferred implementation order

Some HealthKit objects are richer than normal HA scalar sensor states: raw ECG, heartbeat series, workout routes, structured workouts, audiograms, clinical/FHIR records, medication events and other structured samples.

HealthLink uses the following priority order so users do not have to install unnecessary software:

1. **Official Home Assistant iOS Companion extension — preferred.** Contribute additional HealthKit types and a normalized local transport upstream to `home-assistant/iOS`. If accepted, the normal Home Assistant iOS app becomes the only iPhone app the user needs.
2. **Existing official Companion sensors.** Always use them where they already provide enough data.
3. **Standalone HealthLink iOS Bridge — fallback/advanced option only.** Ship this only for types or transport capabilities that cannot reasonably be delivered through the official Companion app.
4. **Manual/Shortcut import — limited fallback.** Apple Shortcuts or exported Apple Health files can be accepted for selected scenarios, but they are not the primary architecture because they cannot provide complete, reliable, continuous full-catalog synchronization.

## Non-app alternatives and their limitations

| Method | Extra app | Automatic | Full HealthKit | Suitable as primary path |
|---|---:|---:|---:|---:|
| Official Home Assistant iOS sensors | No extra app | Yes | No, depends on Companion coverage | **Yes** |
| Upstream full transport in Home Assistant iOS | No extra app | Yes | Target: yes where Apple APIs allow | **Preferred long term** |
| Apple Shortcuts | No extra app | Partial | No | No |
| Apple Health XML export/import | No extra app | No | Historical export only | No |
| iPhone/iCloud database scraping | No | No reliable public API | Unsupported/fragile | **Never** |
| Standalone HealthLink Bridge | Yes | Yes | Target: yes where Apple APIs allow | Advanced fallback |

## User-experience rule

A standard HealthLink user should only need to:

1. Install HealthLink from HACS.
2. Add the HealthLink integration in Home Assistant.
3. Enable desired Apple Health sensors in the official Home Assistant iPhone app.

Everything else is automatic. Advanced full-HealthKit transport must remain optional and clearly separated from this default path.
