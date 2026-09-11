# Contributing to HealthLink

## Principles

1. Keep the normal user path UI-first. Do not require YAML, manual entity IDs, tokens or webhook construction when Home Assistant can discover the information.
2. Never silently combine health data from multiple people or devices.
3. Keep sensitive data out of logs, diagnostics and public bug reports.
4. Do not represent observational correlation as medical or causal advice.
5. Do not place high-frequency HealthKit series such as ECG samples directly into Home Assistant Recorder.
6. Maintain backward-compatible normalized Bridge envelopes where practical.

## Development checks

```bash
python -m compileall -q custom_components/health_link
python -m pytest -q
node --check custom_components/health_link/frontend/health-link-panel.js
```

CI additionally runs critical Ruff checks, HACS validation and Hassfest.

## Translation

HealthLink is a custom integration. Translation files live directly under `custom_components/health_link/translations/` and must contain complete user-facing strings.
