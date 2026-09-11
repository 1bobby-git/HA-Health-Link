"""Privacy helpers. Diagnostics must never expose health values."""
from __future__ import annotations

from typing import Any

_SECRET_KEYS = {
    "bridge_secret", "webhook_id", "token", "secret", "signature", "nonce",
    "medication", "ecg", "fhir", "glucose", "blood_pressure", "state_of_mind",
}


def redact_mapping(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            out[str(key)] = "**REDACTED**" if any(secret in lowered for secret in _SECRET_KEYS) else redact_mapping(item)
        return out
    if isinstance(value, list):
        return [redact_mapping(item) for item in value]
    return value
