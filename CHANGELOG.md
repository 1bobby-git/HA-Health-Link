# Changelog

All notable changes to HealthLink are documented here.

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
- Full HealthKit object coverage requires a native iOS Bridge because Home Assistant Core cannot access HealthKit directly.
- `0.1.0` contains the server-side universal protocol/store and an iOS source scaffold, but does not claim a production App Store/TestFlight Bridge binary.
