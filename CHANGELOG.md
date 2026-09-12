# Changelog

All notable changes to HealthLink are documented here.

## [0.2.0] - 2026-09-12

### Added
- HealthLink-specific daily context sensors: user goal progress, same-time personal activity comparison, daily goal context and daily wellness focus.
- Optional personal goals in the standard Options Flow; zero disables a goal and no medical/population target is assumed.
- Response-capable Home Assistant actions for daily reports, trends, goal management, routine evaluation/history and environment-window analysis.
- Recorder-history bootstrap for official iOS Apple Health Sensors (Labs), allowing HealthLink to reuse retained HA history without a separate iOS app.
- Goal/context events for automation use.
- Explicit Companion time semantics metadata; time-aligned Health↔Home correlation is blocked when Labs provides only the value/report time, preventing misleading associations.

### Changed
- Duplicate raw Apple Health summary entities are disabled by default for new entity-registry entries; existing enabled entities remain intact.
- `sync_request` now refreshes from current HA Apple Health entity states instead of pretending to force iOS/HealthKit.
- `backfill_request` imports Companion Apple Health history from HA Recorder when the Companion source is active.
- Documentation now explicitly distinguishes the Mobile App HealthKit transport from HealthLink's analysis/automation layer.

### Safety
- Derived outputs remain wellness/context information only, with confidence/data-staleness guards and no medical diagnosis or medication automation.

## [0.1.5] - 2026-09-12

### Fixed
- Discover registered iOS devices before Apple Health Labs has any health entities.
- Show the selector even when exactly one unassigned iPhone remains.
- Keep waiting/failed health profiles visible and refresh the profile list on return and periodically while visible.
- Guard profile switching against stale asynchronous responses; preserve Composer forms during background status updates.
- Respect an explicitly cleared device selection; prevent auto-binding a second profile to an existing person's phone.
- Replace truncated brand PNG files with pixel-identical approved artwork; render Studio branding through authenticated local Brands Proxy API with a local image fallback.
- Add profile discovery/identity, frontend race, and full PNG integrity regression tests.
- Keep administrator-only access, per-profile storage and HA-native Options Flow unchanged.

## [0.1.4] - 2026-09-12

### Changed
- A single HealthLink personal profile can now bind multiple Home Assistant Companion iPhones owned by the same person.
- Multiple household members remain isolated by using separate HealthLink profiles; an iPhone already assigned to another profile is excluded from selection.
- Existing single-iPhone entries migrate automatically to the new multi-device list without losing their selected phone.
- The integration settings gear now opens the normal Home Assistant Options Flow. HealthLink Studio remains a separate Home Assistant sidebar panel and is no longer registered as the integration configuration panel.
- Setup text now makes it explicit that the data source is the official Home Assistant iOS **Apple Health Sensors (Labs)** feature, not a separate HealthLink app.

### Data handling
- When several iPhones are attached to one profile, HealthLink imports their `mobile_app` Apple Health sensors into the same personal store while preserving source device provenance.
- Snapshot/latest calculations continue to select the newest sample for a metric rather than summing duplicate iPhone snapshots.

## [0.1.3] - 2026-09-12

### Fixed
- Added the callback `event_filter` required by Home Assistant Core for `EVENT_STATE_REPORTED`, fixing HealthLink config-entry setup failures on current Home Assistant releases.
- Limited repeated-state processing to Apple Health entities that belong to the active HealthLink profile.

### Branding
- Added the approved horizontal HealthLink logo beside the square icon in `custom_components/health_link/brand/` so Home Assistant 2026.3+ can serve both through its local Brands Proxy API.

## [0.1.2] - 2026-09-12

### Changed
- Reworked the repository README as a Korean-first user guide with the same simple installation structure used by the other `HA-*` integrations.
- Added one-click **HACS repository** and **HealthLink Config Flow** buttons using My Home Assistant.
- Applied the final user-approved HealthLink square icon and horizontal wordmark without redesigning the logo or typography.
- Added repository-local branding assets under `assets/` and updated the integration-local brand icon.
- Clarified the normal data path as Apple Health / HealthKit → official Home Assistant iOS Companion app → HealthLink.
- Updated data-source and implementation-status documentation to match the current one-app user experience.

### Removed
- Removed the unused `ios/HealthLinkBridge` Swift development scaffold. The current HealthLink repository no longer ships or requires a separate HealthLink iOS app.
- Removed temporary repository staging/probe files left from early development.

### Scope
- Full native HealthKit expansion continues to prefer upstream support in the official Home Assistant iOS app.
- The existing server-side normalized ingest/storage model remains available for future structured transports without being exposed as a normal end-user setup requirement.

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
- Signed optional server-side ingest protocol with timestamp, sequence and replay protection.
- Opt-in entity exposure, sensitive-data guardrails, private export and redacted diagnostics.
- Korean and English translations.
- Example Home Assistant automation blueprints.
- HACS and Hassfest validation workflows plus unit/smoke tests.

### Privacy
- HealthLink Studio and raw/structured health-data WebSocket APIs are administrator-only.
- Sensitive health metrics are not exposed as Home Assistant entities unless explicitly enabled.
- Diagnostic output excludes raw health values and secrets.

### Known scope
- The normal user path works through the official Home Assistant iOS Companion app.
- Full HealthKit object coverage requires an Apple-platform transport because Home Assistant Core cannot access HealthKit directly.
