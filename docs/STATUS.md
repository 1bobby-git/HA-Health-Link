# HealthLink implementation status

This document separates **implemented code** from the longer-term PRD so users and contributors are never asked to assume a feature exists when it does not.

## 0.1.0 implemented

| Area | Status | Notes |
|---|---|---|
| HACS custom integration layout | Implemented | One integration under `custom_components/health_link`. |
| UI Config Flow | Implemented | No YAML. One detected iPhone binds automatically; multiple iPhones require one safe ownership choice. |
| Official HA iOS Apple Health import | Implemented | Known metrics plus future `health_` Companion sensors are dynamically accepted. |
| Local universal store | Implemented | SQLite/WAL, local-time daily handling, provenance, structured objects, high-frequency series chunks. |
| Personal baseline | Implemented | 7/28/90/365 day robust baseline and relative change. |
| Recovery context | Implemented | Wellness-only personal-baseline context with confidence; not clinical scoring. |
| Health Composer | Implemented | Restricted arithmetic/formula engine and no-code Studio builder. |
| Health + Home timeline | Implemented | Combines HealthLink samples with permitted HA Recorder history. |
| Observational insights | Implemented | Correlation and observed preferred ranges with no-causation wording. |
| Metric exposure controls | Implemented | Sensitive exposure off by default. |
| Admin-only private Studio | Implemented | Raw health views and advanced APIs are not available to ordinary HA users by default. |
| Bridge server protocol | Implemented | Signed/replay-protected normalized ingest endpoint. |
| ECG/route/series storage | Implemented server side | Stored as structured/chunk data, not normal HA state spam. |
| Diagnostics privacy | Implemented | Raw values and secrets excluded. |
| Korean/English | Implemented | Setup translations plus bilingual Studio UI. |

## Intentionally not claimed as complete in 0.1.0

| Area | Why | Planned direction |
|---|---|---|
| Native full-HealthKit transport | A HACS integration running on Linux cannot call Apple's HealthKit API directly. | **Preferred:** upstream the full transport into the official Home Assistant iOS app. **Fallback:** optional standalone HealthLink Bridge only where upstream coverage is insufficient. |
| Every HealthKit object adapter on iOS | The server accepts arbitrary normalized types, but the shipped iOS folder is a protocol scaffold, not an exhaustive production app. | Catalog-driven adapters for quantity, category, correlations, workouts/routes, ECG/series, audiogram, clinical/FHIR, medication, assessments and future types. |
| Live `sleeping` binary sensor | Official Companion sleep metrics are summaries and cannot safely prove the user is sleeping now. | Add only when reliable live episode/source semantics exist. |
| Automatic environment actuation | Unsafe to optimize and control a home from early observational data without guardrails. | Opt-in experiments, bounds, cooldowns, rollback and confidence thresholds. |
| HealthKit write-back | Requires native iOS implementation and per-type Apple write authorization. | Explicit per-type opt-in only; default remains read-only. |
| HACS default-store inclusion | Requires public repo metadata, brand assets, passing remote checks and a GitHub Release. | Complete only after the public repository exists and validations pass. |

## User-experience rule

A normal user must not need to know entity IDs, construct webhook URLs, edit YAML, inspect a database or understand HealthKit class names. Advanced details remain behind the optional Connection/Health data views.

## Transport policy

The default product is the **Home Assistant HACS integration + the official Home Assistant iOS Companion app**. A separate HealthLink iOS app must never be presented as required for ordinary use. Full HealthKit expansion follows the priority order documented in [`DATA_SOURCES.md`](DATA_SOURCES.md): official Companion upstream first, standalone Bridge only as an advanced fallback.
