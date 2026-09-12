# HealthLink v0.3.5 ECG import fix

v0.3.4 added the fast Korean Apple ECG parser but the live `import_uploaded()` path still referenced the legacy `health_import.read_file()` function. v0.3.5 wires the real Options Flow/service import path to `ecg_import_fast.read_file()`.

For ECG-only imports this means HealthLink reads only `electrocardiograms/*.csv` and does not parse or size unrelated `export.xml`/CDA/route payloads. The import result also records parsing/staging and live DB write durations. Derived HealthLink entities are refreshed asynchronously after the import result is returned, so the native Options Flow is not held open by full coordinator recomputation.

A Home Assistant restart is recommended after upgrading so any import task created by an older integration version is discarded.
