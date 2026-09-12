# Changelog

All notable changes to HealthLink are documented here.

## [0.3.3] - 2026-09-12

### Studio UI/UX
- Redesign HealthLink Studio with a clearer dashboard hierarchy based on user feedback: **Today summary → goals/data status → recent insight/quick actions**.
- Reduce the visual radius to 12px/10px/8px for cards, controls and nested rows, replacing the overly rounded card-heavy appearance.
- Replace the filled active-tab pill with a lighter underline navigation and simplify header controls for profile selection, refresh, profile add and native settings.
- Rename technical labels on the Today view to easier concepts such as **회복 신호 (Recovery signal)** and **분석 준비도 (Data readiness)** while preserving the original underlying values.
- Add progress bars and current/target values for configured personal goals, plus explicit empty states when a goal or sufficient data is unavailable.
- Add **Recent insight** and **Quick actions** sections so users can understand what the current data means and jump directly to health data, Composer, connection status, or native ECG/Health import settings.
- Improve responsive layouts for tablet/mobile and reduce unnecessary shadows while retaining Home Assistant theme variables and keyboard focus states.

### Architecture
- Keep the existing HealthLink panel logic intact and load a small modern presentation module on top, reducing regression risk to profile isolation, Composer, timeline, insights and data explorer behavior.
- Keep integration settings in the native Home Assistant Options Flow; Studio remains a feature/dashboard surface only.

## [0.3.2] - 2026-09-12

### Fixed
- Make **ECG only** the default Health export import scope so an ECG import does not accidentally parse the potentially huge `export.xml` health history first.
- Keep long-running native Options Flow imports registered in Home Assistant so a browser/WebSocket disconnect does not orphan the job; reopening **건강 원본·ECG 가져오기** reconnects to the same running or completed task.
- Batch temporary SQLite staging writes in groups of 1,000 and disable durability journaling only for the disposable staging database, reducing CPU/disk overhead while preserving the single atomic live-store commit.

### UX
- Put `ECG만 · 빠름/권장` first in the import selector and clearly label the full Health export path as a large/slow operation.
- Preserve the existing full-health import path for users who deliberately want `export.xml` history.

### Diagnostics
- Import results now retain the selected scope, elapsed seconds, scanned record count and ECG point count without exposing health values.

## [0.3.1] - 2026-09-12

### UX
- Rename user-facing device selection from iPhone-only wording to **iOS/iPadOS Apple device (iPhone/iPad)** wording, matching the actual Companion device discovery logic.
- Clarify that selectable devices are official Home Assistant Companion registrations on the same HA server, not HA login accounts.
- Clarify that Apple Watch is not selected directly; Watch records can arrive through HealthKit on the selected iPhone/iPad.
- Add an in-product quick path for creating `export.zip`: Health app → profile → Export All Health Data → Export → Save to Files → HealthLink import.
- Explain that the doctor-sharing ECG PDF is not the raw waveform import format.

### Validation
- Add regression coverage proving an iPadOS Companion registration is discovered alongside iPhone while Android/macOS are excluded from the Apple Health device selector.

## [0.3.0] - 2026-09-12

### Added
- Native options menu for discovered health metric exposure and local file import.
- Bounded streaming Apple Health XML/ZIP import of quantity, category and workout records, isolated from Companion aggregate series by source and unit.
- ECG JSON and supported Apple-export style English CSV import with explicit timestamp/unit/count validation.
- Six opt-in ECG summary sensors and a native authenticated HA image entity for a non-diagnostic waveform preview.
- Administrator-only catalogue, import, ECG list/detail and paginated waveform response actions; import-complete and new-ECG-record events.

### Fixed
- Historical imports no longer reset the live Companion freshness timestamp.
- Failed parses cannot partially change the live health database; reimports use stable record IDs.
- Sensitive exposure is checked again after permission changes; unknown future Labs metrics are conservative by default.
- Existing report/trend/routine actions now enforce administrator access; unloaded profiles are excluded.
- Purging expired health data also removes expired waveform chunks.

### Preserved
- Native integration settings, duplicate summary sensors, existing profile/entity IDs, approved logos and previous features.
- ECG is not automatically collected through Labs; no private Apple APIs, extra HealthLink iOS app or medical inference.

## [0.2.1] - 2026-09-12

### Changed
- Keep the Apple Health summary entities (steps, active energy, exercise time, sleep duration/deep/REM/efficiency) enabled by default even when equivalent Mobile App entities also exist. HealthLink intentionally keeps them because they belong to the HealthLink profile and can be used consistently with its derived context and automations.
- On upgrade from v0.2.0, re-enable those summary entities only when Home Assistant marked them disabled by the integration; entities explicitly disabled by the user remain disabled.
- The integration settings gear is native Home Assistant configuration only. HealthLink Studio is no longer allowed to act as the integration configuration destination.
- Move the sidebar feature panel to `/health-link-studio` and explicitly remove the legacy `/health-link` panel registration during setup so older cached/runtime registrations cannot keep hijacking the integration settings route.

### UX
- HealthLink Studio remains available for reports, timelines, insights and Composer. Device selection, baselines, personal goals, privacy and retention are configured only through Home Assistant's native Options Flow.

## [0.2.0] - 2026-09-12

### Added
- HealthLink-specific daily context sensors: user goal progress, same-time personal activity comparison, daily goal context and daily wellness focus.
- Optional personal goals in the standard Options Flow; zero disables a goal and no medical/population target is assumed.
- Response-capable Home Assistant actions for daily reports, trends, goal management, routine evaluation/history and environment-window analysis.
- Recorder-history bootstrap for official iOS Apple Health Sensors (Labs), allowing HealthLink to reuse retained HA history without a separate iOS app.
- Goal/context events for automation use.
- Explicit Companion time semantics metadata; time-aligned Health↔Home correlation is blocked when Labs provides only the value/report time, preventing misleading associations.

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

### Added
- Support binding multiple official Companion iPhones to one HealthLink personal profile.
- Preserve source-device identity for every imported Companion sample so multi-device imports remain auditable.
- Automatic config migration from the legacy single `companion_device_id` setting to `companion_device_ids`.

### Changed
- The integration settings gear now uses Home Assistant's native Options Flow instead of routing to HealthLink Studio.
- HealthLink Studio remains a separate administrator-only sidebar workspace.

## [0.1.3] - 2026-09-12

### Fixed
- Add the required event filter for Home Assistant's high-volume `state_reported` event, preventing setup failure on current Core versions.
- Ship HealthLink branding in the integration's local `brand/` directory for the Home Assistant 2026.3+ Brands Proxy API.

## [0.1.2] - 2026-09-11

### Changed
- Remove the standalone HealthLink iOS bridge scaffold from the supported product path.
- Use the official Home Assistant iOS Companion app as the default Apple Health/HealthKit transport.
- Keep the secure webhook transport only as a dormant advanced compatibility path.

## [0.1.1] - 2026-09-11

### Fixed
- Initial HACS package and metadata fixes.
