# HealthLink Bridge (iOS source scaffold)

The Home Assistant integration cannot call HealthKit directly because Home Assistant normally runs on Linux. The optional iOS Bridge is the native side of the protocol for HealthKit object types that the official HA Companion app does not expose.

This directory is intentionally **not presented to end users as an installation requirement in v0.1.0**. The preferred full-catalog route is to extend the official Home Assistant iOS app. A standalone HealthLink Bridge remains an advanced fallback when upstream coverage is insufficient.

The server protocol is already implemented in the HACS integration. This source scaffold contains the normalized envelope/signature model. Production work still required before any standalone distribution includes the complete SDK-versioned HealthKit catalog, per-object query adapters, authorization UX, background/anchor sync, offline queue, deletion tombstones and device testing.
