## HealthLink v0.3.5

- Wire the fast ECG-only reader to the actual `import_uploaded()` path used by the native Options Flow and Home Assistant service action.
- Return the import result before the full HealthLink coordinator recomputes derived context; refresh now continues as a Home Assistant task.
- Add parser/staging and live DB write timings to import diagnostics.
- Keep v0.3.4 Korean Apple ECG CSV support and ECG-only archive filtering.
- Add regression coverage proving the real import path uses the fast reader.
