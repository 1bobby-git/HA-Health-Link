# HealthLink

**Apple Health & HealthKit × Home Assistant — local-first health context platform.**

HealthLink does not stop at copying health values into Home Assistant. It connects body data with home data so users can create personal baselines, combine HealthKit and HA entities, inspect a shared timeline, discover observed relationships, and build automations around context instead of fixed medical thresholds.

> HealthLink is a wellness/context integration, not a medical device and not a diagnostic system.

## Why HealthLink?

- **No YAML required.** The default setup automatically discovers Apple Health sensors already exposed by the official Home Assistant iOS Companion app.
- **No extra iPhone app for normal use.** The standard path uses the official Home Assistant iOS app users already have.
- **Health Composer.** Build a new HA sensor from a HealthKit metric plus another HealthKit or Home Assistant entity without writing code.
- **Personal baseline.** Compare HRV, resting heart rate, sleep and activity against the user's own recent history instead of a universal threshold.
- **Health + Home timeline.** Place health samples and home/environment states on the same time axis.
- **Context Insights.** Inspect observational correlations such as deep sleep vs bedroom CO₂ or HRV vs room temperature. HealthLink explicitly does not claim causation.
- **Recorder protection.** Raw health samples live in a private HealthLink SQLite store; only selected metrics become HA entities.
- **Local-first privacy.** No cloud relay, telemetry or external analytics service is required.
- **Private by default.** HealthLink Studio and raw health-data APIs are administrator-only; sensitive entity exposure is opt-in.
- **Efficient Companion ingestion.** Frequent Apple Health updates are batched before database/entity refreshes, and repeated equal values are preserved when Home Assistant reports them as new samples.

## What HealthLink actually is

**HealthLink is a Home Assistant HACS integration.** The standard mode does **not** require a separate HealthLink iOS app.

The normal data path is:

**Apple Health / HealthKit → official Home Assistant iPhone app → HA `mobile_app` health sensors → HealthLink**

HealthLink then stores, combines and analyzes the data locally in Home Assistant.

For HealthKit object families the official Companion app does not expose yet, HealthLink retains a server-side normalized transport protocol for future expansion. The preferred long-term implementation is to contribute broader HealthKit support to the official Home Assistant iOS app. A standalone HealthLink iOS Bridge remains an advanced fallback, not a normal installation requirement. See [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md).

## Easiest setup

1. Install **HealthLink** from HACS.
2. Add **HealthLink** in **Settings → Devices & services**.
3. On iPhone open **Home Assistant → Settings → Sensors → Apple Health Sensors**.
4. Enable the Apple Health sensors you want.
5. Open **HealthLink** from the Home Assistant sidebar.

That is the normal setup. No entity IDs, webhook addresses, tokens or YAML are required.

If only one compatible iPhone is detected, HealthLink binds it automatically. If several household iPhones expose Apple Health sensors, HealthLink asks which phone belongs to the profile instead of risking mixed health data.

Newly enabled Apple Health sensors are discovered automatically without restarting Home Assistant. A periodic rescan remains only as a recovery fallback.

## Current data source

HealthLink can automatically use every `health_*` sensor exposed by the installed version of the official Home Assistant iOS Companion app. Known metrics receive HealthKit-aware names/domains/aggregation rules, while future Companion `health_*` metrics can still be discovered dynamically.

The server-only HACS integration cannot independently read the private HealthKit database on an iPhone. Direct HealthKit access requires Apple platform APIs, the HealthKit entitlement and per-type user authorization on the Apple device. This is why the official Home Assistant iOS app is the preferred transport.

## HealthLink Studio

The integration adds a **HealthLink** sidebar panel with:

- **Today** — steps, sleep, recovery context, confidence and sync status.
- **Health data** — catalog/explorer with per-metric HA entity exposure.
- **Timeline** — health + selected Home Assistant numeric entity changes.
- **Create sensor** — no-code Health Composer.
- **Insights** — correlation and observed preferred environmental ranges.
- **Connection** — Companion status and administrator-only advanced information.

## Privacy defaults

HealthLink intentionally starts conservative:

- sensitive entity exposure: **OFF**
- unfinished environment actuation: **not exposed in normal settings**
- unfinished HealthKit write-back: **not exposed in normal settings**
- health values in diagnostics: **never**
- exports: private `/config/health_link_exports`, never `/config/www`
- optional Bridge endpoint: **not registered in default Companion/auto mode**

## Install with HACS

Until HealthLink is accepted into HACS defaults, add it as a custom repository:

1. HACS → Integrations → menu → **Custom repositories**
2. Repository: `https://github.com/1bobby-git/HA-Health-Link`
3. Category: **Integration**
4. Install **HealthLink** and restart Home Assistant.
5. Settings → Devices & services → Add integration → **HealthLink**.

## Default entities

The initial pack is intentionally small:

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

Additional metrics can be exposed from **HealthLink → Health data** instead of flooding Home Assistant with hundreds of entities by default.

## Health Composer example

Studio can create definitions such as:

```json
{
  "formula": "(a+b)/2",
  "inputs": {
    "a": {"source": "healthkit", "type_id": "HKQuantityTypeIdentifierHeartRateVariabilitySDNN"},
    "b": {"source": "ha", "entity_id": "sensor.bedroom_temperature"}
  },
  "unit": "score"
}
```

Formulas are parsed through a restricted AST interpreter. `eval` and `exec` are never used.

## Advanced/full HealthKit direction

Quantity/category values that the official Companion app exposes work through the normal path above. Rich HealthKit objects such as raw ECG waveforms, heartbeat series, workout routes, structured workouts, audiograms, clinical/FHIR records and medication events need an Apple-side native transport if they are to be synchronized in full fidelity.

HealthLink's implementation priority is:

1. Extend the **official Home Assistant iOS app** where feasible.
2. Reuse existing Companion Health sensors wherever sufficient.
3. Use a standalone HealthLink iOS Bridge only as an optional fallback for capabilities that cannot reasonably live in the official Companion app.

The HACS server integration contains the normalized storage/ingest model needed for these future structured objects, but does not claim that an App Store/TestFlight Bridge is currently shipped.

## Actions

HealthLink registers:

- `health_link.recalculate`
- `health_link.refresh_baseline`
- `health_link.sync_request`
- `health_link.backfill_request`
- `health_link.enable_metric`
- `health_link.disable_metric`
- `health_link.export`
- `health_link.purge`

Export and purge require administrator context when called by a user.

## HACS readiness

Repository layout includes:

- exactly one integration under `custom_components/`
- `manifest.json` with `version`, `config_flow`, `integration_type`, `iot_class`
- root `hacs.json`
- English and Korean translations
- a local HealthLink brand icon
- HACS Action
- Hassfest Action
- Python 3.14 tests against Home Assistant 2026.8 and 2026.9
- frontend syntax validation

For HACS default inclusion, the repository metadata must also contain a description and valid GitHub topics, all HACS/Hassfest checks must pass, and a GitHub Release must exist.

## Project documentation

- Detailed product and implementation specification: [`docs/HealthLink_PRD_v1.0.md`](docs/HealthLink_PRD_v1.0.md)
- Data-source and transport policy: [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md)
- Shipped vs planned feature matrix: [`docs/STATUS.md`](docs/STATUS.md)
- Changelog: [`CHANGELOG.md`](CHANGELOG.md)

## Development status

`0.1.1` hardens the first public HACS integration: the standard Companion path is simpler, frequent Health updates are batched, repeated equal-value samples can be retained, duplicate iPhone profiles are blocked, the optional Bridge endpoint is disabled by default, and CI targets the actual Python runtime required by current Home Assistant releases.

Native full-HealthKit transport, automatic environment actuation and HealthKit write-back remain later phases and are not represented as completed until they are shipped and tested on iOS.

## License

MIT
