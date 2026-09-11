# HealthLink

**Apple Health & HealthKit × Home Assistant — local-first health context platform.**

HealthLink does not stop at copying health values into Home Assistant. It connects body data with home data so users can create personal baselines, combine HealthKit and HA entities, inspect a shared timeline, discover observed relationships, and build automations around context instead of fixed medical thresholds.

> HealthLink is a wellness/context integration, not a medical device and not a diagnostic system.

## Why HealthLink?

- **No YAML required.** The default setup automatically discovers Apple Health sensors already exposed by the official Home Assistant iOS Companion app.
- **Health Composer.** Build a new HA sensor from a HealthKit metric plus another HealthKit or Home Assistant entity without writing code.
- **Personal baseline.** Compare HRV, resting heart rate, sleep and activity against the user's own recent history instead of a universal threshold.
- **Health + Home timeline.** Place health samples and home/environment states on the same time axis.
- **Context Insights.** Inspect observational correlations such as deep sleep vs bedroom CO₂ or HRV vs room temperature. HealthLink explicitly does not claim causation.
- **Recorder protection.** Raw health samples live in a private HealthLink SQLite store; only selected metrics become HA entities.
- **Local-first privacy.** No cloud relay, telemetry or external analytics service is required.
- **Private by default.** HealthLink Studio and raw health-data APIs are administrator-only; sensitive entity exposure is opt-in.
- **Full HealthKit protocol.** The HA side accepts normalized quantity, category, workout, route, ECG, audiogram, clinical/FHIR, medication, assessment and other structured objects through the optional HealthLink Bridge protocol.

## What HealthLink actually is

**HealthLink is a Home Assistant HACS integration.** The standard mode does **not** require a separate HealthLink iOS app.

The normal data path is: **Apple Health / HealthKit → official Home Assistant iPhone app → HA `mobile_app` health sensors → HealthLink**. HealthLink then stores, combines and analyzes the data locally in Home Assistant.

For HealthKit object families the official Companion app does not expose yet, HealthLink keeps an advanced normalized transport protocol. The preferred long-term implementation is to contribute that transport upstream to the official Home Assistant iOS app. A standalone HealthLink iOS Bridge is a fallback/advanced option, not a normal installation requirement. See [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md).

## Current data paths

### 1. Recommended / easiest: Home Assistant Companion

For current Apple Health sensors exposed by the official HA iOS app:

1. Install HealthLink.
2. Add **HealthLink** in **Settings → Devices & services**.
3. On iPhone open **Home Assistant → Settings → Sensors → Apple Health Sensors**.
4. Enable the health sensors you want. If your Companion version shows **Enable all Apple Health sensors**, you can use it for the easiest setup.
5. Open HealthLink from the HA sidebar. Discovery and import are automatic.

No entity IDs, webhooks, tokens or YAML are required.

### 2. Advanced: HealthLink Bridge protocol

Some HealthKit object families are not currently exposed by the official Companion app. HealthLink therefore includes a signed, replay-protected Bridge protocol and iOS Bridge source scaffold for future full-catalog delivery.

**Important:** v0.1.0 does not ship an App Store/TestFlight HealthLink Bridge binary. End users do not need the Bridge for the normal Companion mode. Full HealthKit object coverage requires an Apple-platform transport because a Linux Home Assistant server cannot directly call Apple's HealthKit APIs. The preferred route is to add that transport to the official Home Assistant iOS app; a standalone Bridge is fallback only.

## HealthLink Studio

The integration adds a **HealthLink** sidebar panel with:

- **Today** — steps, sleep, recovery context, confidence and sync status.
- **Health data** — catalog/explorer with per-metric HA entity exposure.
- **Timeline** — HealthKit + selected Home Assistant numeric entity changes.
- **Create sensor** — no-code Health Composer.
- **Insights** — correlation and observed preferred environmental ranges.
- **Connection** — Companion/Bridge status and admin-only advanced pairing data.

## Privacy defaults

HealthLink intentionally starts conservative:

- sensitive entity exposure: **OFF**
- self-optimizing environment control: **OFF**
- HealthKit write-back: **OFF**
- health values in diagnostics: **never**
- exports: private `/config/health_link_exports`, never `/config/www`
- Bridge transport: HMAC-SHA256, timestamp/sequence validation

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

Additional raw HealthKit metrics are opt-in from **HealthLink → Health data**.

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

## Bridge envelope

```json
{
  "schema_version": 1,
  "profile_id": "p_...",
  "bridge_id": "iphone_...",
  "sequence": 42,
  "sent_at": "2026-09-11T18:30:00+09:00",
  "items": [
    {
      "object_kind": "quantity",
      "type_id": "HKQuantityTypeIdentifierHeartRate",
      "sample_uuid": "...",
      "start": "...",
      "end": "...",
      "numeric_value": 72,
      "unit": "count/min",
      "domain": "heart",
      "source": {"name": "Apple Watch"}
    }
  ]
}
```

Structured objects can additionally send `payload` / `structured_value`; HealthLink stores them outside HA entity attributes.

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

Repository layout is prepared for HACS validation:

- exactly one integration under `custom_components/`
- `manifest.json` with `version`, `config_flow`, `integration_type`, `iot_class`
- root `hacs.json`
- `translations/en.json` and `translations/ko.json`
- HACS Action
- Hassfest Action
- Python unit tests
- no `strings.json` (custom integrations use `translations/` directly in current Home Assistant)

HACS default inclusion still requires public GitHub hosting, repository description/topics/issues, brand assets accepted in `home-assistant/brands`, passing HACS/Hassfest checks without ignores, and a GitHub Release.

## Project documentation

- Detailed product and implementation specification: [`docs/HealthLink_PRD_v1.0.md`](docs/HealthLink_PRD_v1.0.md)
- Data-source and transport policy: [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md)
- Shipped vs planned feature matrix: [`docs/STATUS.md`](docs/STATUS.md)

## Development status

`0.1.0` is the first HACS custom-repository-ready server integration implementation. The default Companion path, local store, baseline engine, Studio, Composer, timeline, observational insights, Bridge ingest protocol, privacy controls and diagnostics are implemented in this repository. Native full-HealthKit transport, automatic environment actuation and HealthKit write-back remain opt-in later phases and must not be represented as completed until they are shipped and tested on iOS.

## License

MIT
