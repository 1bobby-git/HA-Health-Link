# Security and privacy policy

HealthLink processes personal health information. Security and privacy regressions are treated as high priority.

## Report a vulnerability

Please do **not** include real health records, HealthKit exports, Bridge secrets, webhook paths, ECG payloads, clinical/FHIR records, medication names, or other private data in a public issue.

After the GitHub repository is published, use GitHub's private vulnerability reporting feature when available. If private reporting is not available, open a minimal issue that contains no sensitive payload and asks for a private contact path.

## Security model

- Local-first: no HealthLink-operated cloud relay or telemetry is required.
- HealthLink Studio and raw health-data APIs are administrator-only.
- Optional Bridge ingest uses HMAC-SHA256 over timestamp, sequence, nonce and body digest.
- Bridge requests enforce time skew and monotonic sequence checks to reduce replay risk.
- Raw health data is stored outside Home Assistant entity attributes in a private SQLite database.
- Diagnostics intentionally omit health values and secrets.
- Sensitive metrics require explicit opt-in before entity exposure.
- Exports are written outside `/config/www` with restrictive file permissions where supported.

## Not a medical device

HealthLink is a wellness/context automation project. Baselines, scores, correlations and observed ranges are not diagnoses, medical thresholds, treatment recommendations or evidence of causation.
