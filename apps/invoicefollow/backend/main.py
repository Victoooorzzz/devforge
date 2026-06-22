import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "packages"))

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Literal, Optional
import html
import io
import json
import logging
import re
import uuid

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, EmailStr, ValidationError, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel, select
import pandas as pd

from backend_core import create_app, get_current_user, get_session, User, require_product_access, get_settings
from backend_core.database import get_managed_session
from backend_core.email_service import send_email
from backend_core.outbox_models import SystemOutbox
from backend_core.product_insights import summarize_invoices
from backend_core.worker import register_job_handler


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
    outlook_connected: bool = Field(default=False)
    outlook_email: str = Field(default="")
    outlook_state: str = Field(default="")
    stripe_connected: bool = Field(default=False)
    stripe_account_label: str = Field(default="")
    paypal_connected: bool = Field(default=False)
    paypal_account_label: str = Field(default="")
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
    due_date: Optional[date] = None
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
    if user_settings and user_settings.email_template:
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


def build_reminder_schedule(due_date: date, today: date | None = None, user_name: str = "Owner") -> list[dict[str, Any]]:
    today = today or date.today()
    days_overdue = max(0, (today - due_date).days)
    return [
        {"day": 0, "name": "Invoice Original", "tone": "neutral", "sender_label": user_name, "status": "done" if days_overdue >= 0 else "pending"},
        {"day": 7, "name": "First Reminder", "tone": "friendly", "sender_label": user_name, "status": "done" if days_overdue >= 7 else "pending"},
        {"day": 15, "name": "Second Reminder", "tone": "firm", "sender_label": f"{user_name} (Billing)", "status": "done" if days_overdue >= 15 else "pending"},
        {"day": 30, "name": "Final Notice", "tone": "urgent", "sender_label": f"{user_name} (Accounts Receivable)", "status": "done" if days_overdue >= 30 else "pending"},
        {"day": 45, "name": "Pause", "tone": "manual", "sender_label": f"{user_name} (Accounts Receivable)", "status": "done" if days_overdue >= 45 else "pending"},
    ]


def _select_stage(days_overdue: int, templates: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    templates = templates or DEFAULT_TEMPLATES
    stage_key = "original"
    for key, template in templates.items():
        if int(template["day"]) <= days_overdue:
            stage_key = key
    return templates[stage_key]


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


def classify_reply_intent(text: str) -> dict[str, Any]:
    normalized = text.lower()
    paid_terms = ["ya transferi", "transferi", "deposite", "paid", "sent", "listo", "hecho", "ya esta", "confirmado"]
    valid_excuse_terms = ["problema con el banco", "demora", "proxima semana", "en proceso", "me comprometo", "el viernes", "next week", "bank issue"]
    false_excuse_terms = ["no recibi", "no me consta", "error", "no es mio", "ya pague", "contador", "accountant"]
    if any(term in normalized for term in paid_terms):
        return {"label": "PAGADO", "confidence": 0.86, "reason": "Client says payment was sent."}
    if any(term in normalized for term in valid_excuse_terms):
        return {"label": "EXCUSA_VALIDA", "confidence": 0.78, "reason": "Client gave a concrete payment delay or promise."}
    if any(term in normalized for term in false_excuse_terms):
        return {"label": "EXCUSA_FALSA", "confidence": 0.66, "reason": "Client disputed receipt or ownership without payment evidence."}
    return {"label": "DESCONOCIDO", "confidence": 0.35, "reason": "No payment or delay signal was found."}


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
    week_start = today - timedelta(days=7 if today.weekday() == 0 else today.weekday())
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
    recovered_amount = sum(float(getattr(inv, "amount", 0) or 0) for inv in paid_in_month) or sum(float(getattr(event, "amount", 0) or 0) for event in payments_this_week)
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


def _invoice_to_dict(invoice: Invoice) -> dict[str, Any]:
    data = invoice.model_dump()
    data["creates_legal_invoice"] = False
    data["schedule"] = build_reminder_schedule(invoice.due_date, user_name="Owner")
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
        result = await session.execute(select(Invoice).where(Invoice.user_id == user_id, Invoice.status != "paid"))
    except AssertionError:
        return 0
    return len(result.scalars().all())


def _plan_for_user(user: User) -> str:
    return "pro" if user.is_active else "free"


async def _reject_if_over_invoice_limit(session: AsyncSession, user: User) -> None:
    plan = _plan_for_user(user)
    active_count = await _active_invoice_count(session, user.id)
    limit = INVOICEFOLLOW_LIMITS[plan].max_active_invoices
    if active_count >= limit:
        raise HTTPException(status_code=429, detail=f"{plan.title()} plan is limited to {limit} active invoices.")


@cron_router.post("/cron/reminders/enqueue", tags=["cron"])
async def cron_enqueue_reminders(authorization: str | None = Header(default=None)):
    expected = os.getenv("CRON_SECRET")
    if expected and authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    await enqueue_overdue_reminders()
    return {"status": "success", "task": "overdue_reminders_enqueued"}


@cron_router.post("/cron/replies/poll", tags=["cron"])
async def cron_poll_replies(authorization: str | None = Header(default=None)):
    expected = os.getenv("CRON_SECRET")
    if expected and authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"status": "success", "task": "reply_polling_ready", "frequency_hours": 6}


@cron_router.post("/cron/payments/poll", tags=["cron"])
async def cron_poll_payments(authorization: str | None = Header(default=None)):
    expected = os.getenv("CRON_SECRET")
    if expected and authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"status": "success", "stripe_frequency_hours": 1, "paypal_frequency_hours": 6}


async def enqueue_overdue_reminders():
    async with get_managed_session() as session:
        today = date.today()
        result = await session.execute(
            select(Invoice).where(
                Invoice.status == "pending",
                Invoice.due_date <= today,
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
                invoice.cron_paused = True
                invoice.manual_review_reason = "Automatic sequence reached day 45 pause."
                invoice.updated_at = _utc_now()
                session.add(invoice)
                continue
            if invoice.last_reminder_date and (today - invoice.last_reminder_date).days < 1:
                continue

            settings_result = await session.execute(select(InvoiceSettings).where(InvoiceSettings.user_id == invoice.user_id))
            user_settings = settings_result.scalar_one_or_none()
            templates = _templates_from_settings(user_settings)
            stage = _select_stage(days_overdue, templates)
            if not stage.get("enabled", True):
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
                payload={"to": invoice.client_email, "subject": subject, "html_body": html_body},
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
            session.add(job)
            session.add(log)
            session.add(invoice)
        await session.commit()


async def handle_send_email(payload: dict):
    to = payload.get("to")
    subject = payload.get("subject")
    html_body = payload.get("html_body")
    send_email(to=to, subject=subject, html_body=html_body)
    return {"delivered_to": to}


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
    limit = INVOICEFOLLOW_LIMITS[_plan_for_user(user)].max_active_invoices
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
        due_date=body.due_date or draft.due_date or date.today(),
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
    result = await session.execute(select(Invoice).where(Invoice.user_id == user.id))
    all_invoices = result.scalars().all()
    from collections import defaultdict
    client_map = defaultdict(list)
    today = date.today()
    for invoice in all_invoices:
        key = invoice.client_email or invoice.client_name
        client_map[key].append(invoice)
    scores = []
    for _key, invoices in client_map.items():
        total = len(invoices)
        paid = sum(1 for item in invoices if item.status == "paid")
        overdue = sum(1 for item in invoices if item.status in ("pending", "overdue") and item.due_date < today)
        avg_reminders = sum(item.reminders_sent for item in invoices) / total
        has_promise = any(item.payment_promise_date for item in invoices)
        risk_score = min(100, int((overdue / total) * 50 + min(avg_reminders, 5) * 8 + (0 if paid / total > 0.5 else 20) + (10 if not has_promise else 0)))
        scores.append({
            "client_email": invoices[0].client_email,
            "client_name": invoices[0].client_name,
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
        integrations.gmail_connected = True
        integrations.gmail_email = str(body.email)
    integrations.updated_at = _utc_now()
    session.add(integrations)
    await session.flush()
    scopes = ["https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/gmail.send"]
    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    redirect_uri = body.redirect_uri or os.getenv("GOOGLE_REDIRECT_URI", "https://api.devforgeapp.pro/connect/gmail/callback")
    oauth_url = f"https://accounts.google.com/o/oauth2/v2/auth?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope={' '.join(scopes)}&state={state}&access_type=offline&prompt=consent"
    return {"provider": "gmail", "oauth_url": oauth_url, "scopes": scopes, "state": state, "connected": integrations.gmail_connected}


@connect_router.post("/outlook")
async def connect_outlook(body: ConnectRequest, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    integrations = await _get_or_create_integration_settings(session, user)
    state = uuid.uuid4().hex
    integrations.outlook_state = state
    if body.email:
        integrations.outlook_connected = True
        integrations.outlook_email = str(body.email)
    integrations.updated_at = _utc_now()
    session.add(integrations)
    await session.flush()
    scopes = ["Mail.Read", "Mail.Send", "offline_access"]
    client_id = os.getenv("MICROSOFT_CLIENT_ID", "")
    redirect_uri = body.redirect_uri or os.getenv("MICROSOFT_REDIRECT_URI", "https://api.devforgeapp.pro/connect/outlook/callback")
    oauth_url = f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope={' '.join(scopes)}&state={state}"
    return {"provider": "outlook", "oauth_url": oauth_url, "scopes": scopes, "state": state, "connected": integrations.outlook_connected}


@connect_router.post("/stripe")
async def connect_stripe(body: ConnectRequest, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    if not INVOICEFOLLOW_LIMITS[_plan_for_user(user)].payment_connections_enabled:
        raise HTTPException(status_code=402, detail="Stripe read-only connection requires Pro or Team.")
    integrations = await _get_or_create_integration_settings(session, user)
    integrations.stripe_connected = True
    integrations.stripe_account_label = body.account_label or (f"key_...{body.api_key[-4:]}" if body.api_key else "read-only")
    integrations.updated_at = _utc_now()
    session.add(integrations)
    await session.flush()
    return {"provider": "stripe", "connected": True, "mode": "read_only", "account_label": integrations.stripe_account_label}


@connect_router.post("/paypal")
async def connect_paypal(body: ConnectRequest, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    if not INVOICEFOLLOW_LIMITS[_plan_for_user(user)].payment_connections_enabled:
        raise HTTPException(status_code=402, detail="PayPal read-only connection requires Pro or Team.")
    integrations = await _get_or_create_integration_settings(session, user)
    integrations.paypal_connected = True
    integrations.paypal_account_label = body.account_label or "read-only"
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
