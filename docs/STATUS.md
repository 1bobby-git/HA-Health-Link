# HealthLink implementation status

This document separates **implemented code** from the longer-term PRD so users and contributors never have to guess whether a feature is actually available.

## 0.2.0 implemented

| Area | Status | Notes |
|---|---|---|
| HACS custom integration layout | Implemented | One integration under `custom_components/health_link`. |
| UI Config Flow | Implemented | No YAML. One detected iPhone binds automatically; multiple iPhones require one safe ownership choice. |
| Official HA iOS Apple Health import | Implemented | Labs health entities are the standard live source; HealthLink does not claim a second direct HealthKit path. |
| Recorder history bootstrap | Implemented | Backfill retained Apple Health entity history from HA Recorder into the private per-profile store. |
| Personal goals and daily context | Implemented | Optional user-defined steps/exercise/energy/water/sleep goals, progress, same-time activity comparison and daily focus. |
| Automation actions | Implemented | Daily report/trends, goal management, routine evaluation/history and environment window analysis. |
| Local universal store | Implemented | SQLite/WAL, local-time daily handling, provenance, structured objects, high-frequency series chunks. |
| Personal baseline | Implemented | 7/28/90/365 day robust baseline and relative change. |
| Recovery context | Implemented | Wellness-only personal-baseline context with confidence; not clinical scoring. |
| Health Composer | Implemented | Restricted arithmetic/formula engine and no-code Studio builder. |
| Health + Home timeline | Implemented | Combines HealthLink samples with permitted HA Recorder history. |
| Observational insights | Guarded | Time-aligned health↔home correlation is disabled for standard Labs values until the original HealthKit sample/episode timestamp is available; this prevents false associations based on HA report time. |
| Metric exposure controls | Implemented | Sensitive exposure off by default. |
| Admin-only private Studio | Implemented | Raw health views and advanced APIs are not available to ordinary HA users by default. |
| Optional server ingest protocol | Implemented | Signed/replay-protected normalized ingest endpoint remains server-side for future structured transports. It is not registered in normal Companion mode. |
| ECG/route/series storage | Implemented server side | Structured/chunk storage exists so high-frequency data does not become normal HA state spam. |
| Diagnostics privacy | Implemented | Raw values and secrets excluded. |
| Korean/English | Implemented | Setup translations plus bilingual Studio UI. README is Korean-first. |
| Branding | Implemented | Final square integration icon and wide repository logo are included. |
| HACS install/config buttons | Implemented | README provides My Home Assistant HACS repository and Config Flow buttons. |

## Intentionally not claimed as complete

| Area | Why | Planned direction |
|---|---|---|
| Native full-HealthKit transport | A HACS integration running on Linux cannot call Apple's HealthKit API directly. | Prefer broader HealthKit support upstream in the official Home Assistant iOS app. |
| HealthKit types not exposed by Companion | HealthLink can only receive what an Apple-platform client is allowed to read and transmit. | Add support through the official Companion app where feasible. |
| Standalone HealthLink iOS app | A separate app makes installation and maintenance harder for ordinary users. | **Not shipped in this repository.** The previous `ios/HealthLinkBridge` development scaffold was removed in 0.1.2. |
| Live `sleeping` binary sensor | Summary sleep metrics cannot safely prove the user is sleeping right now. | Add only when reliable live episode/source semantics exist. |
| Automatic environment actuation | Early observational data is not enough for safe autonomous control. | Later opt-in experiments only, with bounds, cooldowns, rollback and confidence thresholds. |
| HealthKit write-back | Requires native iOS implementation and per-type Apple write authorization. | Remains disabled until a safe, clearly authorized implementation exists. |
| HACS default-store inclusion | Requires repository metadata, remote checks, release and upstream HACS review. | Complete only after all public repository requirements pass. |

## User-experience rule

A normal user must not need to know entity IDs, construct webhook URLs, edit YAML, inspect a database, understand HealthKit class names, use Xcode, or install a second HealthLink iOS app.

The normal path is:

```text
Apple Health / HealthKit
        ↓
official Home Assistant iOS Companion app
        ↓
HealthLink HACS integration
```

If one iPhone is eligible, HealthLink binds it automatically. If multiple iPhones are present, the user makes one explicit device choice to prevent household health data from being mixed.

## Transport policy

The current product is the **Home Assistant HACS integration + the official Home Assistant iOS Companion app**. Full HealthKit expansion follows [`DATA_SOURCES.md`](DATA_SOURCES.md): official Companion support first. The repository no longer contains a standalone HealthLink iOS Bridge scaffold.
