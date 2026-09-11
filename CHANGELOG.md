# Changelog

All notable changes to HealthLink are documented here.

## [0.1.1] - 2026-09-11

### Changed
- Made the official Home Assistant iOS Companion app the clear default and no-extra-app path.
- Simplified Config Flow and Options Flow so ordinary users are not shown unfinished Bridge, write-back or self-optimization controls.
- Prevented duplicate profiles from importing the same Companion iPhone when the device is already configured.
- Batched frequent Companion health updates before writing to SQLite and refreshing Home Assistant entities, reducing unnecessary database/coordinator work.
- Coalesced entity-registry discovery bursts while keeping newly enabled Apple Health sensors discoverable without a Home Assistant restart.
- Preserved repeated health measurements with the same value by also handling state-reported events and using the report timestamp when available.
- Added a local HACS brand icon.
- Updated CI to Python 3.14 and Home Assistant 2026.8.0 / 2026.9.1 compatibility runs.

### Security / privacy
- The optional HealthLink Bridge webhook is no longer registered in the default Companion/auto mode. It is exposed only for an explicitly configured Bridge mode.
- Unfinished HealthKit write-back and self-optimizing environment controls remain disabled and are no longer presented as usable end-user options.

### Fixed
- Fixed the previous CI environment mismatch where Home Assistant 2026.8+ was tested on Python 3.13 even though current HA packages require Python 3.14.2 or newer.
- Fixed pytest invocation so repository-local `custom_components` imports resolve consistently on GitHub Actions.

## [0.1.0] - 2026-09-11

### Added
- HACS-compatible `health_link` Home Assistant custom integration.
- Zero-YAML automatic discovery/import of Apple Health sensors exposed by the official Home Assistant iOS Companion app.
- Multi-iPhone safety: automatic import pauses instead of mixing household members when ownership is ambiguous.
- Local SQLite/WAL health store with source provenance, local-time daily aggregation, structured-object storage and chunked high-frequency series storage.
- Personal 7/28/90/365-day baseline engine and non-medical recovery context.
- HealthLink Studio sidebar panel with Today, Health data, Timeline, Create sensor, Insights and Connection views.
- No-code Health Composer with restricted AST evaluation; no `eval`/`exec`.
- HealthKit + Home Assistant timeline and observational correlation/preferred-range analysis.
- Signed optional Bridge ingest protocol with timestamp, sequence and replay protection.
- Opt-in entity exposure, sensitive-data guardrails, private export and redacted diagnostics.
- Korean and English translations.
- Example Home Assistant automation blueprints.
- HACS and Hassfest validation workflows plus unit/smoke tests.

### Privacy
- HealthLink Studio and raw/structured health-data WebSocket APIs are administrator-only.
- Sensitive health metrics are not exposed as Home Assistant entities unless explicitly enabled.
- Diagnostic output excludes raw health values and Bridge secrets.

### Known scope
- The normal user path works through the official Home Assistant iOS Companion app.
- Full HealthKit object coverage requires an Apple-platform transport because Home Assistant Core cannot access HealthKit directly.
- `0.1.0` contains the server-side universal protocol/store and an iOS source scaffold, but does not claim a production App Store/TestFlight Bridge binary.
