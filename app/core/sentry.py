"""Sentry event filtering and privacy-safe scrubbing for NLC."""
from __future__ import annotations

import re
from typing import Any

_EXPECTED_LEGAL_GATE_DETAILS = (
    "Rescue plans are withheld until the underlying legal rules receive independent counsel approval and the legal score is released.",
    "Statutory deadlines are unavailable pending rule-level legal validation, company-specific applicability and independent counsel approval.",
    "Compliance risk aggregates are unavailable while statutory score release is disabled pending independent legal approval.",
)
_SENSITIVE_KEY_PARTS = (
    "authorization",
    "cookie",
    "password",
    "secret",
    "token",
    "apikey",
    "credential",
    "privatekey",
)
_BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*")


def _key_text(value: Any) -> str:
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="ignore")
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _is_sensitive_key(value: Any) -> bool:
    key = _key_text(value)
    return any(part in key for part in _SENSITIVE_KEY_PARTS)


def _redact(value: Any) -> Any:
    """Recursively redact secrets in mappings, frame locals, and header pairs."""
    if isinstance(value, dict):
        for key, item in list(value.items()):
            value[key] = "[Filtered]" if _is_sensitive_key(key) else _redact(item)
        return value
    if isinstance(value, list):
        for index, item in enumerate(value):
            if (
                isinstance(item, (list, tuple))
                and len(item) >= 2
                and _is_sensitive_key(item[0])
            ):
                replacement = [item[0], "[Filtered]", *item[2:]]
                value[index] = tuple(replacement) if isinstance(item, tuple) else replacement
            else:
                value[index] = _redact(item)
        return value
    if isinstance(value, tuple):
        return tuple(_redact(item) for item in value)
    if isinstance(value, str):
        return _BEARER_PATTERN.sub("Bearer [Filtered]", value)
    return value


def _is_expected_legal_gate_event(event: dict[str, Any]) -> bool:
    exception = event.get("exception")
    if not isinstance(exception, dict):
        return False
    values = exception.get("values")
    if not isinstance(values, list):
        return False
    for value in values:
        if not isinstance(value, dict):
            continue
        if value.get("type") not in {"HTTPException", "StarletteHTTPException"}:
            continue
        message = str(value.get("value") or "")
        if any(detail in message for detail in _EXPECTED_LEGAL_GATE_DETAILS):
            return True
    return False


def sentry_before_send(
    event: dict[str, Any],
    hint: dict[str, Any],
) -> dict[str, Any] | None:
    """Drop only known legal-gate 503s and scrub all other event payloads."""
    del hint
    try:
        if _is_expected_legal_gate_event(event):
            return None
        return _redact(event)
    except Exception:
        # Fail closed for telemetry rather than risk exporting a secret.
        return None
