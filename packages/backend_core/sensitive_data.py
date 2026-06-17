from __future__ import annotations

import re
from typing import Mapping


SENSITIVE_KEY_PARTS = (
    "authorization",
    "cookie",
    "signature",
    "secret",
    "token",
    "api-key",
    "apikey",
    "password",
)

REDACTED = "[redacted]"


def is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in SENSITIVE_KEY_PARTS)


def mask_sensitive_mapping(values: Mapping[str, object]) -> dict[str, object]:
    return {
        key: REDACTED if is_sensitive_key(str(key)) else value
        for key, value in values.items()
    }


_SECRET_FIELD_PATTERN = re.compile(
    r'("?(?:authorization|token|secret|signature|api_key|apiKey|password)"?\s*:\s*)("[^"]*"|[^,\s}]+)',
    re.IGNORECASE,
)


def mask_sensitive_text(value: str | None) -> str:
    if not value:
        return ""
    return _SECRET_FIELD_PATTERN.sub(r'\1"[redacted]"', value)
