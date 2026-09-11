"""Signed webhook verification for HealthLink Bridge."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import time
from typing import Mapping

from ..const import (
    MAX_CLOCK_SKEW_SECONDS, WEBHOOK_HEADER_BRIDGE, WEBHOOK_HEADER_NONCE,
    WEBHOOK_HEADER_SEQUENCE, WEBHOOK_HEADER_SIGNATURE, WEBHOOK_HEADER_TIMESTAMP,
)

class SignatureError(ValueError):
    """Raised when a bridge request cannot be authenticated."""

@dataclass(frozen=True, slots=True)
class SignedRequest:
    bridge_id: str
    sequence: int
    timestamp: int
    nonce: str


def _parse_timestamp(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        try:
            return int(datetime.fromisoformat(value.replace("Z","+00:00")).timestamp())
        except ValueError as err:
            raise SignatureError("Invalid timestamp") from err


def verify_signed_request(
    headers: Mapping[str,str], body: bytes, secret: str, *, now: int | None = None
) -> SignedRequest:
    try:
        bridge_id=headers[WEBHOOK_HEADER_BRIDGE]
        sequence=int(headers[WEBHOOK_HEADER_SEQUENCE])
        ts=_parse_timestamp(headers[WEBHOOK_HEADER_TIMESTAMP])
        nonce=headers[WEBHOOK_HEADER_NONCE]
        supplied=headers[WEBHOOK_HEADER_SIGNATURE].lower()
    except (KeyError,ValueError) as err:
        raise SignatureError("Missing or invalid signing headers") from err
    if not bridge_id or not nonce or len(nonce)>256 or sequence < 0:
        raise SignatureError("Invalid signing headers")
    current=int(time.time()) if now is None else now
    if abs(current-ts)>MAX_CLOCK_SKEW_SECONDS:
        raise SignatureError("Timestamp outside allowed clock skew")
    body_hash=hashlib.sha256(body).hexdigest()
    message=f"{ts}.{sequence}.{nonce}.{body_hash}".encode()
    expected=hmac.new(secret.encode(),message,hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected,supplied):
        raise SignatureError("Invalid signature")
    return SignedRequest(bridge_id,sequence,ts,nonce)
