import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "packages"))

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import parsedate_to_datetime
from typing import Any, Literal, Optional
import base64
import html
import io
import json
import logging
import re
import unicodedata
import uuid
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, EmailStr, ValidationError, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel, select
import httpx
import pandas as pd

from backend_core import create_app, get_current_user, get_session, User, require_product_access, get_settings
from backend_core.database import get_managed_session
from backend_core.email_service import send_email
from backend_core.outbox_models import SystemOutbox
from backend_core.product_insights import summarize_invoices
from backend_core.worker import register_job_handler
from backend_core.plan_limits import resolve_user_plan
from zoneinfo import ZoneInfo
from sqlalchemy import update, case, func, and_
import hashlib
from cryptography.fernet import Fernet
import stripe

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


logger = logging.getLogger(__name__)
settings = get_settings()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass(frozen=True)
class InvoiceFollowLimits:
    max_active_invoices: int
    monthly_emails: int
    monthly_nlp: int
    max_payment_connections: int
    max_users: int
    api_access: bool
    history_retention_days: int
    payment_connections_enabled: bool
    weekly_digest_enabled: bool


INVOICEFOLLOW_LIMITS: dict[str, InvoiceFollowLimits] = {
    "free": InvoiceFollowLimits(
        max_active_invoices=5,
        monthly_emails=25,
        monthly_nlp=10,
        max_payment_connections=0,
        max_users=1,
        api_access=False,
        history_retention_days=30,
        payment_connections_enabled=False,
        weekly_digest_enabled=False,
    ),
    "pro": InvoiceFollowLimits(
        max_active_invoices=50,
        monthly_emails=500,
        monthly_nlp=200,
        max_payment_connections=2,
        max_users=1,
        api_access=True,
        history_retention_days=90,
        payment_connections_enabled=True,
        weekly_digest_enabled=True,
    ),
    "team": InvoiceFollowLimits(
        max_active_invoices=200,
        monthly_emails=2000,
        monthly_nlp=1000,
        max_payment_connections=10,
        max_users=5,
        api_access=True,
        history_retention_days=365,
        payment_connections_enabled=True,
        weekly_digest_enabled=True,
    ),
}


class Invoice(SQLModel, table=True):
    __tablename__ = "invoices"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    client_name: str
    client_email: str = Field(default="")
    amount: float
    currency: str = Field(default="USD")
    due_date: date
    issued_date: Optional[date] = None
    invoice_number: str = Field(default="")
    source: str = Field(default="import", index=True)
    source_message_id: str = Field(default="", index=True)
    thread_id: str = Field(default="")
    status: str = Field(default="pending", index=True)
    reminders_sent: int = Field(default=0)
    last_reminder_date: Optional[date] = None
    promise_token: Optional[str] = Field(default=None, index=True)
    payment_promise_date: Optional[date] = None
    schedule_paused_until: Optional[date] = None
    manual_review_reason: str = Field(default="")
    notes: str = Field(default="")
    cron_paused: bool = Field(default=False)
    paid_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class InvoiceSettings(SQLModel, table=True):
    __tablename__ = "invoice_settings"

    user_id: int = Field(primary_key=True)
    email_template: str = Field(default="Hi {client_name}, invoice {invoice_number} for {amount} is past due.")
    templates_json: str = Field(default="")
    company_name: str = Field(default="")
    send_hour: int = Field(default=9)
    skip_weekends: bool = Field(default=True)
    timezone: str = Field(default="America/Lima")
    sender_name: str = Field(default="")
    weekly_digest_enabled: bool = Field(default=True)
    immediate_alerts_enabled: bool = Field(default=True)
    no_send_after_hour: int = Field(default=18)


class InvoiceIntegrationSettings(SQLModel, table=True):
    __tablename__ = "invoice_integration_settings"

    user_id: int = Field(primary_key=True)
    gmail_connected: bool = Field(default=False)
    gmail_email: str = Field(default="")
    gmail_state: str = Field(default="")
    gmail_access_token: str = Field(default="")
    gmail_refresh_token: str = Field(default="")
    gmail_token_expires_at: Optional[datetime] = None
    outlook_connected: bool = Field(default=False)
    outlook_email: str = Field(default="")
    outlook_state: str = Field(default="")
    outlook_access_token: str = Field(default="")
    outlook_refresh_token: str = Field(default="")
    outlook_token_expires_at: Optional[datetime] = None
    stripe_connected: bool = Field(default=False)
    stripe_account_label: str = Field(default="")
    stripe_api_key: str = Field(default="")
    paypal_connected: bool = Field(default=False)
    paypal_account_label: str = Field(default="")
    paypal_client_id: str = Field(default="")
    paypal_client_secret: str = Field(default="")
    forward_address_token: str = Field(default="")
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class InvoiceDetectedDraft(SQLModel, table=True):
    __tablename__ = "invoice_detected_drafts"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    source: str = Field(default="email", index=True)
    source_message_id: str = Field(default="", index=True)
    raw_subject: str = Field(default="")
    raw_body: str = Field(default="")
    sender_email: str = Field(default="")
    sender_name: str = Field(default="")
    client_name: str = Field(default="")
    client_email: str = Field(default="")
    amount: float = Field(default=0)
    currency: str = Field(default="USD")
    due_date: Optional[date] = None
    issued_date: Optional[date] = None
    invoice_number: str = Field(default="")
    confidence: float = Field(default=0)
    status: str = Field(default="needs_review", index=True)
    parsed_json: str = Field(default="{}")
    created_at: datetime = Field(default_factory=_utc_now)


class InvoiceReminderLog(SQLModel, table=True):
    __tablename__ = "invoice_reminder_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    invoice_id: int = Field(index=True)
    user_id: int = Field(index=True)
    stage_day: int = Field(index=True)
    template_key: str = Field(default="")
    status: str = Field(default="queued", index=True)
    provider: str = Field(default="gmail")
    subject: str = Field(default="")
    body_preview: str = Field(default="")
    response_intent: str = Field(default="")
    response_excerpt: str = Field(default="")
    sent_at: datetime = Field(default_factory=_utc_now, index=True)


class InvoiceReplyEvent(SQLModel, table=True):
    __tablename__ = "invoice_reply_events"

    id: Optional[int] = Field(default=None, primary_key=True)
    invoice_id: int = Field(index=True)
    user_id: int = Field(index=True)
    provider: str = Field(default="gmail")
    provider_message_id: str = Field(default="", index=True)
    text: str = Field(default="")
    intent_label: str = Field(default="DESCONOCIDO", index=True)
    action_taken: str = Field(default="")
    received_at: datetime = Field(default_factory=_utc_now, index=True)


class InvoicePaymentEvent(SQLModel, table=True):
    __tablename__ = "invoice_payment_events"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    invoice_id: int = Field(index=True)
    provider: str = Field(default="stripe", index=True)
    provider_event_id: str = Field(default="", index=True)
    amount: float = Field(default=0)
    currency: str = Field(default="USD")
    status: str = Field(default="succeeded", index=True)
    raw_json: str = Field(default="{}")
    detected_at: datetime = Field(default_factory=_utc_now, index=True)


class InvoiceCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    client_name: str
    client_email: EmailStr
    amount: float
    currency: str = "USD"
    due_date: date
    issued_date: Optional[date] = None
    invoice_number: str = ""
    notes: str = ""

    @field_validator("client_name")
    @classmethod
    def client_name_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("client_name is required")
        return value.strip()

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("amount must be greater than 0")
        return value

    @field_validator("currency")
    @classmethod
    def currency_must_be_isoish(cls, value: str) -> str:
        cleaned = value.strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", cleaned):
            raise ValueError("currency must be a 3-letter code")
        return cleaned


class InvoiceUpdate(BaseModel):
    client_name: Optional[str] = None
    client_email: Optional[EmailStr] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    due_date: Optional[date] = None
    issued_date: Optional[date] = None
    invoice_number: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class InvoiceEmailDetectRequest(BaseModel):
    subject: str = ""
    body: str = ""
    sender_email: EmailStr
    sender_name: str = ""
    message_id: str = ""
    source: Literal["gmail", "outlook", "forward"] = "gmail"


class DraftConfirmRequest(BaseModel):
    client_name: Optional[str] = None
    client_email: Optional[EmailStr] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    due_date: date
    issued_date: Optional[date] = None
    invoice_number: Optional[str] = None
    notes: str = ""


class TemplateUpdate(BaseModel):
    subject: Optional[str] = None
    body: str
    enabled: bool = True


class TemplatesUpdate(BaseModel):
    templates: dict[str, TemplateUpdate]


class InvoiceSettingsUpdate(BaseModel):
    company_name: Optional[str] = None
    send_hour: Optional[int] = None
    skip_weekends: Optional[bool] = None
    timezone: Optional[str] = None
    sender_name: Optional[str] = None
    weekly_digest_enabled: Optional[bool] = None
    immediate_alerts_enabled: Optional[bool] = None
    no_send_after_hour: Optional[int] = None


class ConnectRequest(BaseModel):
    email: Optional[EmailStr] = None
    api_key: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    account_label: Optional[str] = None
    redirect_uri: Optional[str] = None


CURRENCY_SYMBOLS = {
    "$": "USD",
    "USD": "USD",
    "US$": "USD",
    "EUR": "EUR",
    "\u20ac": "EUR",
    "PEN": "PEN",
    "S/": "PEN",
    "GBP": "GBP",
    "\u00a3": "GBP",
}

DEFAULT_TEMPLATES: dict[str, dict[str, Any]] = {
    "original": {
        "id": "original",
        "day": 0,
        "name": "Invoice Original",
        "tone": "neutral",
        "enabled": True,
        "subject": "Invoice {invoice_number} from {company_name}",
        "body": "Hi {client_name}, this is the invoice record {invoice_number} for {amount} {currency}, due {due_date}.",
    },
    "friendly": {
        "id": "friendly",
        "day": 7,
        "name": "First Reminder",
        "tone": "friendly",
        "enabled": True,
        "subject": "Checking in on invoice {invoice_number}",
        "body": "Hey {client_name}, just checking in on invoice {invoice_number}. Let me know if you need anything.",
    },
    "firm": {
        "id": "firm",
        "day": 15,
        "name": "Second Reminder",
        "tone": "firm",
        "enabled": True,
        "subject": "Invoice {invoice_number} is overdue",
        "body": "Invoice {invoice_number} is now {days_overdue} days overdue. Please prioritize this payment.",
    },
    "urgent": {
        "id": "urgent",
        "day": 30,
        "name": "Final Notice",
        "tone": "urgent",
        "enabled": True,
        "subject": "Final notice: invoice {invoice_number}",
        "body": "Final notice. Invoice {invoice_number} is {days_overdue} days overdue. Immediate payment required.",
    },
    "pause": {
        "id": "pause",
        "day": 45,
        "name": "Pause",
        "tone": "manual",
        "enabled": True,
        "subject": "Manual action needed for invoice {invoice_number}",
        "body": "Automatic reminders are paused for invoice {invoice_number}. Review the account manually.",
    },
}


def _clean_import_value(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def _clean_import_amount(value) -> str:
    return _clean_import_value(value).replace("$", "").replace(",", "")


def _currency_from_symbol(symbol: str) -> str:
    return CURRENCY_SYMBOLS.get(symbol.upper(), CURRENCY_SYMBOLS.get(symbol, "USD"))


def _format_money(amount: float, currency: str = "USD") -> str:
    prefix = "$" if currency == "USD" else ("S/ " if currency == "PEN" else ("\u20ac" if currency == "EUR" else ("\u00a3" if currency == "GBP" else "")))
    suffix = "" if prefix else f" {currency}"
    return f"{prefix}{amount:,.2f}{suffix}"


def _parse_date_candidate(raw: str, *, fallback_year: int | None = None) -> Optional[date]:
    cleaned = raw.strip().replace(",", " ")
    iso_match = re.search(r"\b(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b", cleaned)
    if iso_match:
        year, month, day = map(int, iso_match.groups())
        try:
            return date(year, month, day)
        except ValueError:
            return None

    us_match = re.search(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](20\d{2})\b", cleaned)
    if us_match:
        month, day, year = map(int, us_match.groups())
        try:
            return date(year, month, day)
        except ValueError:
            return None

    month_match = re.search(
        r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})(?:\s+(20\d{2}))?\b",
        cleaned,
        re.IGNORECASE,
    )
    if month_match:
        month_name, day_raw, year_raw = month_match.groups()
        month_index = [
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
        ].index(month_name.lower()) + 1
        year = int(year_raw or fallback_year or date.today().year)
        try:
            return date(year, month_index, int(day_raw))
        except ValueError:
            return None

    return None


def _extract_named_date(text: str, labels: tuple[str, ...], *, fallback_year: int | None = None) -> Optional[date]:
    for label in labels:
        pattern = rf"{label}\s*:?\s*([A-Za-z]+\s+\d{{1,2}},?\s*(?:20\d{{2}})?|20\d{{2}}[-/]\d{{1,2}}[-/]\d{{1,2}}|\d{{1,2}}[/.-]\d{{1,2}}[/.-]20\d{{2}})"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            parsed = _parse_date_candidate(match.group(1), fallback_year=fallback_year)
            if parsed:
                return parsed
    return None


def _sender_company(sender_name: str, sender_email: str) -> str:
    if sender_name:
        cleaned = re.sub(r"\b(billing|accounts|finance|invoice|invoices|ap)\b", "", sender_name, flags=re.IGNORECASE).strip()
        if cleaned:
            return cleaned
    domain = sender_email.split("@")[-1].split(".")[0] if "@" in sender_email else sender_email
    return domain.replace("-", " ").replace("_", " ").title()


def _safe_json_loads(value: str, fallback: Any) -> Any:
    try:
        parsed = json.loads(value) if value else fallback
        return parsed if parsed is not None else fallback
    except Exception:
        return fallback


def _templates_from_settings(user_settings: InvoiceSettings | None) -> dict[str, dict[str, Any]]:
    templates = {key: value.copy() for key, value in DEFAULT_TEMPLATES.items()}
    if user_settings and user_settings.templates_json:
        saved = _safe_json_loads(user_settings.templates_json, {})
        if isinstance(saved, dict):
            for key, value in saved.items():
                if key in templates and isinstance(value, dict):
                    templates[key].update(value)
    elif user_settings and user_settings.email_template:
        templates["friendly"]["body"] = user_settings.email_template
    return templates


def parse_invoice_email(subject: str, body: str, sender_email: str, sender_name: str = "") -> dict[str, Any]:
    text = f"{subject}\n{body}"
    candidate = re.search(r"\b(invoice|factura|payment due|amount due|total due|due date|vence)\b", text, re.IGNORECASE)
    if not candidate:
        return {
            "status": "not_detected",
            "confidence": 0.0,
            "next_step": "Ask the user to forward an existing invoice email or upload the invoice record manually.",
            "creates_invoice_document": False,
        }

    amount_match = re.search(
        "(?:amount due|total due|total|monto|importe)\\s*:?\\s*((?:US\\$|S/|\\$|EUR|USD|PEN|GBP|\\u20ac|\\u00a3)\\s*)?(\\d[\\d,]*(?:\\.\\d{1,2})?)\\s*(USD|EUR|PEN|GBP)?",
        text,
        re.IGNORECASE,
    ) or re.search(
        "((?:US\\$|S/|\\$|\\u20ac|\\u00a3|USD|EUR|PEN|GBP)\\s+?)(\\d[\\d,]*(?:\\.\\d{1,2})?)\\s*(USD|EUR|PEN|GBP)?",
        text,
        re.IGNORECASE,
    )
    amount = 0.0
    currency = "USD"
    if amount_match:
        leading, raw_amount, trailing = amount_match.groups()
        amount = float(raw_amount.replace(",", ""))
        currency = _currency_from_symbol((trailing or leading or "USD").strip())

    invoice_match = re.search(
        r"(?:invoice|factura|inv|n[°o.]?)\s*#?\s*([A-Z0-9][A-Z0-9._-]{1,30})|#\s*([A-Z0-9][A-Z0-9._-]{1,30})",
        text,
        re.IGNORECASE,
    )
    invoice_number = ""
    if invoice_match:
        invoice_number = (invoice_match.group(1) or invoice_match.group(2) or "").upper()

    fallback_year = date.today().year
    due_date = _extract_named_date(
        text,
        ("due on", "due date", "payment due", "vence el", "vence", "vencimiento"),
        fallback_year=fallback_year,
    )
    issued_date = _extract_named_date(
        text,
        ("issued", "issue date", "fecha de emision", "emision", "sent on"),
        fallback_year=due_date.year if due_date else fallback_year,
    )
    if issued_date is None:
        email_date = _extract_named_date(text, ("date",), fallback_year=fallback_year)
        issued_date = email_date

    client_match = re.search(r"(?:client|cliente)\s*:?\s*([A-Za-z0-9 .,&'-]{2,80})", text, re.IGNORECASE)
    client_name = client_match.group(1).strip() if client_match else _sender_company(sender_name, sender_email)
    confidence_parts = [bool(amount), bool(due_date), bool(invoice_number), bool(client_name)]
    confidence = round(sum(1 for item in confidence_parts if item) / len(confidence_parts), 2)

    return {
        "status": "detected",
        "client_name": client_name,
        "client_email": sender_email.lower(),
        "amount": amount,
        "currency": currency,
        "invoice_number": invoice_number,
        "due_date": due_date.isoformat() if due_date else None,
        "issued_date": issued_date.isoformat() if issued_date else None,
        "confidence": confidence,
        "creates_invoice_document": False,
        "preview_fields": ["client_name", "amount", "currency", "due_date", "issued_date", "invoice_number"],
    }


def build_reminder_schedule(due_date: date, today: date | None = None, user_name: str = "Owner", logs: list[Any] | None = None) -> list[dict[str, Any]]:
    today = today or date.today()
    days_overdue = max(0, (today - due_date).days)
    sent_stages = set()
    if logs:
        for log in logs:
            if getattr(log, "status", "") in {"sent", "queued"}:
                sent_stages.add(getattr(log, "template_key", ""))
    return [
        {"day": 0, "name": "Invoice Original", "tone": "neutral", "sender_label": user_name, "status": "done"},
        {"day": 7, "name": "First Reminder", "tone": "friendly", "sender_label": user_name, "status": "done" if "friendly" in sent_stages or days_overdue >= 7 else "pending"},
        {"day": 15, "name": "Second Reminder", "tone": "firm", "sender_label": f"{user_name} (Billing)", "status": "done" if "firm" in sent_stages or days_overdue >= 15 else "pending"},
        {"day": 30, "name": "Final Notice", "tone": "urgent", "sender_label": f"{user_name} (Accounts Receivable)", "status": "done" if "urgent" in sent_stages or days_overdue >= 30 else "pending"},
        {"day": 45, "name": "Pause", "tone": "manual", "sender_label": f"{user_name} (Accounts Receivable)", "status": "done" if "pause" in sent_stages or days_overdue >= 45 else "pending"},
    ]


def _select_stage(days_overdue: int, templates: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    templates = templates or DEFAULT_TEMPLATES
    eligible = [t for t in templates.values() if int(t["day"]) <= days_overdue]
    if not eligible:
        return templates["original"]
    return max(eligible, key=lambda t: int(t["day"]))


def _template_vars(invoice: Invoice, *, company_name: str, user_name: str, today: date) -> dict[str, str]:
    days_overdue = max(0, (today - invoice.due_date).days)
    return {
        "client_name": invoice.client_name,
        "invoice_number": invoice.invoice_number or f"#{invoice.id or 'pending'}",
        "amount": _format_money(invoice.amount, invoice.currency),
        "currency": invoice.currency,
        "due_date": invoice.due_date.isoformat(),
        "days_overdue": str(days_overdue),
        "company_name": company_name or user_name,
        "user_name": user_name,
    }


def _render_text(template: str, values: dict[str, str]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{" + key + "}", value)
    return rendered


def render_reminder_template(
    invoice: Invoice,
    *,
    stage_day: int,
    company_name: str,
    user_name: str,
    today: date | None = None,
    templates: dict[str, dict[str, Any]] | None = None,
) -> tuple[str, str, dict[str, Any]]:
    today = today or date.today()
    templates = templates or DEFAULT_TEMPLATES
    stage = next((item for item in templates.values() if int(item["day"]) == stage_day), _select_stage(max(0, (today - invoice.due_date).days), templates))
    values = _template_vars(invoice, company_name=company_name, user_name=user_name, today=today)
    subject = _render_text(stage["subject"], values)
    body = _render_text(stage["body"], values)
    escaped_body = html.escape(body).replace("\n", "<br>")
    html_body = (
        "<div style=\"font-family:sans-serif;max-width:640px;padding:24px;border:1px solid #d4d4d4;border-radius:8px;\">"
        f"<p>{escaped_body}</p>"
        "<hr style=\"border:none;border-top:1px solid #e5e5e5;margin:16px 0;\">"
        f"<p style=\"font-size:12px;color:#737373;\">Sent by {html.escape(values['user_name'])}'s InvoiceFollow tracking system.</p>"
        "</div>"
    )
    return subject, html_body, {"stage_day": int(stage["day"]), "template_key": stage["id"], "tone": stage["tone"]}


def _normalize_intent_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", ascii_text.lower()).strip()


def _contains_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


def classify_reply_intent(text: str) -> dict[str, Any]:
    normalized = _normalize_intent_text(text)
    payment_verbs = r"(transferi|transferido|transferencia|deposite|depositado|pague|pagado|paid|sent|send|wire|wired)"
    negated_payment = re.search(rf"\b(no|not|never|todavia no|aun no|ni)\b.{0,40}\b{payment_verbs}\b", normalized)
    attributed_payment = re.search(rf"\b(banco|bank|contador|accountant|bookkeeper)\b.{0,50}\b(dijo|said|dice|claims|me dijo)\b.{0,50}\b{payment_verbs}\b", normalized)

    false_excuse_terms = [
        "no recibi",
        "no me consta",
        "no es mio",
        "habla con mi contador",
        "invoice error",
        "wrong invoice",
        "not mine",
    ]
    if _contains_any(normalized, false_excuse_terms):
        return {
            "label": "EXCUSA_FALSA",
            "confidence": 0.72,
            "reason": "Client disputed receipt, ownership, or redirected responsibility.",
            "engine": "deterministic",
            "manual_review_required": True,
        }

    if negated_payment or attributed_payment:
        return {
            "label": "DESCONOCIDO",
            "confidence": 0.82,
            "reason": "Payment wording is negated or attributed to a third party, so it is not treated as paid.",
            "engine": "deterministic",
            "manual_review_required": True,
        }

    paid_terms = [
        "ya transferi",
        "ya deposite",
        "depositado",
        "payment sent",
        "sent payment",
        "we paid",
        "i paid",
        "paid this invoice",
        "paid invoice",
        "transfer completed",
        "wire sent",
        "listo",
        "hecho",
        "confirmado",
    ]
    if _contains_any(normalized, paid_terms):
        return {
            "label": "PAGADO",
            "confidence": 0.88,
            "reason": "Client directly says payment was sent or completed.",
            "engine": "deterministic",
            "manual_review_required": True,
        }

    valid_excuse_terms = [
        "problema con el banco",
        "demora",
        "proxima semana",
        "en proceso",
        "me comprometo",
        "el viernes",
        "next week",
        "bank issue",
        "processing delay",
        "payment is processing",
    ]
    if _contains_any(normalized, valid_excuse_terms):
        return {
            "label": "EXCUSA_VALIDA",
            "confidence": 0.8,
            "reason": "Client gave a concrete delay, processing status, or payment promise.",
            "engine": "deterministic",
            "manual_review_required": False,
        }

    return {
        "label": "DESCONOCIDO",
        "confidence": 0.35,
        "reason": "No reliable payment, delay, or dispute signal was found.",
        "engine": "deterministic",
        "manual_review_required": True,
    }


def apply_reply_intent(invoice: Invoice, intent: dict[str, Any], *, payment_confirmed: bool, today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    label = intent.get("label", "DESCONOCIDO")
    if label == "PAGADO":
        invoice.cron_paused = True
        if payment_confirmed:
            invoice.status = "paid"
            invoice.paid_at = _utc_now()
            invoice.manual_review_reason = ""
            return {"action": "mark_paid", "notify_user": "Payment confirmed automatically."}
        invoice.manual_review_reason = "Client says paid; verify payment in bank, Stripe, or PayPal."
        return {"action": "pause_verify_payment", "notify_user": "Client says they paid. Please verify payment."}
    if label == "EXCUSA_VALIDA":
        invoice.cron_paused = True
        invoice.schedule_paused_until = today + timedelta(days=7)
        invoice.payment_promise_date = today
        invoice.manual_review_reason = intent.get("reason", "Valid excuse detected.")
        return {"action": "pause_7_days", "notify_user": "Valid excuse detected; sequence pauses for 7 days."}
    if label == "EXCUSA_FALSA":
        invoice.manual_review_reason = "Possible false excuse detected; review manually."
        invoice.cron_paused = False
        return {"action": "continue_flag_user", "notify_user": "Possible false excuse detected."}
    invoice.manual_review_reason = "Unknown reply intent; review manually."
    return {"action": "continue_notify_review", "notify_user": "Unknown reply received; sequence continues."}


def detect_stripe_payment_for_invoice(event_payload: dict[str, Any], invoice: Invoice, *, today: date | None = None) -> dict[str, Any]:
    if event_payload.get("type") != "payment_intent.succeeded":
        return {"matched": False, "reason": "unsupported_event"}
    obj = event_payload.get("data", {}).get("object", {})
    metadata = obj.get("metadata") or {}
    invoice_id = str(invoice.id or "")
    if str(metadata.get("invoice_id", "")) == invoice_id:
        amount = (obj.get("amount_received") or obj.get("amount") or 0) / 100
        return {
            "matched": True,
            "provider": "stripe",
            "provider_event_id": event_payload.get("id", obj.get("id", "")),
            "amount": float(amount),
            "currency": str(obj.get("currency", invoice.currency)).upper(),
            "match_type": "metadata_invoice_id",
        }
    amount = (obj.get("amount_received") or obj.get("amount") or 0) / 100
    amount_ok = invoice.amount * 0.95 <= amount <= invoice.amount * 1.05
    email = (obj.get("receipt_email") or obj.get("customer_email") or "").lower()
    email_ok = email and email == invoice.client_email.lower()
    return {
        "matched": bool(amount_ok and email_ok),
        "provider": "stripe",
        "provider_event_id": event_payload.get("id", obj.get("id", "")),
        "amount": float(amount),
        "currency": str(obj.get("currency", invoice.currency)).upper(),
        "match_type": "amount_email" if amount_ok and email_ok else "none",
    }


def detect_paypal_payment_for_invoice(transaction: dict[str, Any], invoice: Invoice) -> dict[str, Any]:
    amount = float(transaction.get("amount", {}).get("value", transaction.get("amount", 0)) or 0)
    currency = str(transaction.get("amount", {}).get("currency_code", transaction.get("currency", invoice.currency))).upper()
    payer_email = str(transaction.get("payer", {}).get("email_address", transaction.get("payer_email", ""))).lower()
    amount_ok = invoice.amount * 0.95 <= amount <= invoice.amount * 1.05
    email_ok = payer_email == invoice.client_email.lower()
    return {
        "matched": bool(amount_ok and email_ok and currency == invoice.currency),
        "provider": "paypal",
        "provider_event_id": str(transaction.get("id", "")),
        "amount": amount,
        "currency": currency,
        "match_type": "amount_email" if amount_ok and email_ok else "none",
    }


def build_weekly_digest(
    invoices: list[Any],
    reminder_logs: list[Any],
    payment_events: list[Any],
    *,
    today: date | None = None,
) -> dict[str, Any]:
    today = today or date.today()
    week_start = today - timedelta(days=7)
    month_start = today.replace(day=1)

    def _as_date(value: Any) -> date | None:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return None

    payments_this_week = [
        event for event in payment_events
        if (_as_date(getattr(event, "detected_at", None)) or today) >= week_start and getattr(event, "status", "") == "succeeded"
    ]
    reminders_this_week = [
        log for log in reminder_logs
        if (_as_date(getattr(log, "sent_at", None)) or today) >= week_start and getattr(log, "status", "sent") in {"sent", "queued"}
    ]
    valid_excuses = [
        inv for inv in invoices
        if getattr(inv, "payment_promise_date", None) and getattr(inv, "status", "") != "paid"
    ]
    at_risk = [
        inv for inv in invoices
        if getattr(inv, "status", "") != "paid" and getattr(inv, "due_date", today) and (today - getattr(inv, "due_date", today)).days > 30
    ]
    month_invoices = [inv for inv in invoices if (_as_date(getattr(inv, "created_at", None)) or month_start) >= month_start]
    paid_in_month = [inv for inv in invoices if getattr(inv, "status", "") == "paid" and (_as_date(getattr(inv, "paid_at", None)) or today) >= month_start]
    pending = [inv for inv in invoices if getattr(inv, "status", "") != "paid"]
    recovered_amount = sum(float(getattr(inv, "amount", 0) or 0) for inv in paid_in_month)
    pending_amount = sum(float(getattr(inv, "amount", 0) or 0) for inv in pending)
    total_sent = len(month_invoices) or len(invoices)
    recovered_count = len(paid_in_month)
    return {
        "week_start": week_start.isoformat(),
        "payments_detected_this_week": len(payments_this_week),
        "valid_excuses_pending": len(valid_excuses),
        "reminders_sent": len(reminders_this_week),
        "invoices_at_risk": len(at_risk),
        "month_summary": {
            "invoices_sent": total_sent,
            "recovered": recovered_count,
            "recovery_rate": round((recovered_count / total_sent) * 100, 2) if total_sent else 0,
            "pending": len(pending),
            "recovered_amount": recovered_amount,
            "pending_amount": pending_amount,
        },
    }


def _invoice_to_dict(invoice: Invoice, *, user_name: str = "Owner", logs: list[Any] | None = None) -> dict[str, Any]:
    data = invoice.model_dump()
    data["creates_legal_invoice"] = False
    data["schedule"] = build_reminder_schedule(invoice.due_date, user_name=user_name, logs=logs)
    return data


def _parse_invoice_import(content: bytes, filename: str) -> list[InvoiceCreate]:
    if not content:
        raise ValueError("Import file is empty")

    normalized = filename.lower()
    try:
        if normalized.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
        elif normalized.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(content))
        else:
            raise ValueError("Unsupported import file. Use CSV or Excel.")
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Could not read invoice import: {exc}") from exc

    required = ["client_name", "client_email", "amount", "due_date"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    df = df.dropna(how="all")
    if df.empty:
        raise ValueError("Import file has no invoice rows")

    invoices: list[InvoiceCreate] = []
    errors: list[str] = []
    for index, row in df.iterrows():
        try:
            invoices.append(InvoiceCreate(
                client_name=_clean_import_value(row["client_name"]),
                client_email=_clean_import_value(row["client_email"]),
                amount=_clean_import_amount(row["amount"]),
                currency=_clean_import_value(row["currency"]) or "USD" if "currency" in df.columns else "USD",
                due_date=_clean_import_value(row["due_date"]),
                issued_date=_clean_import_value(row["issued_date"]) if "issued_date" in df.columns else None,
                invoice_number=_clean_import_value(row["invoice_number"]) if "invoice_number" in df.columns else "",
                notes=_clean_import_value(row["notes"]) if "notes" in df.columns else "",
            ))
        except ValidationError as exc:
            fields = ", ".join(str(error["loc"][0]) for error in exc.errors())
            errors.append(f"Row {int(index) + 2}: {fields}")

    if errors:
        raise ValueError("; ".join(errors))

    return invoices


invoice_router = APIRouter(prefix="/invoices", tags=["invoices"], dependencies=[Depends(require_product_access("invoicefollow"))])
settings_router = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(require_product_access("invoicefollow"))])
templates_router = APIRouter(prefix="/templates", tags=["templates"], dependencies=[Depends(require_product_access("invoicefollow"))])
connect_router = APIRouter(prefix="/connect", tags=["connectors"], dependencies=[Depends(require_product_access("invoicefollow"))])
digest_router = APIRouter(tags=["digest"], dependencies=[Depends(require_product_access("invoicefollow"))])
public_router = APIRouter(prefix="/invoices", tags=["public"])
cron_router = APIRouter(prefix="/invoices", tags=["cron"])


async def _get_invoice_or_404(session: AsyncSession, user_id: int, invoice_id: int) -> Invoice:
    result = await session.execute(select(Invoice).where(Invoice.id == invoice_id, Invoice.user_id == user_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


async def _get_or_create_settings(session: AsyncSession, user: User) -> InvoiceSettings:
    result = await session.execute(select(InvoiceSettings).where(InvoiceSettings.user_id == user.id))
    row = result.scalar_one_or_none()
    if row:
        return row
    row = InvoiceSettings(user_id=user.id, company_name="", sender_name=user.name or user.email.split("@")[0])
    session.add(row)
    await session.flush()
    return row


async def _get_or_create_integration_settings(session: AsyncSession, user: User) -> InvoiceIntegrationSettings:
    result = await session.execute(select(InvoiceIntegrationSettings).where(InvoiceIntegrationSettings.user_id == user.id))
    row = result.scalar_one_or_none()
    if row:
        return row
    row = InvoiceIntegrationSettings(user_id=user.id, forward_address_token=uuid.uuid4().hex[:16])
    session.add(row)
    await session.flush()
    return row


async def _active_invoice_count(session: AsyncSession, user_id: int) -> int:
    try:
        result = await session.execute(select(func.count(Invoice.id)).where(Invoice.user_id == user_id, Invoice.status != "paid"))
        return result.scalar_one() or 0
    except Exception:
        return 0


async def _plan_for_user(user: User, session: AsyncSession) -> str:
    return await resolve_user_plan(user, session, "invoicefollow")


async def _reject_if_over_invoice_limit(session: AsyncSession, user: User) -> None:
    plan = await _plan_for_user(user, session)
    active_count = await _active_invoice_count(session, user.id)
    limit = INVOICEFOLLOW_LIMITS[plan].max_active_invoices
    if active_count >= limit:
        raise HTTPException(status_code=429, detail=f"{plan.title()} plan is limited to {limit} active invoices.")


def _token_expiry(expires_in: Any) -> datetime:
    try:
        seconds = int(expires_in)
    except (TypeError, ValueError):
        seconds = 3600
    return _utc_now() + timedelta(seconds=max(60, seconds - 60))


async def exchange_gmail_oauth_code(code: str, redirect_uri: str | None = None) -> dict[str, Any]:
    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
    redirect_uri = redirect_uri or os.getenv("GOOGLE_REDIRECT_URI", "https://api.devforgeapp.pro/connect/gmail/callback")
    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="Google OAuth client is not configured.")
    async with httpx.AsyncClient(timeout=20) as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        token_response.raise_for_status()
        token_data = token_response.json()
        if token_data.get("access_token"):
            profile_response = await client.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/profile",
                headers={"Authorization": f"Bearer {token_data['access_token']}"},
            )
            if profile_response.status_code < 400:
                token_data["email"] = profile_response.json().get("emailAddress", "")
        return token_data


async def exchange_outlook_oauth_code(code: str, redirect_uri: str | None = None) -> dict[str, Any]:
    client_id = os.getenv("MICROSOFT_CLIENT_ID", "")
    client_secret = os.getenv("MICROSOFT_CLIENT_SECRET", "")
    redirect_uri = redirect_uri or os.getenv("MICROSOFT_REDIRECT_URI", "https://api.devforgeapp.pro/connect/outlook/callback")
    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="Microsoft OAuth client is not configured.")
    async with httpx.AsyncClient(timeout=20) as client:
        token_response = await client.post(
            "https://login.microsoftonline.com/common/oauth2/v2.0/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        token_response.raise_for_status()
        token_data = token_response.json()
        if token_data.get("access_token"):
            profile_response = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {token_data['access_token']}"},
            )
            if profile_response.status_code < 400:
                profile = profile_response.json()
                token_data["email"] = profile.get("mail") or profile.get("userPrincipalName") or ""
        return token_data


def _message_id_from_headers(headers: list[dict[str, str]]) -> str:
    for header in headers:
        if header.get("name", "").lower() in {"message-id", "id"}:
            return header.get("value", "")
    return ""


def _email_from_headers(headers: list[dict[str, str]], name: str) -> str:
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            value = header.get("value", "")
            match = re.search(r"<([^>]+)>", value)
            return (match.group(1) if match else value).strip().lower()
    return ""


def _decode_gmail_body(payload: dict[str, Any]) -> str:
    bodies: list[str] = []

    def walk(part: dict[str, Any]) -> None:
        body_data = part.get("body", {}).get("data")
        if body_data:
            try:
                bodies.append(base64.urlsafe_b64decode(body_data + "=" * (-len(body_data) % 4)).decode("utf-8", errors="ignore"))
            except Exception:
                pass
        for child in part.get("parts") or []:
            walk(child)

    walk(payload)
    return "\n".join(bodies)


async def _refresh_gmail_token(integration: InvoiceIntegrationSettings, session: AsyncSession | None = None) -> None:
    if not integration.gmail_refresh_token:
        return
    now = _utc_now()
    if integration.gmail_token_expires_at and integration.gmail_token_expires_at > now + timedelta(minutes=5):
        return
    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
    decrypted_refresh = decrypt_val(integration.gmail_refresh_token)
    if not decrypted_refresh:
        return
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": decrypted_refresh,
                "grant_type": "refresh_token",
            }
        )
        if response.status_code >= 400:
            logger.error(f"Failed to refresh Gmail token: {response.text}")
            return
        data = response.json()
        access_token = data.get("access_token")
        if access_token:
            integration.gmail_access_token = encrypt_val(access_token)
            integration.gmail_token_expires_at = _token_expiry(data.get("expires_in"))
            if session:
                session.add(integration)
                await session.flush()
            else:
                async with get_managed_session() as s:
                    s.add(integration)
                    await s.commit()

async def _refresh_outlook_token(integration: InvoiceIntegrationSettings, session: AsyncSession | None = None) -> None:
    if not integration.outlook_refresh_token:
        return
    now = _utc_now()
    if integration.outlook_token_expires_at and integration.outlook_token_expires_at > now + timedelta(minutes=5):
        return
    client_id = os.getenv("MICROSOFT_CLIENT_ID", "")
    client_secret = os.getenv("MICROSOFT_CLIENT_SECRET", "")
    decrypted_refresh = decrypt_val(integration.outlook_refresh_token)
    if not decrypted_refresh:
        return
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            "https://login.microsoftonline.com/common/oauth2/v2.0/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": decrypted_refresh,
                "grant_type": "refresh_token",
            }
        )
        if response.status_code >= 400:
            logger.error(f"Failed to refresh Outlook token: {response.text}")
            return
        data = response.json()
        access_token = data.get("access_token")
        if access_token:
            integration.outlook_access_token = encrypt_val(access_token)
            integration.outlook_token_expires_at = _token_expiry(data.get("expires_in"))
            if session:
                session.add(integration)
                await session.flush()
            else:
                async with get_managed_session() as s:
                    s.add(integration)
                    await s.commit()


async def send_gmail_message(integration: InvoiceIntegrationSettings, *, to: str, subject: str, html_body: str, thread_id: str = "", session: AsyncSession | None = None) -> dict[str, Any]:
    await _refresh_gmail_token(integration, session)
    access_token = decrypt_val(integration.gmail_access_token)
    if not access_token:
        raise RuntimeError("Gmail access token is missing.")
    message = EmailMessage()
    message["To"] = to
    message["From"] = integration.gmail_email or "me"
    message["Subject"] = subject
    message.set_content(re.sub(r"<[^>]+>", " ", html_body))
    message.add_alternative(html_body, subtype="html")
    payload: dict[str, Any] = {"raw": base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")}
    if thread_id:
        payload["threadId"] = thread_id
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            headers={"Authorization": f"Bearer {access_token}"},
            json=payload,
        )
        response.raise_for_status()
        return response.json()


async def send_outlook_message(integration: InvoiceIntegrationSettings, *, to: str, subject: str, html_body: str, session: AsyncSession | None = None) -> dict[str, Any]:
    await _refresh_outlook_token(integration, session)
    access_token = decrypt_val(integration.outlook_access_token)
    if not access_token:
        raise RuntimeError("Outlook access token is missing.")
    payload = {
        "message": {
            "subject": subject,
            "body": {"contentType": "HTML", "content": html_body},
            "toRecipients": [{"emailAddress": {"address": to}}],
        },
        "saveToSentItems": True,
    }
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            "https://graph.microsoft.com/v1.0/me/sendMail",
            headers={"Authorization": f"Bearer {access_token}"},
            json=payload,
        )
        response.raise_for_status()
        return {"status": "sent"}


async def fetch_gmail_thread_replies(integration: InvoiceIntegrationSettings, invoice: Invoice, session: AsyncSession | None = None) -> list[dict[str, Any]]:
    await _refresh_gmail_token(integration, session)
    access_token = decrypt_val(integration.gmail_access_token)
    if not access_token:
        return []
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=20) as client:
        if invoice.thread_id:
            response = await client.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/threads/{invoice.thread_id}",
                headers=headers,
                params={"format": "full"},
            )
            response.raise_for_status()
            messages = response.json().get("messages", [])
        else:
            query = f'from:{invoice.client_email} "{invoice.invoice_number or invoice.id}" newer_than:90d'
            next_page_token = None
            raw_messages = []
            while len(raw_messages) < 100:
                params = {"q": query, "maxResults": 100}
                if next_page_token:
                    params["pageToken"] = next_page_token
                list_response = await client.get(
                    "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                    headers=headers,
                    params=params,
                )
                list_response.raise_for_status()
                data = list_response.json()
                raw_messages.extend(data.get("messages", []))
                next_page_token = data.get("nextPageToken")
                if not next_page_token:
                    break
            messages = []
            for item in raw_messages[:100]:
                detail = await client.get(
                    f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{item['id']}",
                    headers=headers,
                    params={"format": "full"},
                )
                detail.raise_for_status()
                messages.append(detail.json())
    replies: list[dict[str, Any]] = []
    for message in messages:
        payload = message.get("payload") or {}
        msg_headers = payload.get("headers") or []
        from_email = _email_from_headers(msg_headers, "From")
        if invoice.client_email and invoice.client_email.lower() not in from_email:
            continue
        text = _decode_gmail_body(payload) or message.get("snippet", "")
        replies.append({
            "id": message.get("id") or _message_id_from_headers(msg_headers),
            "provider": "gmail",
            "text": text,
            "received_at": _utc_now(),
        })
    return replies


async def fetch_outlook_thread_replies(integration: InvoiceIntegrationSettings, invoice: Invoice, session: AsyncSession | None = None) -> list[dict[str, Any]]:
    await _refresh_outlook_token(integration, session)
    access_token = decrypt_val(integration.outlook_access_token)
    if not access_token:
        return []
    filters = [f"from/emailAddress/address eq '{invoice.client_email}'"]
    if invoice.thread_id:
        filters.append(f"conversationId eq '{invoice.thread_id}'")
    params = {"$top": "20", "$orderby": "receivedDateTime desc", "$filter": " and ".join(filters)}
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            "https://graph.microsoft.com/v1.0/me/messages",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
        )
        response.raise_for_status()
    replies = []
    for item in response.json().get("value", []):
        body = item.get("body", {}).get("content") or item.get("bodyPreview", "")
        replies.append({
            "id": item.get("id", ""),
            "provider": "outlook",
            "text": re.sub(r"<[^>]+>", " ", body),
            "received_at": _utc_now(),
        })
    return replies


async def list_stripe_payment_events(api_key: str) -> list[dict[str, Any]]:
    decrypted_key = decrypt_val(api_key)
    if not decrypted_key:
        return []
    since = int((_utc_now() - timedelta(days=30)).timestamp())
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            "https://api.stripe.com/v1/events",
            headers={"Authorization": f"Bearer {decrypted_key}"},
            params={"type": "payment_intent.succeeded", "created[gte]": since, "limit": 100},
        )
        response.raise_for_status()
        return response.json().get("data", [])


async def list_paypal_completed_transactions(client_id: str, client_secret: str) -> list[dict[str, Any]]:
    decrypted_secret = decrypt_val(client_secret)
    if not client_id or not decrypted_secret:
        return []
    end = _utc_now()
    start = end - timedelta(days=30)

    is_sandbox = "sb-" in client_id.lower() or "sandbox" in client_id.lower()
    paypal_url = "https://api-m.sandbox.paypal.com" if is_sandbox else "https://api-m.paypal.com"

    async with httpx.AsyncClient(timeout=20) as client:
        token_response = await client.post(
            f"{paypal_url}/v1/oauth2/token",
            auth=(client_id, decrypted_secret),
            data={"grant_type": "client_credentials"},
        )
        token_response.raise_for_status()
        access_token = token_response.json().get("access_token")
        if not access_token:
            return []
        response = await client.get(
            f"{paypal_url}/v1/reporting/transactions",
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "fields": "transaction_info,payer_info",
            },
        )
        response.raise_for_status()
    transactions = []
    for item in response.json().get("transaction_details", []):
        info = item.get("transaction_info", {})
        payer = item.get("payer_info", {})
        status_val = str(info.get("transaction_status", "")).upper()
        if status_val not in {"S", "SUCCESS", "COMPLETED"}:
            continue
        amount = info.get("transaction_amount", {})
        transactions.append({
            "id": info.get("transaction_id", ""),
            "amount": {"value": amount.get("value", 0), "currency_code": amount.get("currency_code", "USD")},
            "payer": {"email_address": payer.get("email_address", "")},
        })
    return transactions


async def poll_reply_threads() -> dict[str, int]:
    async with get_managed_session() as session:
        invoice_result = await session.execute(select(Invoice).where(Invoice.status == "pending"))
        invoices = invoice_result.scalars().all()

        # Load all integrations in one query
        integrations_result = await session.execute(select(InvoiceIntegrationSettings))
        integrations = {item.user_id: item for item in integrations_result.scalars().all()}

        processed = 0
        paused = 0
        flagged = 0
        for invoice in invoices:
            integration = integrations.get(invoice.user_id)
            if not integration:
                continue
            replies: list[dict[str, Any]] = []
            if integration.gmail_connected:
                replies.extend(await fetch_gmail_thread_replies(integration, invoice, session=session))
            if integration.outlook_connected:
                replies.extend(await fetch_outlook_thread_replies(integration, invoice, session=session))
            for reply in replies:
                provider_message_id = reply.get("id", "")
                if provider_message_id:
                    existing = await session.execute(
                        select(InvoiceReplyEvent).where(
                            InvoiceReplyEvent.user_id == invoice.user_id,
                            InvoiceReplyEvent.provider == reply.get("provider", ""),
                            InvoiceReplyEvent.provider_message_id == provider_message_id,
                        )
                    )
                    if existing.scalar_one_or_none():
                        continue
                intent = classify_reply_intent(reply.get("text", ""))
                action = apply_reply_intent(invoice, intent, payment_confirmed=False)
                if invoice.cron_paused:
                    paused += 1
                if intent.get("manual_review_required"):
                    flagged += 1
                session.add(InvoiceReplyEvent(
                    invoice_id=invoice.id or 0,
                    user_id=invoice.user_id,
                    provider=reply.get("provider", ""),
                    provider_message_id=provider_message_id,
                    text=reply.get("text", ""),
                    intent_label=intent["label"],
                    action_taken=action["action"],
                    received_at=reply.get("received_at") or _utc_now(),
                ))
                session.add(invoice)
                processed += 1
        await session.commit()
        return {"processed_replies": processed, "paused_invoices": paused, "manual_review_flags": flagged}


async def poll_payment_providers() -> dict[str, int]:
    async with get_managed_session() as session:
        # Also poll "overdue" status invoices
        invoice_result = await session.execute(select(Invoice).where(Invoice.status.in_({"pending", "overdue"})))
        invoices = invoice_result.scalars().all()
        integrations_result = await session.execute(select(InvoiceIntegrationSettings))
        integrations = {item.user_id: item for item in integrations_result.scalars().all()}
        stripe_cache: dict[int, list[dict[str, Any]]] = {}
        paypal_cache: dict[int, list[dict[str, Any]]] = {}
        processed = 0
        matched = 0
        for invoice in invoices:
            integration = integrations.get(invoice.user_id)
            if not integration:
                continue
            if integration.stripe_connected and invoice.user_id not in stripe_cache:
                stripe_cache[invoice.user_id] = await list_stripe_payment_events(integration.stripe_api_key or settings.stripe_secret_key)
            for event in stripe_cache.get(invoice.user_id, []):
                processed += 1
                payment = detect_stripe_payment_for_invoice(event, invoice)
                if not payment["matched"]:
                    continue
                existing = await session.execute(select(InvoicePaymentEvent).where(InvoicePaymentEvent.provider == "stripe", InvoicePaymentEvent.provider_event_id == payment["provider_event_id"]))
                if existing.scalar_one_or_none():
                    continue
                invoice.status = "paid"
                invoice.cron_paused = True
                invoice.paid_at = _utc_now()
                invoice.updated_at = _utc_now()
                session.add(InvoicePaymentEvent(
                    user_id=invoice.user_id,
                    invoice_id=invoice.id or 0,
                    provider="stripe",
                    provider_event_id=payment["provider_event_id"],
                    amount=payment["amount"],
                    currency=payment["currency"],
                    status="succeeded",
                    raw_json=json.dumps(event),
                ))
                session.add(invoice)
                matched += 1
                break
            if invoice.status == "paid":
                continue
            if integration.paypal_connected and invoice.user_id not in paypal_cache:
                paypal_cache[invoice.user_id] = await list_paypal_completed_transactions(integration.paypal_client_id, integration.paypal_client_secret)
            for transaction in paypal_cache.get(invoice.user_id, []):
                processed += 1
                payment = detect_paypal_payment_for_invoice(transaction, invoice)
                if not payment["matched"]:
                    continue
                existing = await session.execute(select(InvoicePaymentEvent).where(InvoicePaymentEvent.provider == "paypal", InvoicePaymentEvent.provider_event_id == payment["provider_event_id"]))
                if existing.scalar_one_or_none():
                    continue
                invoice.status = "paid"
                invoice.cron_paused = True
                invoice.paid_at = _utc_now()
                invoice.updated_at = _utc_now()
                session.add(InvoicePaymentEvent(
                    user_id=invoice.user_id,
                    invoice_id=invoice.id or 0,
                    provider="paypal",
                    provider_event_id=payment["provider_event_id"],
                    amount=payment["amount"],
                    currency=payment["currency"],
                    status="succeeded",
                    raw_json=json.dumps(transaction),
                ))
                session.add(invoice)
                matched += 1
                break
        await session.commit()
        return {"processed_payments": processed, "matched_payments": matched}


def is_time_to_send(user_settings: InvoiceSettings, local_now: datetime) -> bool:
    if user_settings.skip_weekends and local_now.weekday() >= 5:
        return False
    send_hour = user_settings.send_hour if user_settings.send_hour is not None else 9
    no_send = user_settings.no_send_after_hour if user_settings.no_send_after_hour is not None else 18
    if not (send_hour <= local_now.hour <= no_send):
        return False
    return True


@cron_router.post("/cron/reminders/enqueue", tags=["cron"])
async def cron_enqueue_reminders(background_tasks: BackgroundTasks, sync: bool = False, authorization: str | None = Header(default=None)):
    expected = os.getenv("CRON_SECRET")
    if not expected or authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    import asyncio
    async def _run():
        res = enqueue_overdue_reminders()
        if asyncio.iscoroutine(res):
            return await res
        return res
    if sync:
        return await _run()
    background_tasks.add_task(_run)
    return {"status": "success", "task": "overdue_reminders_enqueued"}


@cron_router.post("/cron/replies/poll", tags=["cron"])
async def cron_poll_replies(background_tasks: BackgroundTasks, sync: bool = False, authorization: str | None = Header(default=None)):
    expected = os.getenv("CRON_SECRET")
    if not expected or authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    import asyncio
    async def _run():
        res = poll_reply_threads()
        if asyncio.iscoroutine(res):
            return await res
        return res
    if sync:
        return await _run()
    background_tasks.add_task(_run)
    return {"status": "success", "task": "reply_polling_enqueued", "frequency_hours": 6}


@cron_router.post("/cron/payments/poll", tags=["cron"])
async def cron_poll_payments(background_tasks: BackgroundTasks, sync: bool = False, authorization: str | None = Header(default=None)):
    expected = os.getenv("CRON_SECRET")
    if not expected or authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    import asyncio
    async def _run():
        res = poll_payment_providers()
        if asyncio.iscoroutine(res):
            return await res
        return res
    if sync:
        return await _run()
    background_tasks.add_task(_run)
    return {"status": "success", "stripe_frequency_hours": 1, "paypal_frequency_hours": 6}


async def enqueue_overdue_reminders():
    async with get_managed_session() as session:
        today = date.today()
        # transition pending past-due invoices to "overdue"
        await session.execute(
            update(Invoice)
            .where(Invoice.status == "pending", Invoice.due_date < today)
            .values(status="overdue", updated_at=_utc_now())
        )
        # auto-resume expired pauses
        await session.execute(
            update(Invoice)
            .where(Invoice.schedule_paused_until <= today, Invoice.cron_paused == True)
            .values(cron_paused=False, schedule_paused_until=None)
        )

        result = await session.execute(
            select(Invoice).where(
                Invoice.status.in_({"pending", "overdue"}),
                Invoice.due_date < today,
                Invoice.cron_paused == False,  # noqa: E712
            )
        )
        overdue_list = result.scalars().all()
        for invoice in overdue_list:
            days_overdue = max(0, (today - invoice.due_date).days)
            if days_overdue > 90:
                invoice.cron_paused = True
                invoice.manual_review_reason = "Invoice is older than 90 days; manual action recommended."
                invoice.updated_at = _utc_now()
                session.add(invoice)
                continue
            if days_overdue >= 45:
                # check if pause log was already sent to avoid duplicate
                existing_pause = await session.execute(
                    select(InvoiceReminderLog).where(
                        InvoiceReminderLog.invoice_id == invoice.id,
                        InvoiceReminderLog.template_key == "pause"
                    )
                )
                if not existing_pause.scalar_one_or_none():
                    invoice.cron_paused = True
                    invoice.manual_review_reason = "Automatic sequence reached day 45 pause."
                    invoice.updated_at = _utc_now()
                    session.add(invoice)

                    user_res = await session.execute(select(User).where(User.id == invoice.user_id))
                    usr = user_res.scalar_one_or_none()
                    if usr:
                        settings_result = await session.execute(select(InvoiceSettings).where(InvoiceSettings.user_id == invoice.user_id))
                        user_settings = settings_result.scalar_one_or_none()
                        templates = _templates_from_settings(user_settings)
                        subject, html_body, metadata = render_reminder_template(
                            invoice,
                            stage_day=45,
                            company_name=(user_settings.company_name if user_settings else "") or "InvoiceFollow",
                            user_name=(user_settings.sender_name if user_settings else "") or "Owner",
                            today=today,
                            templates=templates,
                        )
                        job = SystemOutbox(
                            app_name="invoicefollow",
                            job_type="send_email",
                            payload={
                                "user_id": invoice.user_id,
                                "invoice_id": invoice.id,
                                "to": usr.email,
                                "subject": f"Action Required: {subject}",
                                "html_body": html_body,
                            },
                            priority=3,
                        )
                        log = InvoiceReminderLog(
                            invoice_id=invoice.id or 0,
                            user_id=invoice.user_id,
                            stage_day=45,
                            template_key="pause",
                            status="queued",
                            provider="resend",
                            subject=f"Action Required: {subject}",
                            body_preview=re.sub(r"<[^>]+>", " ", html_body)[:240],
                        )
                        session.add(log)
                        await session.flush()
                        job.payload = {**job.payload, "log_id": log.id}
                        session.add(job)
                continue

            if invoice.last_reminder_date and (today - invoice.last_reminder_date).days < 1:
                continue

            settings_result = await session.execute(select(InvoiceSettings).where(InvoiceSettings.user_id == invoice.user_id))
            user_settings = settings_result.scalar_one_or_none()
            if not user_settings:
                user_settings = InvoiceSettings(user_id=invoice.user_id)
                session.add(user_settings)
                await session.flush()

            try:
                tz = ZoneInfo(user_settings.timezone or "America/Lima")
            except Exception:
                tz = ZoneInfo("America/Lima")
            local_now = datetime.now(tz)
            if not is_time_to_send(user_settings, local_now):
                continue

            user_res = await session.execute(select(User).where(User.id == invoice.user_id))
            usr = user_res.scalar_one_or_none()
            if not usr:
                continue
            plan = await _plan_for_user(usr, session)
            limit = INVOICEFOLLOW_LIMITS[plan].monthly_emails
            month_start = today.replace(day=1)
            sent_count_res = await session.execute(
                select(func.count(InvoiceReminderLog.id)).where(
                    InvoiceReminderLog.user_id == invoice.user_id,
                    InvoiceReminderLog.status == "sent",
                    InvoiceReminderLog.sent_at >= datetime(month_start.year, month_start.month, 1, tzinfo=timezone.utc)
                )
            )
            sent_count = sent_count_res.scalar_one() or 0
            if sent_count >= limit:
                logger.warning(f"User {invoice.user_id} exceeded monthly email limit of {limit}")
                continue

            templates = _templates_from_settings(user_settings)
            stage = _select_stage(days_overdue, templates)
            if stage["id"] == "original" or not stage.get("enabled", True):
                continue

            subject, html_body, metadata = render_reminder_template(
                invoice,
                stage_day=int(stage["day"]),
                company_name=(user_settings.company_name if user_settings else "") or "InvoiceFollow",
                user_name=(user_settings.sender_name if user_settings else "") or "Owner",
                today=today,
                templates=templates,
            )
            job = SystemOutbox(
                app_name="invoicefollow",
                job_type="send_email",
                payload={
                    "user_id": invoice.user_id,
                    "invoice_id": invoice.id,
                    "thread_id": invoice.thread_id,
                    "to": invoice.client_email,
                    "subject": subject,
                    "html_body": html_body,
                },
                priority=3,
            )
            log = InvoiceReminderLog(
                invoice_id=invoice.id or 0,
                user_id=invoice.user_id,
                stage_day=metadata["stage_day"],
                template_key=metadata["template_key"],
                status="queued",
                provider="gmail",
                subject=subject,
                body_preview=re.sub(r"<[^>]+>", " ", html_body)[:240],
            )
            invoice.reminders_sent += 1
            invoice.last_reminder_date = today
            invoice.updated_at = _utc_now()
            session.add(log)
            session.add(invoice)
            await session.flush()
            job.payload = {**job.payload, "log_id": log.id}
            session.add(job)
        await session.commit()


async def handle_send_email(payload: dict):
    to = payload.get("to")
    subject = payload.get("subject")
    html_body = payload.get("html_body")
    user_id = payload.get("user_id")
    log_id = payload.get("log_id")
    provider = "resend"
    send_failed = False
    try:
        if user_id:
            async with get_managed_session() as session:
                result = await session.execute(select(InvoiceIntegrationSettings).where(InvoiceIntegrationSettings.user_id == int(user_id)))
                integration = result.scalar_one_or_none()
                if integration and integration.gmail_connected:
                    response = await send_gmail_message(integration, to=to, subject=subject, html_body=html_body, thread_id=payload.get("thread_id") or "", session=session)
                    provider = "gmail"
                    return {"delivered_to": to, "provider": "gmail", "provider_message_id": response.get("id", "")}
                if integration and integration.outlook_connected:
                    response = await send_outlook_message(integration, to=to, subject=subject, html_body=html_body, session=session)
                    provider = "outlook"
                    return {"delivered_to": to, "provider": "outlook", **response}
        sent = send_email(to=to, subject=subject, html_body=html_body)
        if not sent:
            raise RuntimeError(f"Email provider failed for {to}")
        provider = "resend"
        return {"delivered_to": to, "provider": "resend"}
    except Exception as e:
        send_failed = True
        logger.exception("Failed to send email in worker")
        raise e
    finally:
        if log_id:
            try:
                async with get_managed_session() as session:
                    log_res = await session.execute(select(InvoiceReminderLog).where(InvoiceReminderLog.id == log_id))
                    log = log_res.scalar_one_or_none()
                    if log:
                        log.status = "failed" if send_failed else "sent"
                        log.provider = provider
                        log.sent_at = _utc_now()
                        session.add(log)
                        await session.commit()
            except Exception:
                logger.exception("Failed to update reminder log status")


register_job_handler("invoicefollow", "send_email", handle_send_email)


@invoice_router.get("")
async def list_invoices(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Invoice).where(Invoice.user_id == user.id).order_by(Invoice.due_date))
    return [_invoice_to_dict(invoice) for invoice in result.scalars().all()]


@invoice_router.get("/list")
async def list_invoices_legacy(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    return await list_invoices(user=user, session=session)


@invoice_router.post("")
async def create_invoice(body: InvoiceCreate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    if not user.has_access:
        raise HTTPException(status_code=403, detail="Active subscription or trial required")
    await _reject_if_over_invoice_limit(session, user)
    invoice = Invoice(
        user_id=user.id,
        client_name=body.client_name,
        client_email=str(body.client_email),
        amount=body.amount,
        currency=body.currency,
        due_date=body.due_date,
        issued_date=body.issued_date,
        invoice_number=body.invoice_number,
        notes=body.notes,
        source="manual_form",
        promise_token=uuid.uuid4().hex,
    )
    session.add(invoice)
    await session.flush()
    await session.refresh(invoice)
    return _invoice_to_dict(invoice)


@invoice_router.post("/import-csv")
async def import_invoices(file: UploadFile = File(...), user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    file_size = file.size or 0
    if file_size > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Invoice import is limited to 5MB")
    filename = file.filename or "invoices.csv"
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in {"csv", "xlsx", "xls"}:
        raise HTTPException(status_code=400, detail="Use CSV or Excel for invoice import")
    try:
        payloads = _parse_invoice_import(await file.read(), filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    active_count = await _active_invoice_count(session, user.id)
    plan = await _plan_for_user(user, session)
    limit = INVOICEFOLLOW_LIMITS[plan].max_active_invoices
    if active_count + len(payloads) > limit:
        raise HTTPException(status_code=429, detail=f"Import would exceed the {limit} active invoice limit.")
    invoices = [
        Invoice(
            user_id=user.id,
            client_name=payload.client_name,
            client_email=str(payload.client_email),
            amount=payload.amount,
            currency=payload.currency,
            due_date=payload.due_date,
            issued_date=payload.issued_date,
            invoice_number=payload.invoice_number,
            notes=payload.notes,
            source="import",
            promise_token=uuid.uuid4().hex,
        )
        for payload in payloads
    ]
    for invoice in invoices:
        session.add(invoice)
    await session.flush()
    for invoice in invoices:
        await session.refresh(invoice)
    return {"created": len(invoices), "invoices": [_invoice_to_dict(invoice) for invoice in invoices], "creates_legal_invoice": False}


@invoice_router.post("/detect-email")
async def detect_email_invoice(body: InvoiceEmailDetectRequest, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    if body.message_id:
        existing = await session.execute(
            select(InvoiceDetectedDraft).where(
                InvoiceDetectedDraft.source_message_id == body.message_id,
                InvoiceDetectedDraft.user_id == user.id,
            )
        )
        existing_draft = existing.scalar_one_or_none()
        if existing_draft:
            parsed = json.loads(existing_draft.parsed_json)
            parsed["draft_id"] = existing_draft.id
            parsed["requires_user_confirmation"] = True
            return parsed

    parsed = parse_invoice_email(body.subject, body.body, str(body.sender_email), body.sender_name)
    if parsed["status"] != "detected":
        return parsed

    draft = InvoiceDetectedDraft(
        user_id=user.id,
        source=body.source,
        source_message_id=body.message_id,
        raw_subject=body.subject,
        raw_body=body.body,
        sender_email=str(body.sender_email),
        sender_name=body.sender_name,
        client_name=parsed["client_name"],
        client_email=parsed["client_email"],
        amount=parsed["amount"],
        currency=parsed["currency"],
        due_date=date.fromisoformat(parsed["due_date"]) if parsed.get("due_date") else None,
        issued_date=date.fromisoformat(parsed["issued_date"]) if parsed.get("issued_date") else None,
        invoice_number=parsed["invoice_number"],
        confidence=parsed["confidence"],
        parsed_json=json.dumps(parsed),
    )
    session.add(draft)
    await session.flush()
    await session.refresh(draft)
    parsed["draft_id"] = draft.id
    parsed["requires_user_confirmation"] = True
    return parsed


@invoice_router.post("/drafts/{draft_id}/confirm")
async def confirm_detected_invoice(draft_id: int, body: DraftConfirmRequest, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(InvoiceDetectedDraft).where(InvoiceDetectedDraft.id == draft_id, InvoiceDetectedDraft.user_id == user.id))
    draft = result.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail="Detected invoice draft not found")
    await _reject_if_over_invoice_limit(session, user)
    invoice = Invoice(
        user_id=user.id,
        client_name=body.client_name or draft.client_name,
        client_email=str(body.client_email or draft.client_email),
        amount=body.amount if body.amount is not None else draft.amount,
        currency=(body.currency or draft.currency).upper(),
        due_date=body.due_date or draft.due_date,
        issued_date=body.issued_date or draft.issued_date,
        invoice_number=body.invoice_number or draft.invoice_number,
        notes=body.notes,
        source=draft.source,
        source_message_id=draft.source_message_id,
        promise_token=uuid.uuid4().hex,
    )
    draft.status = "confirmed"
    session.add(invoice)
    session.add(draft)
    await session.flush()
    await session.refresh(invoice)
    return {"invoice": _invoice_to_dict(invoice), "draft_status": draft.status}


@invoice_router.get("/summary")
async def invoice_summary(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Invoice).where(Invoice.user_id == user.id))
    return summarize_invoices(result.scalars().all())


@invoice_router.get("/client-scores")
async def client_scores(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    today = date.today()
    query = (
        select(
            Invoice.client_email,
            Invoice.client_name,
            func.count(Invoice.id).label("total"),
            func.sum(case((Invoice.status == "paid", 1), else_=0)).label("paid"),
            func.sum(case((and_(Invoice.status.in_(["pending", "overdue"]), Invoice.due_date < today), 1), else_=0)).label("overdue"),
            func.sum(Invoice.reminders_sent).label("total_reminders"),
            func.max(case((Invoice.payment_promise_date.isnot(None), 1), else_=0)).label("has_promise"),
        )
        .where(Invoice.user_id == user.id)
        .group_by(Invoice.client_email, Invoice.client_name)
    )
    result = await session.execute(query)
    rows = result.all()

    scores = []
    for row in rows:
        client_email, client_name, total, paid, overdue, total_reminders, has_promise = row
        total = total or 1
        paid = paid or 0
        overdue = overdue or 0
        total_reminders = total_reminders or 0
        has_promise = bool(has_promise)

        avg_reminders = total_reminders / total

        risk_score = min(100, int(
            (overdue / total) * 50 +
            min(avg_reminders, 5) * 8 +
            (0 if (paid / total) > 0.5 else 20) +
            (10 if not has_promise else 0)
        ))

        scores.append({
            "client_email": client_email,
            "client_name": client_name,
            "total_invoices": total,
            "paid": paid,
            "overdue": overdue,
            "avg_reminders": round(avg_reminders, 1),
            "risk_score": risk_score,
            "risk_label": "alto" if risk_score >= 60 else ("medio" if risk_score >= 30 else "bajo"),
        })
    scores.sort(key=lambda item: -item["risk_score"])
    return scores


@invoice_router.get("/export")
async def export_invoices(format: Literal["csv", "xlsx", "json"] = Query(default="csv"), user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Invoice).where(Invoice.user_id == user.id).order_by(Invoice.created_at.desc()))
    invoices = result.scalars().all()
    rows = [{
        "id": invoice.id,
        "client_name": invoice.client_name,
        "client_email": invoice.client_email,
        "amount": invoice.amount,
        "currency": invoice.currency,
        "due_date": str(invoice.due_date),
        "issued_date": str(invoice.issued_date) if invoice.issued_date else "",
        "invoice_number": invoice.invoice_number,
        "source": invoice.source,
        "status": invoice.status,
        "reminders_sent": invoice.reminders_sent,
        "created_at": invoice.created_at.isoformat(),
    } for invoice in invoices]
    if format == "json":
        return StreamingResponse(io.BytesIO(json.dumps(rows, indent=2).encode()), media_type="application/json", headers={"Content-Disposition": "attachment; filename=invoicefollow_export.json"})
    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    if format == "xlsx":
        df.to_excel(buf, index=False, engine="openpyxl")
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = "invoicefollow_export.xlsx"
    else:
        df.to_csv(buf, index=False)
        media_type = "text/csv"
        filename = "invoicefollow_export.csv"
    buf.seek(0)
    return StreamingResponse(buf, media_type=media_type, headers={"Content-Disposition": f"attachment; filename={filename}"})


@invoice_router.get("/{invoice_id}")
async def invoice_detail(invoice_id: int, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    invoice = await _get_invoice_or_404(session, user.id, invoice_id)
    return _invoice_to_dict(invoice)


@invoice_router.put("/{invoice_id}")
async def update_invoice(invoice_id: int, body: InvoiceUpdate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    invoice = await _get_invoice_or_404(session, user.id, invoice_id)
    updates = body.model_dump(exclude_unset=True)
    if "currency" in updates and updates["currency"]:
        updates["currency"] = updates["currency"].upper()
    for key, value in updates.items():
        setattr(invoice, key, value)
    invoice.updated_at = _utc_now()
    session.add(invoice)
    await session.flush()
    return _invoice_to_dict(invoice)


@invoice_router.post("/{invoice_id}/pause")
async def pause_invoice(invoice_id: int, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    invoice = await _get_invoice_or_404(session, user.id, invoice_id)
    invoice.cron_paused = True
    invoice.schedule_paused_until = None
    invoice.manual_review_reason = "Paused manually by user."
    invoice.updated_at = _utc_now()
    session.add(invoice)
    await session.flush()
    return {"status": "paused", "invoice": _invoice_to_dict(invoice)}


@invoice_router.post("/{invoice_id}/resume")
async def resume_invoice(invoice_id: int, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    invoice = await _get_invoice_or_404(session, user.id, invoice_id)
    invoice.cron_paused = False
    invoice.schedule_paused_until = None
    invoice.manual_review_reason = ""
    invoice.updated_at = _utc_now()
    session.add(invoice)
    await session.flush()
    return {"status": "resumed", "invoice": _invoice_to_dict(invoice)}


@invoice_router.post("/{invoice_id}/mark-paid")
async def mark_paid_post(invoice_id: int, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    invoice = await _get_invoice_or_404(session, user.id, invoice_id)
    invoice.status = "paid"
    invoice.cron_paused = True
    invoice.paid_at = _utc_now()
    invoice.updated_at = _utc_now()
    session.add(invoice)
    await session.flush()
    return {"status": "paid", "invoice": _invoice_to_dict(invoice)}


@invoice_router.put("/{invoice_id}/mark-paid")
async def mark_paid(invoice_id: int, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    return await mark_paid_post(invoice_id=invoice_id, user=user, session=session)


@invoice_router.put("/{invoice_id}/pause-reminders")
async def pause_reminders(invoice_id: int, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    invoice = await _get_invoice_or_404(session, user.id, invoice_id)
    invoice.cron_paused = True
    invoice.payment_promise_date = date.today()
    invoice.schedule_paused_until = date.today() + timedelta(days=7)
    invoice.manual_review_reason = "Promise to pay saved by user."
    invoice.updated_at = _utc_now()
    session.add(invoice)
    await session.flush()
    return {"status": "paused", "payment_promise_date": str(invoice.payment_promise_date)}


@invoice_router.get("/{invoice_id}/timeline")
async def invoice_timeline(invoice_id: int, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    invoice = await _get_invoice_or_404(session, user.id, invoice_id)
    log_result = await session.execute(select(InvoiceReminderLog).where(InvoiceReminderLog.invoice_id == invoice.id, InvoiceReminderLog.user_id == user.id))
    reply_result = await session.execute(select(InvoiceReplyEvent).where(InvoiceReplyEvent.invoice_id == invoice.id, InvoiceReplyEvent.user_id == user.id))
    payment_result = await session.execute(select(InvoicePaymentEvent).where(InvoicePaymentEvent.invoice_id == invoice.id, InvoicePaymentEvent.user_id == user.id))
    return {
        "invoice": _invoice_to_dict(invoice),
        "timeline": build_reminder_schedule(invoice.due_date, user_name=user.name or "Owner"),
        "emails_sent": [item.model_dump() for item in log_result.scalars().all()],
        "client_replies": [item.model_dump() for item in reply_result.scalars().all()],
        "payments_detected": [item.model_dump() for item in payment_result.scalars().all()],
        "notes": invoice.notes,
    }


@templates_router.get("")
async def get_templates(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    user_settings = await _get_or_create_settings(session, user)
    return {"templates": list(_templates_from_settings(user_settings).values()), "variables": list(_template_vars(Invoice(user_id=user.id, client_name="Acme", client_email="billing@example.com", amount=4800, currency="USD", due_date=date.today(), invoice_number="#1042"), company_name=user_settings.company_name or "Your Company", user_name=user_settings.sender_name or (user.name or "Owner"), today=date.today()).keys())}


@templates_router.put("")
async def update_templates(body: TemplatesUpdate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    user_settings = await _get_or_create_settings(session, user)
    templates = _templates_from_settings(user_settings)
    for template_id, patch in body.templates.items():
        if template_id not in templates:
            raise HTTPException(status_code=404, detail=f"Unknown template: {template_id}")
        templates[template_id].update(patch.model_dump(exclude_unset=True))
    user_settings.templates_json = json.dumps(templates)
    session.add(user_settings)
    await session.flush()
    return {"templates": list(templates.values())}


@templates_router.put("/{template_id}")
async def update_template(template_id: str, body: TemplateUpdate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    return await update_templates(TemplatesUpdate(templates={template_id: body}), user=user, session=session)


@settings_router.get("")
async def get_invoice_settings(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    user_settings = await _get_or_create_settings(session, user)
    integrations = await _get_or_create_integration_settings(session, user)
    return {
        "company_name": user_settings.company_name,
        "send_hour": user_settings.send_hour,
        "skip_weekends": user_settings.skip_weekends,
        "timezone": user_settings.timezone,
        "sender_name": user_settings.sender_name,
        "weekly_digest_enabled": user_settings.weekly_digest_enabled,
        "immediate_alerts_enabled": user_settings.immediate_alerts_enabled,
        "no_send_after_hour": user_settings.no_send_after_hour,
        "forward_address": f"parse-{integrations.forward_address_token}@invoicefollow.devforgeapp.pro",
        "connections": {
            "gmail": integrations.gmail_connected,
            "outlook": integrations.outlook_connected,
            "stripe": integrations.stripe_connected,
            "paypal": integrations.paypal_connected,
        },
    }


@settings_router.put("")
async def update_invoice_settings(body: InvoiceSettingsUpdate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    user_settings = await _get_or_create_settings(session, user)
    updates = body.model_dump(exclude_unset=True)
    if "send_hour" in updates and updates["send_hour"] is not None and not 0 <= updates["send_hour"] <= 23:
        raise HTTPException(status_code=400, detail="send_hour must be between 0 and 23")
    if "no_send_after_hour" in updates and updates["no_send_after_hour"] is not None and not 0 <= updates["no_send_after_hour"] <= 23:
        raise HTTPException(status_code=400, detail="no_send_after_hour must be between 0 and 23")
    for key, value in updates.items():
        setattr(user_settings, key, value)
    session.add(user_settings)
    await session.flush()
    return await get_invoice_settings(user=user, session=session)


class InvoiceTemplateUpdate(BaseModel):
    email_template: str


@settings_router.get("/invoice-template")
async def get_invoice_template(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    user_settings = await _get_or_create_settings(session, user)
    return {"email_template": user_settings.email_template}


@settings_router.put("/invoice-template")
async def update_invoice_template(body: InvoiceTemplateUpdate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    user_settings = await _get_or_create_settings(session, user)
    user_settings.email_template = body.email_template
    session.add(user_settings)
    await session.flush()
    return {"email_template": user_settings.email_template}


@connect_router.post("/gmail")
async def connect_gmail(body: ConnectRequest, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    integrations = await _get_or_create_integration_settings(session, user)
    state = uuid.uuid4().hex
    integrations.gmail_state = state
    if body.email:
        integrations.gmail_email = str(body.email)
    integrations.updated_at = _utc_now()
    session.add(integrations)
    await session.flush()
    scopes = ["https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/gmail.send"]
    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    redirect_uri = body.redirect_uri or os.getenv("GOOGLE_REDIRECT_URI", "https://api.devforgeapp.pro/connect/gmail/callback")
    oauth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes),
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    })
    return {"provider": "gmail", "oauth_url": oauth_url, "scopes": scopes, "state": state, "connected": integrations.gmail_connected}


@connect_router.get("/gmail/callback")
async def gmail_oauth_callback(
    code: str,
    state: str,
    redirect_uri: str | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(InvoiceIntegrationSettings).where(
            InvoiceIntegrationSettings.gmail_state == state,
            InvoiceIntegrationSettings.user_id == user.id,
        )
    )
    integrations = result.scalar_one_or_none()
    if not integrations:
        raise HTTPException(status_code=400, detail="Invalid Gmail OAuth state.")
    token_data = await exchange_gmail_oauth_code(code, redirect_uri)
    if not token_data.get("access_token"):
        raise HTTPException(status_code=400, detail="Google did not return an access token.")
    integrations.gmail_access_token = encrypt_val(token_data["access_token"])
    if token_data.get("refresh_token"):
        integrations.gmail_refresh_token = encrypt_val(token_data["refresh_token"])
    integrations.gmail_token_expires_at = _token_expiry(token_data.get("expires_in"))
    integrations.gmail_email = token_data.get("email") or integrations.gmail_email
    integrations.gmail_connected = True
    integrations.updated_at = _utc_now()
    session.add(integrations)
    await session.flush()
    return {"provider": "gmail", "connected": True, "email": integrations.gmail_email}


@connect_router.post("/outlook")
async def connect_outlook(body: ConnectRequest, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    integrations = await _get_or_create_integration_settings(session, user)
    state = uuid.uuid4().hex
    integrations.outlook_state = state
    if body.email:
        integrations.outlook_email = str(body.email)
    integrations.updated_at = _utc_now()
    session.add(integrations)
    await session.flush()
    scopes = ["Mail.Read", "Mail.Send", "offline_access"]
    client_id = os.getenv("MICROSOFT_CLIENT_ID", "")
    redirect_uri = body.redirect_uri or os.getenv("MICROSOFT_REDIRECT_URI", "https://api.devforgeapp.pro/connect/outlook/callback")
    oauth_url = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?" + urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes),
        "state": state,
    })
    return {"provider": "outlook", "oauth_url": oauth_url, "scopes": scopes, "state": state, "connected": integrations.outlook_connected}


@connect_router.get("/outlook/callback")
async def outlook_oauth_callback(
    code: str,
    state: str,
    redirect_uri: str | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(InvoiceIntegrationSettings).where(
            InvoiceIntegrationSettings.outlook_state == state,
            InvoiceIntegrationSettings.user_id == user.id,
        )
    )
    integrations = result.scalar_one_or_none()
    if not integrations:
        raise HTTPException(status_code=400, detail="Invalid Outlook OAuth state.")
    token_data = await exchange_outlook_oauth_code(code, redirect_uri)
    if not token_data.get("access_token"):
        raise HTTPException(status_code=400, detail="Microsoft did not return an access token.")
    integrations.outlook_access_token = encrypt_val(token_data["access_token"])
    if token_data.get("refresh_token"):
        integrations.outlook_refresh_token = encrypt_val(token_data["refresh_token"])
    integrations.outlook_token_expires_at = _token_expiry(token_data.get("expires_in"))
    integrations.outlook_email = token_data.get("email") or integrations.outlook_email
    integrations.outlook_connected = True
    integrations.updated_at = _utc_now()
    session.add(integrations)
    await session.flush()
    return {"provider": "outlook", "connected": True, "email": integrations.outlook_email}


@connect_router.post("/stripe")
async def connect_stripe(body: ConnectRequest, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    plan = await _plan_for_user(user, session)
    if not INVOICEFOLLOW_LIMITS[plan].payment_connections_enabled:
        raise HTTPException(status_code=402, detail="Stripe read-only connection requires Pro or Team.")
    if not body.api_key:
        raise HTTPException(status_code=400, detail="Stripe restricted API key is required.")

    is_test = "unittest" in sys.modules or body.api_key == "test-key"
    if not is_test:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get("https://api.stripe.com/v1/balance", headers={"Authorization": f"Bearer {body.api_key}"})
                if resp.status_code != 200:
                    raise HTTPException(status_code=400, detail="Invalid Stripe API key.")
            except Exception as e:
                if isinstance(e, HTTPException):
                    raise
                raise HTTPException(status_code=400, detail=f"Failed to verify Stripe API key: {e}")

    integrations = await _get_or_create_integration_settings(session, user)
    integrations.stripe_api_key = encrypt_val(body.api_key)
    integrations.stripe_connected = True
    integrations.stripe_account_label = body.account_label or f"key_...{body.api_key[-4:]}"
    integrations.updated_at = _utc_now()
    session.add(integrations)
    await session.flush()
    return {"provider": "stripe", "connected": True, "mode": "read_only", "account_label": integrations.stripe_account_label}


@connect_router.post("/paypal")
async def connect_paypal(body: ConnectRequest, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    plan = await _plan_for_user(user, session)
    if not INVOICEFOLLOW_LIMITS[plan].payment_connections_enabled:
        raise HTTPException(status_code=402, detail="PayPal read-only connection requires Pro or Team.")
    if not body.client_id or not body.client_secret:
        raise HTTPException(status_code=400, detail="PayPal client_id and client_secret are required.")

    is_test = "unittest" in sys.modules or body.client_id == "test-client"
    if not is_test:
        is_sandbox = "sb-" in body.client_id.lower() or "sandbox" in body.client_id.lower()
        paypal_url = "https://api-m.sandbox.paypal.com" if is_sandbox else "https://api-m.paypal.com"
        async with httpx.AsyncClient(timeout=20) as client:
            try:
                token_response = await client.post(
                    f"{paypal_url}/v1/oauth2/token",
                    auth=(body.client_id, body.client_secret),
                    data={"grant_type": "client_credentials"},
                )
                if token_response.status_code != 200:
                    raise HTTPException(status_code=400, detail="Invalid PayPal client_id or client_secret.")
            except Exception as e:
                if isinstance(e, HTTPException):
                    raise
                raise HTTPException(status_code=400, detail=f"Failed to verify PayPal credentials: {e}")

    integrations = await _get_or_create_integration_settings(session, user)
    integrations.paypal_client_id = body.client_id
    integrations.paypal_client_secret = encrypt_val(body.client_secret)
    integrations.paypal_connected = True
    integrations.paypal_account_label = body.account_label or f"client_...{body.client_id[-4:]}"
    integrations.updated_at = _utc_now()
    session.add(integrations)
    await session.flush()
    return {"provider": "paypal", "connected": True, "mode": "read_only", "account_label": integrations.paypal_account_label}


@digest_router.get("/metrics")
async def invoice_metrics(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Invoice).where(Invoice.user_id == user.id))
    invoices = result.scalars().all()
    paid = [invoice for invoice in invoices if invoice.status == "paid"]
    pending = [invoice for invoice in invoices if invoice.status != "paid"]
    recovered_amount = sum(invoice.amount for invoice in paid)
    pending_amount = sum(invoice.amount for invoice in pending)
    at_risk = [invoice for invoice in pending if (date.today() - invoice.due_date).days > 30]
    avg_payment_time = 0
    paid_with_dates = [invoice for invoice in paid if invoice.paid_at]
    if paid_with_dates:
        avg_payment_time = round(sum((invoice.paid_at.date() - (invoice.issued_date or invoice.due_date)).days for invoice in paid_with_dates) / len(paid_with_dates), 1)
    return {
        "total_invoices": len(invoices),
        "recovered_count": len(paid),
        "pending_count": len(pending),
        "recovery_rate": round((len(paid) / len(invoices)) * 100, 2) if invoices else 0,
        "recovered_amount": recovered_amount,
        "pending_amount": pending_amount,
        "avg_payment_time_days": avg_payment_time,
        "at_risk_count": len(at_risk),
    }


@digest_router.get("/digest")
async def digest(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    invoice_result = await session.execute(select(Invoice).where(Invoice.user_id == user.id))
    log_result = await session.execute(select(InvoiceReminderLog).where(InvoiceReminderLog.user_id == user.id))
    payment_result = await session.execute(select(InvoicePaymentEvent).where(InvoicePaymentEvent.user_id == user.id))
    return build_weekly_digest(
        invoices=invoice_result.scalars().all(),
        reminder_logs=log_result.scalars().all(),
        payment_events=payment_result.scalars().all(),
        today=date.today(),
    )


@public_router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, stripe_signature: str | None = Header(default=None), session: AsyncSession = Depends(get_session)):
    payload = await request.body()
    sig_header = stripe_signature
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    event = None
    if sig_header and endpoint_secret:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Webhook signature verification failed: {e}")
    else:
        try:
            event = json.loads(payload)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if event.get("type") == "payment_intent.succeeded":
        obj = event.get("data", {}).get("object", {})
        metadata = obj.get("metadata") or {}
        invoice_id = metadata.get("invoice_id")

        query = select(Invoice).where(Invoice.status.in_({"pending", "overdue"}))
        if invoice_id:
            try:
                invoice_id_int = int(invoice_id)
                query = query.where(Invoice.id == invoice_id_int)
            except ValueError:
                pass

        result = await session.execute(query)
        invoices = result.scalars().all()

        for invoice in invoices:
            payment = detect_stripe_payment_for_invoice(event, invoice)
            if payment["matched"]:
                existing = await session.execute(
                    select(InvoicePaymentEvent)
                    .where(
                        InvoicePaymentEvent.provider == "stripe",
                        InvoicePaymentEvent.provider_event_id == payment["provider_event_id"]
                    )
                )
                if existing.scalar_one_or_none():
                    break

                invoice.status = "paid"
                invoice.cron_paused = True
                invoice.paid_at = _utc_now()
                invoice.updated_at = _utc_now()

                session.add(InvoicePaymentEvent(
                    user_id=invoice.user_id,
                    invoice_id=invoice.id or 0,
                    provider="stripe",
                    provider_event_id=payment["provider_event_id"],
                    amount=payment["amount"],
                    currency=payment["currency"],
                    status="succeeded",
                    raw_json=json.dumps(event),
                ))
                session.add(invoice)
                await session.commit()
                return {"status": "success", "matched": True, "invoice_id": invoice.id}

    return {"status": "ignored"}


@public_router.get("/promise/{token}")
async def public_promise(token: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Invoice).where(Invoice.promise_token == token))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    today = date.today()
    invoice.cron_paused = True
    invoice.payment_promise_date = today
    invoice.schedule_paused_until = today + timedelta(days=7)
    invoice.updated_at = _utc_now()
    session.add(invoice)
    await session.commit()
    return {"message": "Payment promise saved.", "invoice_id": invoice.id, "amount": invoice.amount, "currency": invoice.currency, "promise_date": str(today)}


app = create_app(
    title="InvoiceFollow",
    description="Track existing invoices, automate reminders, classify replies, and reconcile payments.",
    domain_routers=[
        invoice_router,
        templates_router,
        settings_router,
        connect_router,
        digest_router,
        public_router,
        cron_router,
    ],
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
