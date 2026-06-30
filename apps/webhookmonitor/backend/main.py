import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "packages"))

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel, select, delete
from typing import Any, Optional, Literal
from datetime import datetime, timezone, timedelta
import base64, hashlib, hmac, json, re as _re, uuid, logging, httpx, io
import pandas as pd
from urllib.parse import parse_qsl, urlparse
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from backend_core import create_app, get_current_user, get_session, User, require_product_access
from backend_core.database import get_managed_session
from backend_core.email_service import send_email
from backend_core.logic_bridge import detect_and_act_on_payment
from backend_core.outbox_models import SystemOutbox
from backend_core.plan_limits import (
    get_webhookmonitor_limits_for_user_id,
    reject_webhook_endpoint_count_if_needed,
    reject_webhook_rate_if_needed,
)
from backend_core.product_insights import summarize_webhooks
from backend_core.security_utils import is_public_http_url
from backend_core.sensitive_data import is_sensitive_key, mask_sensitive_mapping, mask_sensitive_text
from backend_core.worker import register_job_handler
from pydantic import BaseModel, Field as PydanticField

logger = logging.getLogger(__name__)

from cryptography.fernet import Fernet

class IntegrationsCrypto:
    _fernet = None

    @classmethod
    def get_fernet(cls):
        if cls._fernet is None:
            key_str = os.getenv("ENCRYPTION_KEY", "")
            if not key_str:
                key_bytes = b"fallback_devforge_encryption_k3y"
                key_str = base64.urlsafe_b64encode(key_bytes).decode()
            else:
                try:
                    decoded = base64.urlsafe_b64decode(key_str.encode())
                    if len(decoded) != 32:
                        raise ValueError()
                except Exception:
                    h = hashlib.sha256(key_str.encode()).digest()
                    key_str = base64.urlsafe_b64encode(h).decode()
            cls._fernet = Fernet(key_str.encode())
        return cls._fernet

    @classmethod
    def encrypt(cls, val: str) -> str:
        if not val:
            return val
        if val.startswith("enc:"):
            return val
        f = cls.get_fernet()
        return "enc:" + f.encrypt(val.encode()).decode()

    @classmethod
    def decrypt(cls, val: str) -> str:
        if not val:
            return val
        if not val.startswith("enc:"):
            return val
        try:
            f = cls.get_fernet()
            return f.decrypt(val[4:].encode()).decode()
        except Exception:
            return val

def encrypt_val(val: str) -> str:
    return IntegrationsCrypto.encrypt(val)

def decrypt_val(val: str) -> str:
    return IntegrationsCrypto.decrypt(val)

MAX_WEBHOOK_BODY_BYTES = 10 * 1024 * 1024
WEBHOOK_PUBLIC_BASE_URL = "https://webhookmonitor.devforgeapp.pro"
EXPORT_OMITTED_HEADERS = {"host", "content-length", "transfer-encoding", "connection"}
DEFAULT_WEBHOOK_METHODS = ["POST", "PUT", "PATCH", "DELETE"]
DEFAULT_RETRY_BACKOFF_SECONDS = [1, 2, 4]
SIGNATURE_PROVIDERS = {"", "stripe", "github", "shopify", "generic"}


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

# SQL migrations needed:
# ALTER TABLE webhook_requests ADD COLUMN IF NOT EXISTS user_id INTEGER;
# ALTER TABLE webhook_requests ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0;
# ALTER TABLE webhook_requests ADD COLUMN IF NOT EXISTS next_retry_at TIMESTAMP;
# ALTER TABLE webhook_requests ADD COLUMN IF NOT EXISTS last_retry_status INTEGER;
# ALTER TABLE webhook_requests ADD COLUMN IF NOT EXISTS auto_retry_enabled BOOLEAN DEFAULT FALSE;
# ALTER TABLE webhook_settings ADD COLUMN IF NOT EXISTS expected_interval_minutes INTEGER DEFAULT 0;
# ALTER TABLE webhook_settings ADD COLUMN IF NOT EXISTS alert_email VARCHAR DEFAULT '';
# ALTER TABLE webhook_settings ADD COLUMN IF NOT EXISTS auto_retry_enabled BOOLEAN DEFAULT FALSE;


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class WebhookEndpoint(SQLModel, table=True):
    __tablename__ = "webhook_endpoints"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    slug: str = Field(unique=True, index=True)
    name: str = Field(default="Default endpoint")
    allowed_methods_json: str = Field(default='["POST","PUT","PATCH","DELETE"]')
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=_utc_now_naive)


class WebhookRequest(SQLModel, table=True):
    __tablename__ = "webhook_requests"
    id: Optional[int] = Field(default=None, primary_key=True)
    request_uuid: str = Field(default_factory=lambda: str(uuid.uuid4()), index=True)
    endpoint_id: int = Field(index=True)
    user_id: Optional[int] = Field(default=None, index=True)
    method: str
    path: str
    headers_json: str = "{}"
    body: str = ""
    query_params_json: str = "{}"
    ip_address: str = ""
    received_at: datetime = Field(default_factory=_utc_now_naive)
    forward_error: str = ""
    signature_valid: Optional[bool] = None
    signature_error: str = ""
    signature_provider: str = ""
    replay_of_request_id: Optional[int] = Field(default=None, index=True)
    replay_target_url: str = ""
    replay_status: str = ""
    # Exponential backoff retry tracking
    retry_count: int = Field(default=0)
    next_retry_at: Optional[datetime] = None
    last_retry_status: Optional[int] = None
    auto_retry_enabled: bool = Field(default=False)


class WebhookSettings(SQLModel, table=True):
    __tablename__ = "webhook_settings"
    user_id: int = Field(primary_key=True)
    forward_url: str = Field(default="")
    fallback_url: str = Field(default="")
    expected_interval_minutes: int = Field(default=0)   # 0 = silence check disabled
    alert_email: str = Field(default="")
    slack_webhook_url: str = Field(default="")
    discord_webhook_url: str = Field(default="")
    auto_retry_enabled: bool = Field(default=False)     # enable auto exponential backoff
    retry_max_attempts: int = Field(default=3)
    retry_backoff_seconds_json: str = Field(default="[1, 2, 4]")
    forward_timeout_seconds: int = Field(default=30)
    signature_provider: str = Field(default="")
    signature_secret: str = Field(default="")
    last_silence_alert_sent_at: Optional[datetime] = None


class WebhookForwardRule(SQLModel, table=True):
    __tablename__ = "webhook_forward_rules"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    name: str
    match_path: str
    match_equals: str
    forward_url: str
    fallback_url: str = Field(default="")
    auto_retry_enabled: bool = Field(default=False)
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=_utc_now_naive)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class WebhookPrefsUpdate(BaseModel):
    forward_url: str = ""
    fallback_url: str = ""
    expected_interval_minutes: int = 0
    alert_email: str = ""
    slack_webhook_url: str = ""
    discord_webhook_url: str = ""
    auto_retry_enabled: bool = False
    retry_max_attempts: int = 3
    retry_backoff_seconds: list[int] = PydanticField(default_factory=lambda: DEFAULT_RETRY_BACKOFF_SECONDS.copy())
    forward_timeout_seconds: int = 30
    signature_provider: str = ""
    signature_secret: str = ""


class EndpointCreate(BaseModel):
    name: str = "Default endpoint"
    methods: list[str] = PydanticField(default_factory=lambda: DEFAULT_WEBHOOK_METHODS.copy())


class ReplayPayload(BaseModel):
    mode: Literal["exact", "modified", "alternate"] = "exact"
    target_url: str = ""
    body_override: Optional[str] = None
    headers_override: Optional[dict[str, str]] = None


class WebhookSearchPayload(BaseModel):
    json_path: str = ""
    equals: Optional[str] = None
    status: Literal["all", "failed", "successful", "pending", "auto_retry"] = "all"
    method: str = ""
    provider: str = ""
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    limit: int = 50


class RetryPayload(BaseModel):
    payload_override: Optional[str] = None  # JSON string; None = use original body
    schedule_auto_retry: bool = False        # schedule exponential backoff if delivery fails


class SchemaValidationPayload(BaseModel):
    json_schema: dict[str, Any] = PydanticField(alias="schema")


class ForwardRuleCreate(BaseModel):
    name: str
    match_path: str
    match_equals: str
    forward_url: str
    fallback_url: str = ""
    auto_retry_enabled: bool = False
    is_active: bool = True


def _matches_log_status(request: WebhookRequest, status: str) -> bool:
    last_retry_status = getattr(request, "last_retry_status", None)
    if status == "all":
        return True
    if status == "failed":
        return last_retry_status is not None and last_retry_status >= 400
    if status == "successful":
        return last_retry_status is not None and 200 <= last_retry_status < 300
    if status == "pending":
        return last_retry_status is None
    if status == "auto_retry":
        return bool(getattr(request, "auto_retry_enabled", False))
    return True


def _json_path(path: tuple[Any, ...] | list[Any]) -> str:
    output = "$"
    for part in path:
        if isinstance(part, int):
            output += f"[{part}]"
        else:
            key = str(part)
            if key.replace("_", "").replace("-", "").isalnum():
                output += f".{key}"
            else:
                output += f"[{json.dumps(key)}]"
    return output


def _mask_diff_value(path: str, value: Any) -> Any:
    if is_sensitive_key(path):
        return "[redacted]"
    if isinstance(value, dict):
        return {
            key: _mask_diff_value(f"{path}.{key}", nested_value)
            for key, nested_value in value.items()
        }
    if isinstance(value, list):
        return [
            _mask_diff_value(f"{path}[{index}]", item)
            for index, item in enumerate(value)
        ]
    if isinstance(value, str):
        return mask_sensitive_text(value)
    return value


def _parse_json_or_text(value: str) -> Any:
    try:
        return json.loads(value)
    except Exception:
        return mask_sensitive_text(value)


def _diff_values(old: Any, new: Any, path: str = "$") -> dict[str, list[dict[str, Any]]]:
    diff = {"added": [], "removed": [], "changed": []}

    if isinstance(old, dict) and isinstance(new, dict):
        old_keys = set(old)
        new_keys = set(new)
        for key in sorted(new_keys - old_keys):
            child_path = f"{path}.{key}"
            diff["added"].append({"path": child_path, "value": _mask_diff_value(child_path, new[key])})
        for key in sorted(old_keys - new_keys):
            child_path = f"{path}.{key}"
            diff["removed"].append({"path": child_path, "old_value": _mask_diff_value(child_path, old[key])})
        for key in sorted(old_keys & new_keys):
            child_path = f"{path}.{key}"
            nested = _diff_values(old[key], new[key], child_path)
            for bucket, items in nested.items():
                diff[bucket].extend(items)
        return diff

    if isinstance(old, list) and isinstance(new, list):
        shared = min(len(old), len(new))
        for index in range(shared):
            nested = _diff_values(old[index], new[index], f"{path}[{index}]")
            for bucket, items in nested.items():
                diff[bucket].extend(items)
        for index in range(shared, len(new)):
            child_path = f"{path}[{index}]"
            diff["added"].append({"path": child_path, "value": _mask_diff_value(child_path, new[index])})
        for index in range(shared, len(old)):
            child_path = f"{path}[{index}]"
            diff["removed"].append({"path": child_path, "old_value": _mask_diff_value(child_path, old[index])})
        return diff

    if old != new:
        diff["changed"].append({
            "path": path,
            "old_value": _mask_diff_value(path, old),
            "new_value": _mask_diff_value(path, new),
        })
    return diff


def _parse_request_body_json(request: WebhookRequest) -> Any:
    try:
        return json.loads(request.body or "{}")
    except Exception:
        raise HTTPException(status_code=400, detail="Request body must be valid JSON for schema validation")


def _schema_error_path(error) -> str:
    return _json_path(list(error.absolute_path))


def _serialize_forward_rule(rule: WebhookForwardRule) -> dict[str, Any]:
    return {
        "id": rule.id,
        "name": rule.name,
        "match_path": rule.match_path,
        "match_equals": rule.match_equals,
        "forward_url": rule.forward_url,
        "fallback_url": rule.fallback_url,
        "auto_retry_enabled": rule.auto_retry_enabled,
        "is_active": rule.is_active,
        "created_at": rule.created_at.isoformat() if rule.created_at else None,
    }


def _validate_forward_rule_urls(forward_url: str, fallback_url: str = "") -> None:
    if not is_public_http_url(forward_url):
        raise HTTPException(status_code=400, detail="Forward URL must be a public http(s) URL")
    if fallback_url and not is_public_http_url(fallback_url):
        raise HTTPException(status_code=400, detail="Fallback URL must be a public http(s) URL")


def _extract_match_value(payload: Any, match_path: str) -> Any:
    normalized = match_path.strip().removeprefix("$.").removeprefix("$")
    if not normalized:
        return payload

    current = payload
    # Split on dots but handle array notation like events[0]
    parts = _re.split(r'\.|(?=\[)', normalized)
    for part in parts:
        if not part:
            continue
        # Handle array index notation: [0], [1], etc.
        idx_match = _re.match(r'^\[(\d+)\]$', part)
        if idx_match:
            index = int(idx_match.group(1))
            if isinstance(current, list) and 0 <= index < len(current):
                current = current[index]
            else:
                return None
            continue
        # Handle mixed: events[0]
        bracket_match = _re.match(r'^(\w+)\[(\d+)\]$', part)
        if bracket_match:
            key, index = bracket_match.group(1), int(bracket_match.group(2))
            if isinstance(current, dict):
                current = current.get(key)
            else:
                return None
            if isinstance(current, list) and 0 <= index < len(current):
                current = current[index]
            else:
                return None
            continue
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            index = int(part)
            current = current[index] if 0 <= index < len(current) else None
        else:
            return None
    return current


def _rule_matches_body(rule: WebhookForwardRule, body: str) -> bool:
    try:
        payload = json.loads(body or "{}")
    except Exception:
        return False
    value = _extract_match_value(payload, rule.match_path)
    return str(value) == rule.match_equals


def _select_forward_rule(rules: list[WebhookForwardRule], body: str) -> WebhookForwardRule | None:
    for rule in rules:
        if rule.is_active and _rule_matches_body(rule, body):
            return rule
    return None


def _safe_json_dict(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value or "{}")
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _safe_json_list(value: str, default: list[Any]) -> list[Any]:
    try:
        parsed = json.loads(value or "[]")
    except Exception:
        return default
    return parsed if isinstance(parsed, list) else default


def _allowed_methods(endpoint: WebhookEndpoint) -> list[str]:
    methods = _safe_json_list(getattr(endpoint, "allowed_methods_json", ""), DEFAULT_WEBHOOK_METHODS.copy())
    normalized = [str(method).upper() for method in methods if str(method).strip()]
    return normalized or DEFAULT_WEBHOOK_METHODS.copy()


def _headers_lookup(headers: dict[str, Any], name: str) -> str:
    wanted = name.lower()
    for key, value in headers.items():
        if str(key).lower() == wanted:
            return str(value)
    return ""


def _body_bytes(body: bytes | str) -> bytes:
    if isinstance(body, bytes):
        return body
    return str(body).encode("utf-8")


def _signature_response(
    valid: bool,
    error: str = "",
    details: Optional[dict[str, Any]] = None,
    provider: str = "",
) -> dict[str, Any]:
    return {
        "valid": valid,
        "error": error,
        "details": details or {},
        "provider": provider,
    }


def _parse_stripe_signature(header: str) -> dict[str, list[str]]:
    parsed: dict[str, list[str]] = {}
    for part in header.split(","):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        parsed.setdefault(key.strip(), []).append(value.strip())
    return parsed


def _verify_rsa_sha256(public_key_pem: str, signature: str, body: bytes) -> bool:
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.exceptions import InvalidSignature
    except Exception:
        return False

    try:
        public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
        public_key.verify(base64.b64decode(signature), body, padding.PKCS1v15(), hashes.SHA256())
        return True
    except (InvalidSignature, ValueError):
        return False


def validate_webhook_signature(
    provider: str,
    secret: str,
    headers: dict[str, Any],
    body: bytes | str,
    *,
    now: Optional[datetime] = None,
    tolerance_seconds: int = 300,
) -> dict[str, Any]:
    provider_name = (provider or "").strip().lower()
    if provider_name not in SIGNATURE_PROVIDERS or not provider_name:
        return _signature_response(False, "unsupported_provider", {"provider": provider}, provider_name)
    if not secret:
        return _signature_response(False, "missing_secret", provider=provider_name)

    raw_body = _body_bytes(body)
    now_utc = now or datetime.now(timezone.utc)

    if provider_name == "stripe":
        header = _headers_lookup(headers, "stripe-signature")
        if not header:
            return _signature_response(False, "missing_signature_header", {"header": "stripe-signature"}, provider_name)
        parts = _parse_stripe_signature(header)
        timestamps = parts.get("t") or []
        signatures = parts.get("v1") or []
        if not timestamps or not signatures:
            return _signature_response(False, "malformed_signature_header", {"header": "stripe-signature"}, provider_name)
        try:
            timestamp = int(timestamps[0])
        except ValueError:
            return _signature_response(False, "invalid_timestamp", {"timestamp": timestamps[0]}, provider_name)
        diff_seconds = abs(int(now_utc.timestamp()) - timestamp)
        if diff_seconds > tolerance_seconds:
            return _signature_response(
                False,
                "timestamp_too_old",
                {
                    "now": now_utc.isoformat(),
                    "timestamp": datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat(),
                    "diff_minutes": round(diff_seconds / 60, 2),
                },
                provider_name,
            )
        signed_payload = f"{timestamp}.".encode("utf-8") + raw_body
        expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
        if any(hmac.compare_digest(expected, signature) for signature in signatures):
            return _signature_response(True, provider=provider_name)
        return _signature_response(False, "signature_mismatch", {"header": "stripe-signature"}, provider_name)

    if provider_name == "github":
        header = _headers_lookup(headers, "x-hub-signature-256")
        if not header.startswith("sha256="):
            return _signature_response(False, "missing_signature_header", {"header": "x-hub-signature-256"}, provider_name)
        expected = "sha256=" + hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        return _signature_response(
            hmac.compare_digest(expected, header),
            "" if hmac.compare_digest(expected, header) else "signature_mismatch",
            {"header": "x-hub-signature-256"},
            provider_name,
        )

    if provider_name == "shopify":
        header = _headers_lookup(headers, "x-shopify-hmac-sha256")
        if not header:
            return _signature_response(False, "missing_signature_header", {"header": "x-shopify-hmac-sha256"}, provider_name)
        expected = base64.b64encode(hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).digest()).decode("utf-8")
        return _signature_response(
            hmac.compare_digest(expected, header),
            "" if hmac.compare_digest(expected, header) else "signature_mismatch",
            {"header": "x-shopify-hmac-sha256"},
            provider_name,
        )

    header = _headers_lookup(headers, "x-signature")
    if not header:
        return _signature_response(False, "missing_signature_header", {"header": "x-signature"}, provider_name)
    algorithm, _, supplied = header.partition("=")
    algorithm = algorithm.lower().strip()
    supplied = supplied.strip() if supplied else algorithm
    if not supplied:
        return _signature_response(False, "malformed_signature_header", {"header": "x-signature"}, provider_name)
    if algorithm in ("sha256", "hmac-sha256", ""):
        expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    elif algorithm in ("sha1", "hmac-sha1"):
        expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha1).hexdigest()
    elif algorithm in ("rsa-sha256", "rsa"):
        valid = _verify_rsa_sha256(secret, supplied, raw_body)
        return _signature_response(
            valid,
            "" if valid else "signature_mismatch",
            {"header": "x-signature", "algorithm": "rsa-sha256"},
            provider_name,
        )
    else:
        return _signature_response(False, "unsupported_algorithm", {"algorithm": algorithm}, provider_name)
    return _signature_response(
        hmac.compare_digest(expected, supplied),
        "" if hmac.compare_digest(expected, supplied) else "signature_mismatch",
        {"header": "x-signature", "algorithm": algorithm or "sha256"},
        provider_name,
    )


def _signature_for_settings(settings: Optional[WebhookSettings], headers: dict[str, Any], body: bytes) -> dict[str, Any]:
    if not settings or not settings.signature_provider or not settings.signature_secret:
        return {"valid": None, "error": "", "details": {}, "provider": settings.signature_provider if settings else ""}
    return validate_webhook_signature(settings.signature_provider, decrypt_val(settings.signature_secret), headers, body)


def _settings_retry_backoff(settings: Optional[WebhookSettings]) -> list[int]:
    if not settings:
        return DEFAULT_RETRY_BACKOFF_SECONDS.copy()
    values = _safe_json_list(settings.retry_backoff_seconds_json, DEFAULT_RETRY_BACKOFF_SECONDS.copy())
    cleaned = []
    for value in values[:3]:
        try:
            cleaned.append(max(1, int(float(str(value).strip()))))
        except (ValueError, TypeError):
            pass
    return cleaned or DEFAULT_RETRY_BACKOFF_SECONDS.copy()


def _serialize_request(request: WebhookRequest) -> dict[str, Any]:
    headers = mask_sensitive_mapping(_safe_json_dict(request.headers_json))
    return {
        "id": request.id,
        "event_id": getattr(request, "request_uuid", str(request.id)),
        "endpoint_id": getattr(request, "endpoint_id", None),
        "method": getattr(request, "method", ""),
        "path": getattr(request, "path", ""),
        "headers": headers,
        "body": getattr(request, "body", ""),
        "query_params": _safe_json_dict(getattr(request, "query_params_json", "{}")),
        "ip_address": getattr(request, "ip_address", ""),
        "received_at": request.received_at.isoformat() if getattr(request, "received_at", None) else None,
        "retry_count": getattr(request, "retry_count", 0),
        "next_retry_at": request.next_retry_at.isoformat() if getattr(request, "next_retry_at", None) else None,
        "last_retry_status": getattr(request, "last_retry_status", None),
        "forward_status": getattr(request, "last_retry_status", None),
        "forward_error": getattr(request, "forward_error", ""),
        "auto_retry_enabled": getattr(request, "auto_retry_enabled", False),
        "signature_valid": getattr(request, "signature_valid", None),
        "signature_error": getattr(request, "signature_error", ""),
        "signature_provider": getattr(request, "signature_provider", ""),
        "replay_of_request_id": getattr(request, "replay_of_request_id", None),
        "replay_target_url": getattr(request, "replay_target_url", ""),
        "replay_status": getattr(request, "replay_status", ""),
    }


def _parse_optional_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid datetime: {value}")
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _request_received_at_utc(request: WebhookRequest) -> datetime:
    received = request.received_at
    if received.tzinfo is None:
        return received.replace(tzinfo=timezone.utc)
    return received.astimezone(timezone.utc)


def _request_matches_search(request: WebhookRequest, criteria: WebhookSearchPayload) -> bool:
    if not _matches_log_status(request, criteria.status):
        return False
    if criteria.method and request.method.upper() != criteria.method.upper():
        return False
    if criteria.provider and getattr(request, "signature_provider", "").lower() != criteria.provider.lower():
        return False

    received = _request_received_at_utc(request)
    date_from = _parse_optional_datetime(criteria.date_from)
    date_to = _parse_optional_datetime(criteria.date_to)
    if date_from and received < date_from:
        return False
    if date_to and received > date_to:
        return False

    if criteria.json_path:
        try:
            payload = json.loads(request.body or "{}")
        except Exception:
            return False
        value = _extract_match_value(payload, criteria.json_path)
        if criteria.equals is not None and str(value) != criteria.equals:
            return False

    return True


def _validate_public_url_field(value: str, field_name: str) -> None:
    if value and not is_public_http_url(value):
        raise HTTPException(status_code=400, detail=f"{field_name} must be a public http(s) URL")


def _validate_method_list(methods: list[str]) -> list[str]:
    normalized = []
    for method in methods:
        value = str(method).strip().upper()
        if value not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            raise HTTPException(status_code=400, detail=f"Unsupported webhook method: {method}")
        if value not in normalized:
            normalized.append(value)
    return normalized or DEFAULT_WEBHOOK_METHODS.copy()


def _serialize_endpoint(endpoint: WebhookEndpoint) -> dict[str, Any]:
    return {
        "id": endpoint.id,
        "uuid": endpoint.slug,
        "name": endpoint.name,
        "endpoint_url": f"{WEBHOOK_PUBLIC_BASE_URL}/in/{endpoint.slug}",
        "methods": _allowed_methods(endpoint),
        "created_at": endpoint.created_at.isoformat() if endpoint.created_at else None,
        "is_active": endpoint.is_active,
    }


def _request_export_url(request: WebhookRequest) -> str:
    path = request.path or ""
    if path.startswith("http://") or path.startswith("https://"):
        return path
    normalized_path = path if path.startswith("/") else f"/{path}"
    return f"{WEBHOOK_PUBLIC_BASE_URL}{normalized_path}"


def _exportable_headers(headers_json: str) -> dict[str, str]:
    try:
        raw_headers = json.loads(headers_json or "{}")
    except Exception:
        raw_headers = {}

    headers: dict[str, str] = {}
    for key, value in raw_headers.items():
        normalized_key = str(key).strip()
        if not normalized_key:
            continue
        if normalized_key.lower() in EXPORT_OMITTED_HEADERS:
            continue
        headers[normalized_key] = str(value)
    return headers


def _shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _build_curl_export(request: WebhookRequest) -> str:
    url = _request_export_url(request)
    lines = [f"curl --request {request.method.upper()} {_shell_quote(url)}"]
    for key, value in _exportable_headers(request.headers_json).items():
        lines.append(f"  --header {_shell_quote(f'{key}: {value}')}")
    if request.body:
        lines.append(f"  --data-raw {_shell_quote(request.body)}")
    return " \\\n".join(lines) + "\n"


def _postman_url(raw_url: str) -> dict[str, Any]:
    parsed = urlparse(raw_url)
    url_payload: dict[str, Any] = {"raw": raw_url}
    if parsed.scheme:
        url_payload["protocol"] = parsed.scheme
    if parsed.netloc:
        url_payload["host"] = parsed.netloc.split(".")
    path_parts = [part for part in parsed.path.split("/") if part]
    if path_parts:
        url_payload["path"] = path_parts
    query_parts = [{"key": key, "value": value} for key, value in parse_qsl(parsed.query, keep_blank_values=True)]
    if query_parts:
        url_payload["query"] = query_parts
    return url_payload


def _build_postman_collection(request: WebhookRequest) -> dict[str, Any]:
    url = _request_export_url(request)
    item_request: dict[str, Any] = {
        "method": request.method.upper(),
        "header": [
            {"key": key, "value": value}
            for key, value in _exportable_headers(request.headers_json).items()
        ],
        "url": _postman_url(url),
    }
    if request.body:
        item_request["body"] = {
            "mode": "raw",
            "raw": request.body,
            "options": {"raw": {"language": "json" if _looks_like_json(request.body) else "text"}},
        }
    return {
        "info": {
            "_postman_id": str(uuid.uuid4()),
            "name": f"WebhookMonitor request {request.id}",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "item": [
            {
                "name": f"{request.method.upper()} {request.path}",
                "request": item_request,
            }
        ],
    }


def _looks_like_json(value: str) -> bool:
    try:
        json.loads(value)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
webhook_router = APIRouter(prefix="/webhooks", tags=["webhooks"], dependencies=[Depends(require_product_access("webhookmonitor"))])
settings_router = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(require_product_access("webhookmonitor"))])
ingestion_router = APIRouter(tags=["ingestion"])
cron_router = APIRouter(prefix="/webhooks", tags=["cron"])


@settings_router.get("/webhook-prefs")
async def get_webhook_prefs(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(WebhookSettings).where(WebhookSettings.user_id == user.id))
    ws = result.scalar_one_or_none()
    if not ws:
        ws = WebhookSettings(user_id=user.id)
        session.add(ws)
        await session.flush()
    return {
        "forward_url": ws.forward_url,
        "fallback_url": ws.fallback_url,
        "expected_interval_minutes": ws.expected_interval_minutes,
        "alert_email": ws.alert_email,
        "slack_webhook_url": decrypt_val(ws.slack_webhook_url),
        "discord_webhook_url": decrypt_val(ws.discord_webhook_url),
        "auto_retry_enabled": ws.auto_retry_enabled,
        "retry_max_attempts": ws.retry_max_attempts,
        "retry_backoff_seconds": _settings_retry_backoff(ws),
        "forward_timeout_seconds": ws.forward_timeout_seconds,
        "signature_provider": ws.signature_provider,
        "signature_secret": "",
        "signature_secret_set": bool(ws.signature_secret),
    }


async def _save_webhook_prefs(
    body: WebhookPrefsUpdate,
    user: User,
    session: AsyncSession,
):
    result = await session.execute(select(WebhookSettings).where(WebhookSettings.user_id == user.id))
    ws = result.scalar_one_or_none()
    if not ws:
        ws = WebhookSettings(user_id=user.id)
    forward_url = body.forward_url.strip()
    fallback_url = body.fallback_url.strip()
    slack_webhook_url = body.slack_webhook_url.strip()
    discord_webhook_url = body.discord_webhook_url.strip()
    _validate_public_url_field(forward_url, "Forward URL")
    _validate_public_url_field(fallback_url, "Fallback URL")
    _validate_public_url_field(slack_webhook_url, "Slack Webhook URL")
    _validate_public_url_field(discord_webhook_url, "Discord Webhook URL")

    signature_provider = body.signature_provider.strip().lower()
    if signature_provider not in SIGNATURE_PROVIDERS:
        raise HTTPException(status_code=400, detail="Unsupported signature provider")
    if signature_provider and not (body.signature_secret or ws.signature_secret):
        raise HTTPException(status_code=400, detail="Signature secret is required when a provider is selected")
    if body.retry_max_attempts not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="Retry attempts must be 1, 2, or 3")
    if body.forward_timeout_seconds not in (10, 30, 60):
        raise HTTPException(status_code=400, detail="Forward timeout must be 10, 30, or 60 seconds")
    retry_backoff_seconds = [max(1, int(value)) for value in body.retry_backoff_seconds[:3]]

    ws.forward_url = forward_url
    ws.fallback_url = fallback_url
    ws.expected_interval_minutes = body.expected_interval_minutes
    ws.alert_email = body.alert_email.strip()
    ws.slack_webhook_url = encrypt_val(slack_webhook_url)
    ws.discord_webhook_url = encrypt_val(discord_webhook_url)
    ws.auto_retry_enabled = body.auto_retry_enabled
    ws.retry_max_attempts = body.retry_max_attempts
    ws.retry_backoff_seconds_json = json.dumps(retry_backoff_seconds)
    ws.forward_timeout_seconds = body.forward_timeout_seconds
    ws.signature_provider = signature_provider
    if body.signature_secret:
        ws.signature_secret = encrypt_val(body.signature_secret)
    if not signature_provider:
        ws.signature_secret = ""
    session.add(ws)
    await session.flush()
    return {"ok": True}


@settings_router.put("/webhook-prefs")
async def update_webhook_prefs(
    body: WebhookPrefsUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    return await _save_webhook_prefs(body, user, session)


@webhook_router.post("/config")
async def update_config(
    body: WebhookPrefsUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    return await _save_webhook_prefs(body, user, session)


@webhook_router.get("/config")
async def get_config(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(WebhookEndpoint)
        .where(WebhookEndpoint.user_id == user.id)
        .order_by(WebhookEndpoint.created_at.asc())
    )
    ep = result.scalar_one_or_none()
    if not ep:
        ep = WebhookEndpoint(user_id=user.id, slug=str(uuid.uuid4()), name="Default endpoint")
        session.add(ep)
        await session.flush()
        await session.refresh(ep)
    return {"endpoint_url": f"{WEBHOOK_PUBLIC_BASE_URL}/in/{ep.slug}", "endpoint": _serialize_endpoint(ep)}


@webhook_router.get("/endpoints")
async def list_endpoints(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(WebhookEndpoint)
        .where(WebhookEndpoint.user_id == user.id)
        .order_by(WebhookEndpoint.created_at.desc())
    )
    return [_serialize_endpoint(endpoint) for endpoint in result.scalars().all()]


@webhook_router.post("/endpoints")
async def create_endpoint(
    body: EndpointCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    plan, limits = await get_webhookmonitor_limits_for_user_id(session, user.id)
    count_result = await session.execute(
        select(func.count(WebhookEndpoint.id)).where(WebhookEndpoint.user_id == user.id)
    )
    endpoint_count = count_result.scalar_one()
    reject_webhook_endpoint_count_if_needed(plan, limits, endpoint_count)

    methods = _validate_method_list(body.methods)
    name = body.name.strip() or "Default endpoint"
    endpoint = WebhookEndpoint(
        user_id=user.id,
        slug=str(uuid.uuid4()),
        name=name,
        allowed_methods_json=json.dumps(methods),
    )
    session.add(endpoint)
    await session.flush()
    await session.refresh(endpoint)
    return _serialize_endpoint(endpoint)


@webhook_router.get("/endpoints/{endpoint_id}")
async def get_endpoint(
    endpoint_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == endpoint_id,
            WebhookEndpoint.user_id == user.id,
        )
    )
    endpoint = result.scalar_one_or_none()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    return _serialize_endpoint(endpoint)


@webhook_router.delete("/endpoints/{endpoint_id}")
async def delete_endpoint(
    endpoint_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    # Delete associated webhook requests first
    await session.execute(
        delete(WebhookRequest).where(WebhookRequest.endpoint_id == endpoint_id)
    )
    await session.execute(
        delete(WebhookEndpoint).where(
            WebhookEndpoint.id == endpoint_id,
            WebhookEndpoint.user_id == user.id,
        )
    )
    await session.flush()
    return {"status": "deleted"}


@webhook_router.get("/endpoints/{endpoint_id}/events")
async def list_endpoint_events(
    endpoint_id: int,
    status: Literal["all", "failed", "successful", "pending", "auto_retry"] = Query(default="all"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    endpoint = await get_endpoint(endpoint_id, user, session)
    query = select(WebhookRequest).where(WebhookRequest.endpoint_id == endpoint["id"])
    result = await session.execute(query.order_by(WebhookRequest.received_at.desc()).limit(50))
    return [_serialize_request(request) for request in result.scalars().all() if _matches_log_status(request, status)]


@webhook_router.get("/logs")
async def list_logs(
    status: Literal["all", "failed", "successful", "pending", "auto_retry"] = Query(default="all"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    query = select(WebhookRequest).where(WebhookRequest.user_id == user.id)
    if status == "failed":
        query = query.where(WebhookRequest.last_retry_status >= 400)
    elif status == "successful":
        query = query.where(WebhookRequest.last_retry_status >= 200, WebhookRequest.last_retry_status < 300)
    elif status == "pending":
        query = query.where(WebhookRequest.last_retry_status == None)  # noqa: E711
    elif status == "auto_retry":
        query = query.where(WebhookRequest.auto_retry_enabled == True)  # noqa: E712
    result = await session.execute(query.order_by(WebhookRequest.received_at.desc()).limit(100))
    requests = [r for r in result.scalars().all() if _matches_log_status(r, status)]
    return [_serialize_request(r) for r in requests]


@webhook_router.get("/summary")
async def webhook_summary(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(WebhookRequest)
        .where(WebhookRequest.user_id == user.id)
        .order_by(WebhookRequest.received_at.desc())
        .limit(1000)
    )
    return summarize_webhooks(result.scalars().all())


@webhook_router.delete("/requests")
async def delete_requests(
    confirm: str = Query(..., description="Must be exactly 'CONFIRM' to delete all requests"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    if confirm != "CONFIRM":
        raise HTTPException(status_code=400, detail="Confirmation required. Set confirm=CONFIRM.")
    await session.execute(delete(WebhookRequest).where(WebhookRequest.user_id == user.id))
    await session.flush()
    return {"status": "deleted", "message": "All logs cleared"}


@webhook_router.get("/forward-rules")
async def list_forward_rules(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(WebhookForwardRule)
        .where(WebhookForwardRule.user_id == user.id)
        .order_by(WebhookForwardRule.id.desc())
    )
    return [_serialize_forward_rule(rule) for rule in result.scalars().all()]


@webhook_router.post("/forward-rules")
async def create_forward_rule(
    body: ForwardRuleCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    name = body.name.strip()
    match_path = body.match_path.strip()
    match_equals = body.match_equals.strip()
    forward_url = body.forward_url.strip()
    fallback_url = body.fallback_url.strip()

    if not name:
        raise HTTPException(status_code=400, detail="Rule name is required")
    if not match_path:
        raise HTTPException(status_code=400, detail="Match path is required")
    if not _re.match(r"^(\$?(\.\w+(\[\d+\])?)*)$", match_path) and not _re.match(r"^\w+(\[\d+\])?(\.\w+(\[\d+\])?)*$", match_path):
        raise HTTPException(status_code=400, detail="Invalid match path format. Examples: '$.event', 'events[0].type'")
    if not match_equals:
        raise HTTPException(status_code=400, detail="Match value is required")
    _validate_forward_rule_urls(forward_url, fallback_url)

    rule = WebhookForwardRule(
        user_id=user.id,
        name=name,
        match_path=match_path,
        match_equals=match_equals,
        forward_url=forward_url,
        fallback_url=fallback_url,
        auto_retry_enabled=body.auto_retry_enabled,
        is_active=body.is_active,
    )
    session.add(rule)
    await session.flush()
    return _serialize_forward_rule(rule)


@webhook_router.delete("/forward-rules/{rule_id}")
async def delete_forward_rule(
    rule_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await session.execute(
        delete(WebhookForwardRule).where(
            WebhookForwardRule.id == rule_id,
            WebhookForwardRule.user_id == user.id,
        )
    )
    await session.flush()
    return {"status": "deleted"}


async def _get_user_endpoint(user: User, session: AsyncSession) -> WebhookEndpoint:
    ep_result = await session.execute(
        select(WebhookEndpoint)
        .where(WebhookEndpoint.user_id == user.id)
        .order_by(WebhookEndpoint.created_at.asc())
        .limit(1)
    )
    ep = ep_result.scalar_one_or_none()
    if not ep:
        raise HTTPException(status_code=404, detail="No endpoint configured")
    return ep


async def _get_owned_request(request_id: int, endpoint_id: int, session: AsyncSession) -> WebhookRequest:
    req_result = await session.execute(
        select(WebhookRequest).where(
            WebhookRequest.id == request_id,
            WebhookRequest.endpoint_id == endpoint_id,
        )
    )
    req = req_result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    return req


async def _get_owned_request_for_user(request_id: int, user_id: int, session: AsyncSession) -> WebhookRequest:
    req_result = await session.execute(
        select(WebhookRequest).where(
            WebhookRequest.id == request_id,
            WebhookRequest.user_id == user_id,
        )
    )
    req = req_result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    return req


@webhook_router.get("/requests/{request_id}/diff")
async def diff_request(
    request_id: int,
    base_request_id: int = Query(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    request = await _get_owned_request_for_user(request_id, user.id, session)
    base_request = await _get_owned_request_for_user(base_request_id, user.id, session)

    return {
        "request_id": request.id,
        "base_request_id": base_request.id,
        "headers": _diff_values(
            json.loads(base_request.headers_json or "{}"),
            json.loads(request.headers_json or "{}"),
        ),
        "body": _diff_values(
            _parse_json_or_text(base_request.body or ""),
            _parse_json_or_text(request.body or ""),
        ),
    }


@webhook_router.post("/requests/{request_id}/validate-schema")
async def validate_request_schema(
    request_id: int,
    body: SchemaValidationPayload,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    request = await _get_owned_request_for_user(request_id, user.id, session)

    try:
        Draft202012Validator.check_schema(body.json_schema)
    except SchemaError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON Schema: {exc.message}")

    validator = Draft202012Validator(body.json_schema)
    payload = _parse_request_body_json(request)
    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.absolute_path))

    return {
        "request_id": request.id,
        "valid": not errors,
        "errors": [
            {
                "path": _schema_error_path(error),
                "message": error.message,
                "validator": error.validator,
            }
            for error in errors
        ],
    }


@webhook_router.get("/requests/{request_id}/export")
async def export_request(
    request_id: int,
    format: Literal["curl", "postman"] = Query(default="curl"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    request = await _get_owned_request_for_user(request_id, user.id, session)

    if format == "postman":
        collection = _build_postman_collection(request)
        return Response(
            content=json.dumps(collection, indent=2),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=webhook-request-{request.id}.postman_collection.json"
            },
        )

    return Response(
        content=_build_curl_export(request),
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename=webhook-request-{request.id}.curl.sh"},
    )


@webhook_router.get("/events/{request_id}")
async def get_event(
    request_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    request = await _get_owned_request_for_user(request_id, user.id, session)
    return _serialize_request(request)


@webhook_router.get("/events/{request_id}/diff")
async def diff_event(
    request_id: int,
    base_request_id: int = Query(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await diff_request(request_id, base_request_id, user, session)


REPLAY_LIMITS = {}  # user_id -> list of float timestamps

async def _replay_event_impl(
    request_id: int,
    body: ReplayPayload,
    user: User,
    session: AsyncSession,
):
    now_ts = datetime.now(timezone.utc).timestamp()
    history = REPLAY_LIMITS.setdefault(user.id, [])
    history = [t for t in history if now_ts - t < 60]
    REPLAY_LIMITS[user.id] = history
    if len(history) >= 10:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Max 10 replays per minute.")
    history.append(now_ts)

    request = await _get_owned_request_for_user(request_id, user.id, session)

    target_url = body.target_url.strip()
    if not target_url:
        if body.mode == "alternate":
            raise HTTPException(status_code=400, detail="Replay target URL is required for alternate replay")
        target_url = _request_export_url(request)
    _validate_public_url_field(target_url, "Replay target URL")

    headers = _exportable_headers(request.headers_json)
    if body.mode == "alternate":
        auth_headers = {"authorization", "x-api-key", "stripe-signature", "x-hub-signature-256", "x-shopify-hmac-sha256"}
        headers = {k: v for k, v in headers.items() if k.lower() not in auth_headers}
    if body.headers_override:
        headers.update({str(key): str(value) for key, value in body.headers_override.items()})
    replay_body = body.body_override if body.body_override is not None else request.body

    status_code: Optional[int] = None
    replay_status = "failed"
    forward_error = ""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=replay_body.encode("utf-8"),
            )
        status_code = response.status_code
        replay_status = "success" if 200 <= response.status_code < 300 else "failed"
        if replay_status == "failed":
            forward_error = f"Replay returned {response.status_code}"
    except httpx.RequestError as exc:
        forward_error = str(exc)

    replay_request = WebhookRequest(
        endpoint_id=request.endpoint_id,
        user_id=request.user_id,
        method=request.method,
        path=target_url,
        headers_json=json.dumps(headers),
        body=replay_body,
        query_params_json=getattr(request, "query_params_json", "{}"),
        ip_address="replay",
        last_retry_status=status_code,
        forward_error=forward_error,
        signature_valid=getattr(request, "signature_valid", None),
        signature_error=getattr(request, "signature_error", ""),
        signature_provider=getattr(request, "signature_provider", ""),
        replay_of_request_id=request.id,
        replay_target_url=target_url,
        replay_status=replay_status,
    )
    session.add(replay_request)
    await session.flush()

    return {
        "status": replay_status,
        "event": _serialize_request(replay_request),
        "target_url": target_url,
        "response_status": status_code,
        "error": forward_error,
    }


@webhook_router.post("/events/{request_id}/replay")
async def replay_event(
    request_id: int,
    body: ReplayPayload,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await _replay_event_impl(request_id, body, user, session)


@webhook_router.post("/requests/{request_id}/replay")
async def replay_request(
    request_id: int,
    body: ReplayPayload,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await _replay_event_impl(request_id, body, user, session)


@webhook_router.post("/search")
async def search_events(
    body: WebhookSearchPayload,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    limit = min(max(body.limit, 1), 100)
    result = await session.execute(
        select(WebhookRequest)
        .where(WebhookRequest.user_id == user.id)
        .order_by(WebhookRequest.received_at.desc())
        .limit(1000)
    )
    matches = [
        request
        for request in result.scalars().all()
        if _request_matches_search(request, body)
    ]
    return {
        "total": len(matches),
        "items": [_serialize_request(request) for request in matches[:limit]],
    }


@webhook_router.post("/requests/{request_id}/retry")
async def retry_request(
    request_id: int,
    body: RetryPayload,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Encola un job de reenvío en system_outbox.
    """
    req = await _get_owned_request_for_user(request_id, user.id, session)

    ws_result = await session.execute(select(WebhookSettings).where(WebhookSettings.user_id == user.id))
    ws = ws_result.scalar_one_or_none()
    if not ws or not ws.forward_url:
        raise HTTPException(status_code=400, detail="No forward_url configured in settings")
    if not is_public_http_url(ws.forward_url):
        raise HTTPException(status_code=400, detail="Forward URL must be a public http(s) URL")
        
    job = SystemOutbox(
        app_name="webhookmonitor",
        job_type="forward_webhook",
        payload={
            "request_id": req.id,
            "payload_override": body.payload_override,
            "forward_url": ws.forward_url,
            "fallback_url": ws.fallback_url,
            "max_attempts": ws.retry_max_attempts,
            "backoff_seconds": _settings_retry_backoff(ws),
            "timeout_seconds": ws.forward_timeout_seconds,
        },
        status="pending",
        max_attempts=ws.retry_max_attempts if body.schedule_auto_retry else 1
    )
    session.add(job)
    await session.commit()
    
    return {
        "status": "queued",
        "message": "Retry job queued successfully in system_outbox"
    }


# ---------------------------------------------------------------------------
# Cron jobs
# ---------------------------------------------------------------------------

async def check_webhook_silences():
    """
    Cron: detects silence on endpoints with expected_interval_minutes > 0.
    If the last webhook is older than 2x the expected interval, sends an alert email.
    """
    async with get_managed_session() as session:
        settings_res = await session.execute(
            select(WebhookSettings).where(WebhookSettings.expected_interval_minutes > 0)
        )
        all_settings = settings_res.scalars().all()

        for ws in all_settings:
            if not ws.alert_email:
                continue

            ep_res = await session.execute(
                select(WebhookEndpoint).where(
                    WebhookEndpoint.user_id == ws.user_id,
                    WebhookEndpoint.is_active == True,  # noqa: E712
                )
            )
            user_endpoints = ep_res.scalars().all()
            if not user_endpoints:
                continue

            now = datetime.now(timezone.utc)
            silence_threshold = timedelta(minutes=ws.expected_interval_minutes * 2)
            last_received_str = "Never"
            is_silent = True

            for ep in user_endpoints:
                last_res = await session.execute(
                    select(WebhookRequest)
                    .where(WebhookRequest.endpoint_id == ep.id)
                    .order_by(WebhookRequest.received_at.desc())
                    .limit(1)
                )
                last_req = last_res.scalar_one_or_none()

                if last_req is not None:
                    last_ts = last_req.received_at
                    if last_ts.tzinfo is None:
                        last_ts = last_ts.replace(tzinfo=timezone.utc)
                    age = now - last_ts
                    if age <= silence_threshold:
                        is_silent = False
                        break
                    last_received_str = last_ts.strftime("%Y-%m-%d %H:%M UTC")

            if is_silent:
                # Check if a silence alert was already sent in the last hour
                if ws.last_silence_alert_sent_at is not None:
                    last_alert_ts = ws.last_silence_alert_sent_at
                    if last_alert_ts.tzinfo is None:
                        last_alert_ts = last_alert_ts.replace(tzinfo=timezone.utc)
                    if (now - last_alert_ts) < timedelta(hours=1):
                        continue

                logger.warning(f"Silence detected for user {ws.user_id} — last webhook: {last_received_str}")
                try:
                    await run_in_threadpool(
                        send_email,
                        to=ws.alert_email,
                        subject="⚠️ Webhook Silence Detected",
                        html_body=f"""
                        <div style="font-family:sans-serif;padding:20px;border:2px solid #F59E0B;border-radius:12px;">
                          <h2 style="color:#F59E0B;">⚠️ Silence Alert</h2>
                          <p>No webhooks received in the last <strong>{ws.expected_interval_minutes * 2} minutes</strong>.</p>
                          <p><strong>Last webhook:</strong> {last_received_str}</p>
                          <p><strong>Expected interval:</strong> every {ws.expected_interval_minutes} minutes</p>
                          <p>Please verify your service is sending correctly.</p>
                        </div>
                        """
                    )
                    ws.last_silence_alert_sent_at = datetime.now(timezone.utc).replace(tzinfo=None)
                    session.add(ws)
                    await session.flush()
                except Exception as e:
                    logger.error(f"Failed to send silence alert: {e}")



async def cleanup_old_logs():
    """
    Cron: deletes webhook request logs outside each user's retention window.
    """
    async with get_managed_session() as session:
        endpoints_result = await session.execute(
            select(WebhookEndpoint.user_id).distinct()
        )
        deleted = 0
        for user_id in endpoints_result.scalars().all():
            _plan, limits = await get_webhookmonitor_limits_for_user_id(session, user_id)
            cutoff = _utc_now_naive() - timedelta(days=limits.retention_days)
            result = await session.execute(
                delete(WebhookRequest).where(
                    WebhookRequest.user_id == user_id,
                    WebhookRequest.received_at < cutoff,
                )
            )
            deleted += result.rowcount or 0
        await session.commit()
        logger.info("Cleanup cron: deleted %s webhook logs outside plan retention", deleted)
        return deleted


@cron_router.post("/cron/silence", tags=["cron"])
async def cron_silence_check(authorization: str | None = Header(default=None)):
    """cron-job.org endpoint — detects silent webhooks."""
    expected = os.getenv("CRON_SECRET")
    if not expected or authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    await check_webhook_silences()
    return {"status": "success", "task": "silence_check"}



@cron_router.post("/cron/cleanup", tags=["cron"])
async def cron_cleanup_logs(authorization: str | None = Header(default=None)):
    """cron-job.org endpoint — purges webhook logs older than 30 days."""
    expected = os.getenv("CRON_SECRET")
    if not expected or authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    deleted = await cleanup_old_logs()
    return {"status": "success", "task": "cleanup", "deleted_count": deleted}


# ---------------------------------------------------------------------------
# Export logs endpoint — Skill: backend-architect
# ---------------------------------------------------------------------------
@webhook_router.get("/logs/export")
async def export_logs(
    format: Literal["csv", "xlsx", "json"] = Query(default="csv"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Export all webhook request logs as CSV, XLSX, or JSON."""
    result = await session.execute(
        select(WebhookRequest)
        .where(WebhookRequest.user_id == user.id)
        .order_by(WebhookRequest.received_at.desc())
        .limit(1000)
    )
    requests = result.scalars().all()
    rows = [{
        "id": r.id,
        "event_id": getattr(r, "request_uuid", str(r.id)),
        "endpoint_id": r.endpoint_id,
        "method": r.method,
        "path": r.path,
        "headers_preview": json.dumps(mask_sensitive_mapping(_safe_json_dict(r.headers_json))),
        "body_preview": mask_sensitive_text(r.body[:200] if r.body else ""),
        "query_params": getattr(r, "query_params_json", "{}"),
        "ip_address": getattr(r, "ip_address", ""),
        "received_at": r.received_at.isoformat(),
        "retry_count": r.retry_count,
        "last_retry_status": r.last_retry_status,
        "forward_error": getattr(r, "forward_error", ""),
        "signature_valid": getattr(r, "signature_valid", None),
        "signature_error": getattr(r, "signature_error", ""),
        "signature_provider": getattr(r, "signature_provider", ""),
        "replay_of_request_id": getattr(r, "replay_of_request_id", None),
        "replay_status": getattr(r, "replay_status", ""),
        "auto_retry_enabled": r.auto_retry_enabled,
    } for r in requests]

    if format == "json":
        return StreamingResponse(
            io.BytesIO(json.dumps(rows, indent=2).encode()),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=webhookmonitor_export.json"}
        )
    df = pd.DataFrame(rows) if rows else pd.DataFrame()
    buf = io.BytesIO()
    if format == "xlsx":
        df.to_excel(buf, index=False, engine="openpyxl")
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = "webhookmonitor_export.xlsx"
    else:
        df.to_csv(buf, index=False)
        media_type = "text/csv"
        filename = "webhookmonitor_export.csv"
    buf.seek(0)
    return StreamingResponse(buf, media_type=media_type, headers={"Content-Disposition": f"attachment; filename={filename}"})


# ---------------------------------------------------------------------------
# Ingestion (public, no auth)
# ---------------------------------------------------------------------------

async def _notify_webhook_issue(settings: Optional[WebhookSettings], subject: str, message: str) -> None:
    if not settings:
        return
    if settings.alert_email:
        try:
            await run_in_threadpool(
                send_email,
                to=settings.alert_email,
                subject=subject,
                html_body=f"<p>{message}</p>",
            )
        except Exception as exc:
            logger.warning("Webhook email notification failed: %s", exc)

    async def post_json(url: str, payload: dict[str, Any]) -> None:
        if not url or not is_public_http_url(url):
            return
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(url, json=payload)
        except Exception as exc:
            logger.warning("Webhook notification failed for %s: %s", url, exc)

    await post_json(decrypt_val(settings.slack_webhook_url), {"text": f"{subject}: {message}"})
    await post_json(decrypt_val(settings.discord_webhook_url), {"content": f"{subject}: {message}"})


async def _persist_and_forward(
    request_id: Optional[int] = None,
    user_id: int = 0,
    body: str = "",
    headers: dict[str, Any] = None,
    path: str = "",
    signature_result: Optional[dict[str, Any]] = None,
    endpoint_id: Optional[int] = None,
    method: Optional[str] = None,
    query_params: Optional[dict[str, Any]] = None,
    ip_address: Optional[str] = None,
):
    try:
        async with get_managed_session() as session:
            signature_result = signature_result or {"valid": None, "error": "", "provider": "", "details": {}}
            headers = headers or {}

            # Fallback for compatibility (e.g. tests calling it directly with endpoint_id instead of request_id)
            if request_id is None:
                req = WebhookRequest(
                    endpoint_id=endpoint_id,
                    user_id=user_id,
                    method=method or "POST",
                    path=path,
                    headers_json=json.dumps(headers),
                    body=body,
                    query_params_json=json.dumps(query_params or {}),
                    ip_address=ip_address or "",
                )
                session.add(req)
                await session.flush()
            else:
                # Update the already-persisted WebhookRequest with signature info
                req_result = await session.execute(
                    select(WebhookRequest).where(WebhookRequest.id == request_id)
                )
                req = req_result.scalar_one_or_none()
                if not req:
                    logger.error("_persist_and_forward: request %s not found", request_id)
                    return
            req.signature_valid = signature_result.get("valid")
            req.signature_error = signature_result.get("error") or ""
            req.signature_provider = signature_result.get("provider") or ""
            session.add(req)
            await session.flush()

            rules_result = await session.execute(
                select(WebhookForwardRule).where(
                    WebhookForwardRule.user_id == user_id,
                    WebhookForwardRule.is_active == True,  # noqa: E712
                )
            )
            matched_rule = _select_forward_rule(list(rules_result.scalars().all()), body)

            settings_result = await session.execute(
                select(WebhookSettings).where(WebhookSettings.user_id == user_id)
            )
            user_settings = settings_result.scalar_one_or_none()
            retry_attempts = user_settings.retry_max_attempts if user_settings else 3
            retry_backoff = _settings_retry_backoff(user_settings)
            timeout_seconds = user_settings.forward_timeout_seconds if user_settings else 30

            if matched_rule:
                req.auto_retry_enabled = matched_rule.auto_retry_enabled
                job = SystemOutbox(
                    app_name="webhookmonitor",
                    job_type="forward_webhook",
                    payload={
                        "request_id": req.id,
                        "forward_rule_id": matched_rule.id,
                        "forward_url": matched_rule.forward_url,
                        "fallback_url": matched_rule.fallback_url,
                        "max_attempts": retry_attempts,
                        "backoff_seconds": retry_backoff,
                        "timeout_seconds": timeout_seconds,
                    },
                    status="pending",
                    max_attempts=retry_attempts if matched_rule.auto_retry_enabled else 1
                )
                session.add(job)
            elif user_settings and user_settings.forward_url:
                req.auto_retry_enabled = user_settings.auto_retry_enabled
                job = SystemOutbox(
                    app_name="webhookmonitor",
                    job_type="forward_webhook",
                    payload={
                        "request_id": req.id,
                        "forward_url": user_settings.forward_url,
                        "fallback_url": user_settings.fallback_url,
                        "max_attempts": retry_attempts,
                        "backoff_seconds": retry_backoff,
                        "timeout_seconds": timeout_seconds,
                    },
                    status="pending",
                    max_attempts=retry_attempts if user_settings.auto_retry_enabled else 1
                )
                session.add(job)

            await session.commit()

            if signature_result.get("valid") is False:
                await _notify_webhook_issue(
                    user_settings,
                    "Webhook signature validation failed",
                    f"Provider={signature_result.get('provider')}; error={signature_result.get('error')}; path={path}",
                )

            # Logic Bridge: check if this is a payment webhook and auto-pay invoices
            try:
                await detect_and_act_on_payment(user_id=user_id, headers=headers, body=body)
            except Exception as e:
                logger.debug(f"Logic bridge check skipped: {e}")
    except Exception:
        logger.exception("_persist_and_forward failed for request_id=%s", request_id)

async def process_webhook_forward(payload: dict):
    request_id = payload.get("request_id")
    payload_override = payload.get("payload_override")
    forward_url = (payload.get("forward_url") or "").strip()
    fallback_url = (payload.get("fallback_url") or "").strip()
    max_attempts = int(payload.get("max_attempts") or 1)
    timeout_seconds = float(payload.get("timeout_seconds") or 30)
    
    async with get_managed_session() as session:
        req_result = await session.execute(select(WebhookRequest).where(WebhookRequest.id == request_id))
        req = req_result.scalar_one_or_none()
        if not req:
            return {"status": "skipped", "reason": "request not found"}

        ws = None
        if not forward_url:
            ws_result = await session.execute(select(WebhookSettings).where(WebhookSettings.user_id == req.user_id))
            ws = ws_result.scalar_one_or_none()
            forward_url = ws.forward_url if ws else ""
            fallback_url = fallback_url or (ws.fallback_url if ws else "")
            max_attempts = ws.retry_max_attempts if ws else max_attempts
            timeout_seconds = float(ws.forward_timeout_seconds if ws else timeout_seconds)
        elif req.user_id is not None:
            ws_result = await session.execute(select(WebhookSettings).where(WebhookSettings.user_id == req.user_id))
            ws = ws_result.scalar_one_or_none()

        if not forward_url:
            return {"status": "skipped", "reason": "no forward url"}
        if not is_public_http_url(forward_url):
            return {"status": "skipped", "reason": "unsafe forward url"}
        if fallback_url and not is_public_http_url(fallback_url):
            return {"status": "skipped", "reason": "unsafe fallback url"}
            
        headers = _safe_json_dict(req.headers_json)
        safe_headers = {
            k: v for k, v in headers.items()
            if k.lower() not in ("host", "content-length", "transfer-encoding", "connection")
        }

        body_to_send = payload_override if payload_override is not None else req.body

        async def deliver(url: str):
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                return await client.request(
                    method=req.method,
                    url=url,
                    headers=safe_headers,
                    content=body_to_send.encode("utf-8"),
                )

        async def deliver_fallback_if_final(reason: str):
            if not fallback_url or req.retry_count < max_attempts:
                return None
            response = await deliver(fallback_url)
            req.last_retry_status = response.status_code
            if 200 <= response.status_code < 300:
                req.auto_retry_enabled = False
                req.next_retry_at = None
                req.forward_error = ""
                session.add(req)
                await session.commit()
                return {
                    "status": "success",
                    "forward_url": fallback_url,
                    "response_status": response.status_code,
                    "fallback": True,
                }
            req.forward_error = f"{reason}; fallback returned {response.status_code}"
            return None

        try:
            response = await deliver(forward_url)
            req.last_retry_status = response.status_code
            if 200 <= response.status_code < 300:
                req.auto_retry_enabled = False
                req.next_retry_at = None
                req.forward_error = ""
                session.add(req)
                await session.commit()
                return {"status": "success", "forward_url": forward_url, "response_status": response.status_code}

            req.retry_count += 1
            req.forward_error = f"Forward returned {response.status_code}"
            backoff = _settings_retry_backoff(ws)
            if req.retry_count <= len(backoff):
                delay = backoff[min(req.retry_count - 1, len(backoff) - 1)]
                req.next_retry_at = _utc_now_naive() + timedelta(seconds=delay)
            fallback_result = await deliver_fallback_if_final(req.forward_error)
            if fallback_result:
                return fallback_result
            session.add(req)
            await session.commit()
            if req.retry_count >= max_attempts:
                await _notify_webhook_issue(ws, "Webhook forward failed", req.forward_error)
            raise Exception(req.forward_error)

        except httpx.RequestError as e:
            req.retry_count += 1
            req.forward_error = str(e)
            backoff = _settings_retry_backoff(ws)
            if req.retry_count <= len(backoff):
                delay = backoff[min(req.retry_count - 1, len(backoff) - 1)]
                req.next_retry_at = _utc_now_naive() + timedelta(seconds=delay)
            try:
                fallback_result = await deliver_fallback_if_final(req.forward_error)
            except httpx.RequestError as fallback_error:
                req.forward_error = f"{req.forward_error}; fallback failed: {fallback_error}"
                fallback_result = None
            if fallback_result:
                return fallback_result
            session.add(req)
            await session.commit()
            if req.retry_count >= max_attempts:
                await _notify_webhook_issue(ws, "Webhook forward failed", req.forward_error)
            raise e

register_job_handler("webhookmonitor", "forward_webhook", process_webhook_forward)


@ingestion_router.api_route("/in/{slug}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@ingestion_router.api_route("/hook/{slug}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def ingest_webhook(
    slug: str,
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(WebhookEndpoint).where(WebhookEndpoint.slug == slug))
    ep = result.scalar_one_or_none()
    if not ep:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    if getattr(ep, "is_active", True) is False:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    if request.method.upper() not in _allowed_methods(ep):
        raise HTTPException(status_code=405, detail="HTTP method is not enabled for this endpoint")

    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_WEBHOOK_BODY_BYTES:
                raise HTTPException(status_code=413, detail="Webhook body too large")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid content-length header")

    plan, limits = await get_webhookmonitor_limits_for_user_id(session, ep.user_id)
    since = _utc_now_naive() - timedelta(days=1)
    count_result = await session.execute(
        select(func.count(WebhookRequest.id)).where(
            WebhookRequest.user_id == ep.user_id,
            WebhookRequest.received_at >= since,
        )
    )
    recent_count = count_result.scalar_one()
    reject_webhook_rate_if_needed(plan, limits, recent_count)

    raw_body = await request.body()
    if len(raw_body) > MAX_WEBHOOK_BODY_BYTES:
        raise HTTPException(status_code=413, detail="Webhook body too large")

    body = raw_body.decode("utf-8", errors="replace")
    headers = dict(request.headers)
    settings_result = await session.execute(select(WebhookSettings).where(WebhookSettings.user_id == ep.user_id))
    settings = settings_result.scalar_one_or_none()
    signature_result = _signature_for_settings(settings, headers, raw_body)
    query_params = dict(request.query_params.multi_items())
    ip_address = request.client.host if request.client else ""

    # Persist a minimal WebhookRequest synchronously before responding
    req = WebhookRequest(
        endpoint_id=ep.id,
        user_id=ep.user_id,
        method=request.method,
        path=str(request.url.path),
        headers_json=json.dumps(headers),
        body=body,
        query_params_json=json.dumps(query_params or {}),
        ip_address=ip_address,
    )
    session.add(req)
    await session.flush()
    await session.commit()

    background_tasks.add_task(
        _persist_and_forward,
        request_id=req.id,
        user_id=ep.user_id,
        body=body,
        headers=headers,
        path=str(request.url.path),
        signature_result=signature_result,
        query_params=query_params,
        ip_address=ip_address,
    )
    return {
        "status": "received",
        "signature_valid": signature_result.get("valid"),
        "signature_error": signature_result.get("error", ""),
    }


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = create_app(
    title="Webhook Monitor",
    description="Real-time monitoring, alerting, and exponential backoff retries for your webhooks",
    domain_routers=[ingestion_router, webhook_router, settings_router, cron_router]
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8004, reload=True)
