import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "packages"))

import asyncio
import base64, csv, hashlib, hmac, html, json, logging, io, re, secrets, tempfile, unicodedata, uuid
from difflib import SequenceMatcher
from urllib.parse import urlencode, urlparse
from urllib import error as url_error, request as url_request
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from fastapi import APIRouter, Depends, Header, HTTPException, File, UploadFile, Query, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, DateTime, func, Index, or_, text as sa_text, tuple_, delete
from sqlalchemy.exc import IntegrityError
from sqlmodel import Field, SQLModel, select
from pydantic import BaseModel, ConfigDict, EmailStr, Field as PydanticField, TypeAdapter, ValidationError
from typing import Any, Optional, List, Literal
from datetime import datetime, timezone, timedelta
from collections import Counter
import pandas as pd
import snowballstemmer
from cryptography.fernet import Fernet

from backend_core import create_app, get_current_user, get_session, User, require_product_access
from backend_core.database import get_managed_session
from backend_core.email_service import send_email
from backend_core.outbox_models import SystemOutbox
from backend_core.plan_limits import (
    get_feedbacklens_limits,
    reject_feedbacklens_feedback_count_if_needed,
    reject_feedbacklens_source_if_needed,
)
from backend_core.worker import register_job_handler

logger = logging.getLogger(__name__)
DEDUPE_LOOKBACK_LIMIT = 50
DEDUPE_LOOKBACK_DAYS = 90
EXPORT_BATCH_SIZE = 200
PUBLIC_WEBHOOK_RATE_LIMIT = 60
PUBLIC_WEBHOOK_RATE_WINDOW_SECONDS = 60
SEMANTIC_DUPLICATE_THRESHOLD = 0.75
SIMHASH_HAMMING_THRESHOLD = 10
FEEDBACK_TEXT_LIMIT = 2000
SPAM_TERMS = (
    "buy now", "click here", "free money", "casino", "viagra", "limited offer",
    "act now", "order now", "special promotion", "credit card", "weight loss",
    "work from home", "make money", "million dollars", "risk free", "call now",
    "exclusive deal", "congratulations you won", "click below", "100% free",
    "no obligation", "this is not spam", "winner", "lottery", "dear friend",
    "nigerian prince", "investment opportunity", "double your", "earn extra cash",
)
DEFAULT_TOPIC_TERMS = (
    "checkout", "payment", "billing", "login", "export", "csv", "crash",
    "performance", "onboarding", "pricing", "mobile", "dashboard", "refund",
    "summary", "dark", "mode", "api", "webhook", "integration", "sync", "import",
    "notification", "email", "password", "account", "subscription", "cancel",
)
DEFAULT_URGENT_TERMS = (
    "bug", "crash", "refund", "payment", "billing", "checkout", "login",
    "critical", "broken",
)
_ENGLISH_STEMMER = snowballstemmer.stemmer("english")
CONTEXTUAL_SPAM_TERMS = {
    "buy now", "credit card", "investment opportunity", "make money",
    "weight loss", "work from home",
}
OUTBOUND_HTTP_HOSTS = {
    "api.github.com",
    "api.twitter.com",
    "api.x.com",
    "github.com",
    "oauth.reddit.com",
    "www.reddit.com",
}
FEEDBACK_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "for",
    "from",
    "i",
    "in",
    "is",
    "it",
    "my",
    "of",
    "on",
    "or",
    "our",
    "that",
    "the",
    "this",
    "to",
    "was",
    "we",
    "when",
    "with",
    "you",
    "your",
    "they",
    "them",
    "their",
    "has",
    "have",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "could",
    "should",
    "can",
    "may",
    "might",
    "after",
    "before",
}
NEGATION_OF_NEGATIVE = {
    "not", "no", "never", "none", "nobody", "nothing", "neither", "nowhere",
    "hardly", "barely", "scarcely", "without", "aint", "lack", "lacking",
}
INABILITY_WORDS = {
    "cannot", "can't", "couldn't", "unable", "fails", "failed", "failing",
    "won't", "wouldn't", "doesn't", "dont", "doesnt", "didnt", "isnt",
    "arent", "wasnt", "werent", "hasnt", "havent", "hadnt",
}
POSITIVE_WORDS = [
    "love", "great", "amazing", "excellent", "perfect", "best", "wonderful",
    "fantastic", "good", "thank", "thanks", "awesome", "happy", "pleased",
    "smooth", "fast", "impressive", "beautiful", "clean", "intuitive", "easy",
    "reliable", "solid", "flawless", "outstanding", "superb", "brilliant",
    "enjoy", "nice", "helpful", "efficient", "seamless", "pleasant", "delightful",
    "remarkable", "incredible", "satisfied", "recommend", "perfectly", "works",
]
NEGATIVE_WORDS = [
    "bad", "terrible", "worst", "hate", "broken", "awful", "horrible",
    "useless", "poor", "wrong", "disappointed", "frustrating", "slow",
    "annoying", "ugly", "confusing", "complicated", "clunky", "unreliable",
    "messy", "outdated", "defective", "unusable", "waste", "regret", "sad",
    "angry", "ridiculous", "pathetic", "unacceptable", "inferior", "weak",
    "disgusting", "trash", "garbage", "crap", "suck", "hates", "hated",
]
NEGATIVE_ADJECTIVES = {
    "bad", "terrible", "awful", "horrible", "useless", "poor", "wrong", "broken",
    "disappointing", "frustrating", "annoying", "ugly", "confusing", "clunky",
    "slow", "unreliable", "messy", "outdated", "defective", "unusable",
    "inferior", "weak", "disgusting", "pathetic", "unacceptable",
}
URGENT_WORDS = [
    "urgent", "immediately", "refund", "charge", "lost", "critical", "asap",
    "blocked", "blocking", "down", "outage", "security", "breach", "hack",
    "stolen", "fraud", "emergency", "escalate", "legal", "lawyer", "complaint",
    "ceo", "manager", "supervisor", "deadline", "penalty", "fine", "sued", "help",
]
FEEDBACKLENS_SENTIMENT_MODEL = os.getenv(
    "FEEDBACKLENS_SENTIMENT_MODEL",
    "distilbert-base-uncased-finetuned-sst-2-english",
)
FEEDBACKLENS_URGENCY_MODEL = os.getenv(
    "FEEDBACKLENS_URGENCY_MODEL",
    "cross-encoder/nli-deberta-v3-xsmall",
)
FEEDBACKLENS_LOCAL_ANALYSIS_TIMEOUT_SECONDS = float(os.getenv("FEEDBACKLENS_LOCAL_ANALYSIS_TIMEOUT_SECONDS", "8"))
_sentiment_pipeline = None
_urgency_pipeline = None
_embedder = None


class SpamDetectedError(ValueError):
    def __init__(self, reasons: list[str]):
        self.reasons = reasons
        super().__init__(f"Feedback rejected as spam: {reasons}")


class SourceAuthorizationError(RuntimeError):
    pass


class FeedbackLensCrypto:
    _fernet: Fernet | None = None
    _key: str = ""

    @classmethod
    def get_fernet(cls) -> Fernet:
        key_str = os.getenv("ENCRYPTION_KEY", "").strip()
        if not key_str:
            raise RuntimeError("ENCRYPTION_KEY is required for FeedbackLens source secrets.")
        if cls._fernet is None or cls._key != key_str:
            try:
                decoded = base64.urlsafe_b64decode(key_str.encode())
                if len(decoded) != 32:
                    raise ValueError()
            except Exception:
                key_str = base64.urlsafe_b64encode(hashlib.sha256(key_str.encode()).digest()).decode()
            cls._fernet = Fernet(key_str.encode())
            cls._key = os.getenv("ENCRYPTION_KEY", "").strip()
        return cls._fernet

    @classmethod
    def encrypt(cls, value: str) -> str:
        if not value or value.startswith("enc:"):
            return value
        return "enc:" + cls.get_fernet().encrypt(value.encode()).decode()

    @classmethod
    def decrypt(cls, value: str) -> str:
        if not value or not value.startswith("enc:"):
            return value
        try:
            return cls.get_fernet().decrypt(value[4:].encode()).decode()
        except Exception:
            return value


def encrypt_secret(value: str) -> str:
    return FeedbackLensCrypto.encrypt(value)


def decrypt_secret(value: str) -> str:
    return FeedbackLensCrypto.decrypt(value)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _run_in_thread(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(None, lambda: func(*args, **kwargs))


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class FeedbackEntry(SQLModel, table=True):
    __tablename__ = "feedback_entries"
    # Blank source_message_id values stay reusable for manual/imported feedback.
    __table_args__ = (
        Index(
            "uq_feedback_entries_user_source_message_id_nonempty",
            "user_id",
            "source",
            "source_message_id",
            unique=True,
            sqlite_where=sa_text("source_message_id != ''"),
            postgresql_where=sa_text("source_message_id <> ''"),
        ),
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    text: str
    sentiment: Optional[str] = None       # positive | negative | neutral
    confidence: Optional[float] = None
    themes_json: str = Field(default="[]")
    is_urgent: bool = Field(default=False)
    draft_reply: Optional[str] = None
    analysis_engine: Optional[str] = None  # "enhanced_keyword" | "local_transformers" | "keyword"
    source: str = Field(default="manual", index=True)
    author: str = Field(default="")
    source_url: str = Field(default="")
    source_message_id: str = Field(default="", index=True)
    cluster_slug: str = Field(default="", index=True)
    priority: str = Field(default="low", index=True)
    created_at: datetime = Field(default_factory=_utc_now, sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(default_factory=_utc_now, sa_column=Column(DateTime(timezone=True), nullable=False))
    analyzed_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))


class FeedbackSource(SQLModel, table=True):
    __tablename__ = "feedback_sources"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    source_type: str = Field(index=True)
    display_name: str = Field(default="")
    handle: str = Field(default="")
    status: str = Field(default="connected", index=True)
    access_token: str = Field(default="")
    refresh_token: str = Field(default="")
    webhook_secret: str = Field(default="")
    config_json: str = Field(default="{}")
    forward_token: str = Field(default_factory=lambda: uuid.uuid4().hex, index=True)
    last_polled_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    created_at: datetime = Field(default_factory=_utc_now, sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(default_factory=_utc_now, sa_column=Column(DateTime(timezone=True), nullable=False))


class FeedbackSettings(SQLModel, table=True):
    __tablename__ = "feedback_settings"
    user_id: int = Field(primary_key=True)
    custom_prompt: str = Field(default="")
    negative_threshold: float = Field(default=0.5, ge=0, le=1)
    alert_email: str = Field(default="")
    weekly_summary_enabled: bool = Field(default=True)
    timezone: str = Field(default="UTC")
    last_weekly_digest_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class FeedbackCreate(BaseModel):
    text: str


class FeedbackSourceCreate(BaseModel):
    source_type: Literal["twitter", "reddit", "github", "canny", "email", "manual"]
    display_name: str = ""
    handle: str = ""
    access_token: str = ""
    refresh_token: str = ""
    webhook_secret: str = ""
    repo: str = ""
    config: dict[str, Any] = PydanticField(default_factory=dict)


class EmailAttachmentPayload(BaseModel):
    filename: str = ""
    content_type: str = ""
    text: str = ""
    content: str = ""
    encoding: Literal["plain", "base64"] = "plain"


class EmailIngestRequest(BaseModel):
    from_email: str
    subject: str = ""
    body: str
    message_id: str = ""
    source_url: str = ""
    attachments: list[EmailAttachmentPayload] = PydanticField(default_factory=list)


class CannyIngestRequest(BaseModel):
    author: str = ""
    title: str = ""
    body: str
    url: str = ""
    post_id: str = ""


class GitHubIssueRequest(BaseModel):
    repo: str = ""
    labels: list[str] = PydanticField(default_factory=lambda: ["feedback-lens"])


class GitHubConnectRequest(BaseModel):
    repo: str = ""
    redirect_uri: str = ""


class TwitterConnectRequest(BaseModel):
    handle: str = ""
    query: str = ""
    redirect_uri: str = ""


class RedditConnectRequest(BaseModel):
    subreddit: str = ""
    query: str = ""
    redirect_uri: str = ""


class FeedbackPrefsUpdate(BaseModel):
    custom_prompt: str = ""
    negative_threshold: float = PydanticField(default=0.5, ge=0, le=1)
    alert_email: Optional[EmailStr] = None
    weekly_summary_enabled: bool = True
    timezone: str = "UTC"


class FeedbackSourceConfig(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    query: str = ""
    handle: str = ""
    oauth_state: str = ""
    redirect_uri: str = ""
    code_verifier: str = ""
    subreddit: str = ""
    repo: str = ""


class GitHubWebhookUser(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    login: str = ""


class GitHubWebhookIssue(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    id: int
    title: str = ""
    body: str = ""
    html_url: str = ""
    user: GitHubWebhookUser = PydanticField(default_factory=GitHubWebhookUser)


class GitHubWebhookPayload(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    action: str = ""
    issue: GitHubWebhookIssue | None = None


_THEMES_ADAPTER = TypeAdapter(list[str])

# ---------------------------------------------------------------------------
# Analysis Engines: enhanced rules by default, local transformers optional
# ---------------------------------------------------------------------------

def _configured_spam_terms(custom_terms: tuple[str, ...] = ()) -> tuple[str, ...]:
    env_terms = tuple(
        term.strip().lower()
        for term in os.getenv("FEEDBACKLENS_SPAM_TERMS", "").split(",")
        if term.strip()
    )
    return tuple(dict.fromkeys((*SPAM_TERMS, *env_terms, *(term.lower() for term in custom_terms))))


def _is_spam_feedback_v2(
    text: str,
    *,
    custom_terms: tuple[str, ...] = (),
    whitelist: tuple[str, ...] = (),
) -> dict[str, Any]:
    lowered = text.lower()
    reasons: list[str] = []
    score = 0

    matched_whitelist = [term.lower() for term in whitelist if term and term.lower() in lowered]
    if matched_whitelist:
        return {"is_spam": False, "score": 0, "reasons": ["user_whitelist"]}

    matched_terms = [term for term in _configured_spam_terms(custom_terms) if term in lowered]
    spam_hits = len(matched_terms)
    strong_spam_hits = [term for term in matched_terms if term not in CONTEXTUAL_SPAM_TERMS]
    if spam_hits >= 2:
        score += 3
        reasons.append(f"multi_spam_terms({spam_hits})")
    elif spam_hits == 1:
        score += 1
        reasons.append("spam_term")

    url_count = len(re.findall(r"https?://", lowered))
    if url_count >= 3:
        score += 2
        reasons.append("many_urls")
    elif url_count >= 1 and strong_spam_hits:
        score += 2
        reasons.append("url+spam")

    if len(text) > 20:
        caps_ratio = sum(1 for char in text if char.isupper()) / max(len(text), 1)
        if caps_ratio > 0.5:
            score += 2
            reasons.append("shouting_caps")

    if text.count("!") / max(len(text), 1) > 0.08:
        score += 1
        reasons.append("exclamation_spam")

    words = [word.lower() for word in re.findall(r"[a-zA-Z]+", text)]
    repeats = sum(1 for _word, count in Counter(words).items() if count > 3)
    if repeats:
        score += 1
        reasons.append("repeated_words")

    if len(text) > 50:
        entropy_ratio = len(set(text.lower())) / len(text)
        if entropy_ratio < 0.3:
            score += 1
            reasons.append("low_entropy")

    return {"is_spam": score >= 3, "score": score, "reasons": reasons}


def _is_spam_feedback(text: str) -> bool:
    return bool(_is_spam_feedback_v2(text)["is_spam"])


def _configured_feedback_terms(name: str, defaults: tuple[str, ...]) -> tuple[str, ...]:
    configured = tuple(
        term.strip().lower()
        for term in os.getenv(name, "").split(",")
        if term.strip()
    )
    return tuple(dict.fromkeys((*configured, *defaults)))


def _extract_themes(text: str, focus_terms: str = "") -> list[str]:
    tokens = list(_feedback_tokens(text))
    focus = {_stem_feedback_token(token) for token in _normalize_feedback_text(focus_terms).split() if len(token) > 2}
    priority_terms = _configured_feedback_terms("FEEDBACKLENS_TOPIC_TERMS", DEFAULT_TOPIC_TERMS)
    ordered: list[str] = []
    for token in priority_terms:
        if _stem_feedback_token(token) in tokens and token not in ordered:
            ordered.append(token)
    for token in sorted(focus & set(tokens)):
        if token not in ordered:
            ordered.append(token)
    for token, _count in Counter(tokens).most_common(6):
        if token not in ordered:
            ordered.append(token)
    return ordered[:5]


def _software_failure_score(text: str) -> int:
    lowered = text.lower()
    problem_indicators = [
        "not", "cannot", "can't", "couldn't", "won't", "isn't", "arent", "doesn't",
        "dont", "doesnt", "didnt", "wasnt", "werent", "hasnt", "havent", "error",
        "broken", "fail", "failed", "failure", "bug", "crash", "crashes", "crashed",
        "blocked", "blocking", "unauthorized", "unauthorised", "not working",
        "doesn't work", "slow", "freezes", "hangs", "stuck", "timeout", "unable to",
        "impossible", "missing", "disappeared", "blank", "empty", "wrong",
    ]
    if not any(indicator in lowered for indicator in problem_indicators):
        return 0

    patterns = [
        r"\bcrash(?:es|ed|ing)?\b",
        r"\bblock(?:s|ed|ing)?\b",
        r"\bbroken\b",
        r"\bbug(?:s)?\b",
        r"\berror(?:s)?\b",
        r"\bfail(?:s|ed|ing|ure)?\b",
        r"\bunauthori[sz]ed\b",
        r"\bnot working\b",
        r"\bcan't\b",
        r"\bcannot\b",
        r"\bfreezes?\b",
        r"\bhangs?\b",
        r"\bstuck\b",
        r"\btimeout\b",
        r"\bslow\b",
        r"\bunable to\b",
    ]
    score = sum(1 for pattern in patterns if re.search(pattern, lowered))

    auth_problem_terms = {
        "broken", "error", "slow", "cannot", "can't", "unauthorized", "unauthorised",
        "fail", "fails", "failed", "failure", "unable", "blocked", "blocking",
        "stuck", "timeout", "crash", "crashes", "crashed",
    }
    for sentence in re.split(r"(?<=[.!?])\s+", lowered):
        words = re.findall(r"[a-zA-Z']+", sentence)
        auth_indexes = {
            index
            for index, word in enumerate(words)
            if word in {"login", "signin"} or (word == "sign" and index + 1 < len(words) and words[index + 1] == "in")
        }
        for index in auth_indexes:
            window = words[max(0, index - 5): min(len(words), index + 6)]
            if any(word.strip("'") in auth_problem_terms for word in window):
                score += 1
                return score
    return score


def _support_draft(sentiment: str, is_urgent: bool, themes: list[str] | None = None) -> str:
    theme_set = {str(theme).lower() for theme in (themes or [])}
    if theme_set & {"billing", "payment", "checkout", "refund", "subscription"}:
        topic_sentence = "We are reviewing the billing and payment details now."
    elif theme_set & {"login", "password", "account"}:
        topic_sentence = "We are reviewing the account access path now."
    elif theme_set & {"export", "csv", "import"}:
        topic_sentence = "We are reviewing the data import and export path now."
    elif theme_set & {"api", "webhook", "integration", "sync"}:
        topic_sentence = "We are reviewing the integration path now."
    else:
        topic_sentence = "Our team is reviewing the reported area now."
    if is_urgent:
        return (
            "Thanks for reaching out. We received your message and are treating it as a priority. "
            f"{topic_sentence} We will follow up with the next step as soon as possible."
        )
    if sentiment == "negative":
        return (
            "Thanks for sharing this. We are sorry the experience did not meet expectations. "
            f"{topic_sentence} Could you send a few more details so we can look into it quickly?"
        )
    if sentiment == "positive":
        return "Thanks for the kind words. We appreciate you taking the time to share what is working well."
    return "Thanks for the feedback. We have logged it for review and will use it while planning upcoming improvements."


def _analyze_with_enhanced_keywords(text: str, focus_terms: str = "") -> dict:
    text_lower = text.lower()
    sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", text_lower) if sentence.strip()]
    if not sentences:
        sentences = [text_lower]

    pos_score = 0
    neg_score = 0
    urgent_score = 0

    for sentence in sentences:
        words = re.findall(r"[a-zA-Z']+", sentence)
        sentence_pos = 0
        sentence_neg = 0
        sentence_urgent = 0

        for index, word in enumerate(words):
            clean = word.lower().strip("'")
            window = words[max(0, index - 3): min(len(words), index + 4)]
            is_negated = any(item.lower().strip("'") in NEGATION_OF_NEGATIVE for item in window)
            is_inability = any(item.lower().strip("'") in INABILITY_WORDS for item in window)

            if clean in POSITIVE_WORDS:
                if is_negated and not is_inability:
                    sentence_neg += 2
                elif is_inability:
                    sentence_neg += 1
                else:
                    sentence_pos += 1
            elif clean in NEGATIVE_WORDS:
                if is_negated and not is_inability and clean in NEGATIVE_ADJECTIVES:
                    sentence_pos += 2
                elif is_inability:
                    sentence_neg += 1
                else:
                    sentence_neg += 1
            elif clean in URGENT_WORDS:
                sentence_urgent += 1

        failure = _software_failure_score(sentence)
        if failure > 0:
            negated_failure = re.search(
                r"\b(not|n't|never|hardly|barely)\s+\w{0,12}\s*(broken|crash|fail|bug|error|block|hang|freeze|slow)",
                sentence,
            )
            if not negated_failure:
                sentence_neg += failure

        pos_score += sentence_pos
        neg_score += sentence_neg
        urgent_score += sentence_urgent

    failure_total = _software_failure_score(text_lower)
    if neg_score > pos_score:
        sentiment = "negative"
        confidence = min(0.55 + 0.04 * neg_score, 0.95)
    elif pos_score > neg_score:
        sentiment = "positive"
        confidence = min(0.55 + 0.04 * pos_score, 0.95)
    else:
        sentiment = "neutral"
        confidence = 0.55

    is_urgent = (urgent_score > 0 and sentiment == "negative") or (urgent_score > 0 and failure_total > 0)
    themes = _extract_themes(text, focus_terms)
    return {
        "sentiment": sentiment,
        "confidence": round(confidence, 2),
        "themes": themes,
        "is_urgent": is_urgent,
        "draft_reply": _support_draft(sentiment, is_urgent, themes),
        "engine": "enhanced_keyword",
    }


def _get_sentiment_pipeline():
    global _sentiment_pipeline
    if os.getenv("FEEDBACKLENS_ENABLE_LOCAL_ML", "0").strip().lower() not in {"1", "true", "yes"}:
        raise RuntimeError("FeedbackLens local ML is disabled; set FEEDBACKLENS_ENABLE_LOCAL_ML=1 to opt in.")
    if _sentiment_pipeline is None:
        try:
            from optimum.onnxruntime import ORTModelForSequenceClassification
            from transformers import AutoTokenizer, pipeline

            tokenizer = AutoTokenizer.from_pretrained(FEEDBACKLENS_SENTIMENT_MODEL)
            model = ORTModelForSequenceClassification.from_pretrained(
                FEEDBACKLENS_SENTIMENT_MODEL,
                export=True,
            )
            _sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model=model,
                tokenizer=tokenizer,
                device=-1,
                truncation=True,
                max_length=512,
            )
        except Exception as exc:
            logger.warning("ONNX sentiment pipeline unavailable, trying transformers default: %s", exc)
            from transformers import pipeline
            _sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model=FEEDBACKLENS_SENTIMENT_MODEL,
                device=-1,
                truncation=True,
                max_length=512,
            )
    return _sentiment_pipeline


def _get_urgency_pipeline():
    global _urgency_pipeline
    if os.getenv("FEEDBACKLENS_ENABLE_LOCAL_ML", "0").strip().lower() not in {"1", "true", "yes"}:
        raise RuntimeError("FeedbackLens local ML is disabled; set FEEDBACKLENS_ENABLE_LOCAL_ML=1 to opt in.")
    if _urgency_pipeline is None:
        from transformers import pipeline
        _urgency_pipeline = pipeline(
            "zero-shot-classification",
            model=FEEDBACKLENS_URGENCY_MODEL,
            device=-1,
        )
    return _urgency_pipeline


def _analyze_with_local_transformers_sync(text: str, focus_terms: str = "") -> dict:
    pipe = _get_sentiment_pipeline()
    result = pipe(text[:512])
    label = str(result[0].get("label", "")).lower()
    score = float(result[0].get("score", 0.55))
    sentiment = "positive" if "positive" in label else "negative" if "negative" in label else "neutral"

    fallback = _analyze_with_enhanced_keywords(text, focus_terms)
    failure_score = _software_failure_score(text)
    if sentiment == "positive" and failure_score > 0 and fallback["sentiment"] == "negative":
        sentiment = "negative"
        score = max(score, fallback["confidence"])

    urgent_pipe = _get_urgency_pipeline()
    urgent_result = urgent_pipe(
        text[:512],
        candidate_labels=["urgent technical issue", "general feedback", "compliment"],
    )
    is_urgent = urgent_result["labels"][0] == "urgent technical issue" and urgent_result["scores"][0] > 0.6

    themes = _extract_themes(text, focus_terms)
    return {
        "sentiment": sentiment,
        "confidence": round(score, 2),
        "themes": themes,
        "is_urgent": is_urgent,
        "draft_reply": _support_draft(sentiment, is_urgent, themes),
        "engine": "local_transformers",
    }


async def _analyze_with_local_transformers(text: str, focus_terms: str = "") -> dict:
    try:
        return await asyncio.wait_for(
            _run_in_thread(_analyze_with_local_transformers_sync, text, focus_terms),
            timeout=FEEDBACKLENS_LOCAL_ANALYSIS_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning("Local transformer analysis timed out; using enhanced keyword fallback.")
        fallback = _analyze_with_enhanced_keywords(text, focus_terms)
        fallback["engine"] = "enhanced_keyword"
        return fallback
    except Exception as exc:
        logger.warning("Local transformer analysis unavailable, using enhanced keywords: %s", exc)
        return _analyze_with_enhanced_keywords(text, focus_terms)


def _analyze_feedback_locally(text: str, focus_terms: str = "") -> dict:
    return _analyze_with_enhanced_keywords(text, focus_terms)


async def _analyze_feedback_locally_async(text: str, focus_terms: str = "") -> dict:
    engine = os.getenv("FEEDBACKLENS_ANALYSIS_ENGINE", "enhanced_keyword").strip().lower()
    if engine in {"local_transformers", "transformers", "distilbert"}:
        return await _analyze_with_local_transformers(text, focus_terms)
    return _analyze_with_enhanced_keywords(text, focus_terms)


def _cluster_slug_for_analysis(text: str, themes: list[str] | None = None) -> str:
    tokens = _feedback_tokens(text)
    theme_tokens = [_stem_feedback_token(token) for token in (themes or []) if token]
    all_tokens = tokens | set(theme_tokens)
    if {"dark", "mode"}.issubset(all_tokens):
        return "dark-mode"
    if {"csv", "export"}.issubset(all_tokens):
        return "export"
    if {"checkout", "crash"}.issubset(all_tokens):
        return "checkout"
    priority_terms = _configured_feedback_terms("FEEDBACKLENS_TOPIC_TERMS", DEFAULT_TOPIC_TERMS)
    for term in priority_terms:
        if _stem_feedback_token(term) in all_tokens:
            return term
    source = theme_tokens[0] if theme_tokens else (sorted(tokens)[0] if tokens else "general")
    slug = re.sub(r"[^a-z0-9]+", "-", source.lower()).strip("-")
    return slug or "general"


def _priority_for_analysis(analysis: dict) -> str:
    themes = set(analysis.get("themes") or [])
    urgent_terms = set(_configured_feedback_terms("FEEDBACKLENS_URGENT_TERMS", DEFAULT_URGENT_TERMS))
    if analysis.get("is_urgent") or themes & urgent_terms:
        return "urgent"
    if analysis.get("sentiment") == "negative":
        return "high"
    return "low"


def _apply_local_processing(entry: FeedbackEntry, focus_terms: str = "") -> dict:
    analysis = _analyze_feedback_locally(entry.text, focus_terms)
    entry.sentiment = analysis["sentiment"]
    entry.confidence = analysis["confidence"]
    entry.themes_json = json.dumps(analysis["themes"])
    entry.is_urgent = analysis["is_urgent"]
    entry.draft_reply = analysis.get("draft_reply")
    entry.analysis_engine = analysis["engine"]
    entry.cluster_slug = _cluster_slug_for_analysis(entry.text, analysis["themes"])
    entry.priority = _priority_for_analysis(analysis)
    entry.updated_at = _utc_now()
    entry.analyzed_at = entry.updated_at
    return analysis


async def _apply_local_processing_async(entry: FeedbackEntry, focus_terms: str = "") -> dict:
    analysis = await _analyze_feedback_locally_async(entry.text, focus_terms)
    entry.sentiment = analysis["sentiment"]
    entry.confidence = analysis["confidence"]
    entry.themes_json = json.dumps(analysis["themes"])
    entry.is_urgent = analysis["is_urgent"]
    entry.draft_reply = analysis.get("draft_reply")
    entry.analysis_engine = analysis["engine"]
    entry.cluster_slug = _cluster_slug_for_analysis(entry.text, analysis["themes"])
    entry.priority = _priority_for_analysis(analysis)
    entry.updated_at = _utc_now()
    entry.analyzed_at = entry.updated_at
    return analysis


def _combine_feedback_text(title: str = "", body: str = "") -> str:
    pieces = [title.strip(), body.strip()]
    return "\n\n".join(piece for piece in pieces if piece)


def _source_poll_frequency_hours(source_type: str) -> int | None:
    return {
        "twitter": 6,
        "reddit": 6,
        "github": 1,
        "canny": None,
        "email": None,
        "manual": None,
    }.get(source_type)


def _sentence_split(text: str) -> list[str]:
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", text) if sentence.strip()]


def _clean_feedback_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not normalized:
        return ""
    spam_check = _is_spam_feedback_v2(normalized)
    if spam_check["is_spam"]:
        raise SpamDetectedError(spam_check["reasons"])
    if len(normalized) <= FEEDBACK_TEXT_LIMIT:
        return normalized

    key_terms = (
        "bug", "broken", "crash", "refund", "payment", "billing", "checkout", "login",
        "export", "csv", "urgent", "blocked", "error", "slow", "pricing", "feature",
        "security", "breach", "hack", "stolen", "fraud", "outage", "down",
    )
    sentences = _sentence_split(normalized)
    selected: list[str] = []
    for sentence in sentences[:3]:
        if sentence not in selected:
            selected.append(sentence)
    for sentence in sentences:
        lowered = sentence.lower()
        if any(term in lowered for term in key_terms) and sentence not in selected:
            selected.append(sentence)
    compact = " ".join(selected).strip() or normalized[:FEEDBACK_TEXT_LIMIT]
    if len(compact) > FEEDBACK_TEXT_LIMIT:
        compact = compact[:FEEDBACK_TEXT_LIMIT].rsplit(" ", 1)[0].strip()
    return compact


def _extract_attachment_text(attachment: EmailAttachmentPayload) -> str:
    text = attachment.text.strip()
    if text:
        return text

    content_type = attachment.content_type.lower()
    filename = attachment.filename.lower()
    text_like = (
        content_type.startswith("text/")
        or content_type in {"application/json", "application/csv", "text/csv"}
        or filename.endswith((".txt", ".csv", ".json", ".md", ".log"))
    )
    if not text_like or not attachment.content:
        return ""

    raw = attachment.content
    if attachment.encoding == "base64":
        try:
            raw_bytes = base64.b64decode(raw, validate=True)
            return raw_bytes.decode("utf-8", errors="replace").strip()
        except Exception:
            return ""
    return raw.strip()


def _combine_email_feedback_text(body: EmailIngestRequest) -> str:
    pieces = [_combine_feedback_text(body.subject, body.body)]
    for attachment in body.attachments:
        extracted = _extract_attachment_text(attachment)
        if extracted:
            label = attachment.filename or "attachment"
            pieces.append(f"Attachment {label}: {extracted}")
    return "\n\n".join(piece for piece in pieces if piece.strip())


class _NoRedirectHandler(url_request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _validate_outbound_url(url: str) -> str:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme != "https" or not hostname or parsed.username or parsed.password:
        raise ValueError("Outbound integrations require an authenticated HTTPS provider URL")
    if hostname not in OUTBOUND_HTTP_HOSTS:
        raise ValueError(f"Outbound provider host is not allowed: {hostname}")
    return url


def _open_outbound(req: url_request.Request):
    _validate_outbound_url(req.full_url)
    opener = url_request.build_opener(_NoRedirectHandler())
    response = opener.open(req, timeout=30)
    _validate_outbound_url(response.geturl())
    return response


def _http_json(url: str, *, method: str = "GET", headers: dict[str, str] | None = None, payload: dict | None = None) -> dict:
    _validate_outbound_url(url)
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = url_request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "DevForge-FeedbackLens",
            **(headers or {}),
        },
    )
    try:
        with _open_outbound(req) as response:
            raw = response.read().decode("utf-8")
    except url_error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        if exc.code in {401, 403}:
            raise SourceAuthorizationError(raw or "Provider authorization failed") from exc
        raise HTTPException(status_code=502, detail=f"Source request failed: {raw}") from exc
    return json.loads(raw) if raw else {}


def _http_form_json(
    url: str,
    *,
    payload: dict[str, str],
    headers: dict[str, str] | None = None,
    basic_auth: tuple[str, str] | None = None,
) -> dict:
    _validate_outbound_url(url)
    request_headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "DevForge-FeedbackLens",
        **(headers or {}),
    }
    if basic_auth:
        token = base64.b64encode(f"{basic_auth[0]}:{basic_auth[1]}".encode("utf-8")).decode("ascii")
        request_headers["Authorization"] = f"Basic {token}"

    req = url_request.Request(
        url,
        data=urlencode(payload).encode("utf-8"),
        method="POST",
        headers=request_headers,
    )
    try:
        with _open_outbound(req) as response:
            raw = response.read().decode("utf-8")
    except url_error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        raise HTTPException(status_code=502, detail=f"OAuth token exchange failed: {raw}") from exc
    return json.loads(raw) if raw else {}


def _source_config(source: FeedbackSource) -> dict:
    try:
        config = FeedbackSourceConfig.model_validate_json(source.config_json or "{}")
        return {key: value for key, value in config.model_dump().items() if value not in {"", None}}
    except (ValidationError, ValueError, TypeError):
        return {}


def _pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii").rstrip("=")
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).decode("ascii").rstrip("=")
    return verifier, challenge


async def _feedbacklens_plan(user: User, session: AsyncSession):
    return await get_feedbacklens_limits(user, session)


def _count_from_result(result: Any) -> int:
    if hasattr(result, "scalar_one"):
        return int(result.scalar_one() or 0)
    if hasattr(result, "scalar"):
        value = result.scalar
        if isinstance(value, int):
            return value
    rows = getattr(result, "rows", None)
    if rows is not None:
        return len(rows)
    return 0


async def _feedback_source_count(user_id: int, session: AsyncSession) -> int:
    result = await session.execute(
        select(func.count()).select_from(FeedbackSource).where(
            FeedbackSource.user_id == user_id,
            FeedbackSource.status != "deleted",
        )
    )
    return _count_from_result(result)


async def _monthly_feedback_count(user_id: int, session: AsyncSession) -> int:
    month_start = _utc_now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    result = await session.execute(
        select(func.count()).select_from(FeedbackEntry).where(
            FeedbackEntry.user_id == user_id,
            FeedbackEntry.created_at >= month_start,
        )
    )
    return _count_from_result(result)


async def _enforce_source_limit(user: User, source_type: str, session: AsyncSession) -> None:
    plan, limits = await _feedbacklens_plan(user, session)
    source_count = await _feedback_source_count(user.id, session)
    reject_feedbacklens_source_if_needed(plan, limits, source_type, source_count)


async def _enforce_feedback_limit(user: User, incoming_count: int, session: AsyncSession) -> None:
    plan, limits = await _feedbacklens_plan(user, session)
    monthly_count = await _monthly_feedback_count(user.id, session)
    reject_feedbacklens_feedback_count_if_needed(plan, limits, monthly_count, incoming_count)


async def _enforce_public_webhook_rate_limit(source_id: int, session: AsyncSession) -> None:
    bind = getattr(session, "bind", None)
    dialect_name = getattr(getattr(bind, "dialect", None), "name", "")
    if dialect_name == "postgresql":
        await session.execute(
            sa_text("SELECT pg_advisory_xact_lock(:key)").bindparams(key=8_405_000 + source_id)
        )

    now = _utc_now().replace(tzinfo=None)
    bucket = f"feedbacklens-rate-{source_id}"
    result = await session.execute(
        select(func.count()).select_from(SystemOutbox).where(
            SystemOutbox.app_name == bucket,
            SystemOutbox.job_type == "github_ingest",
            SystemOutbox.status == "completed",
            SystemOutbox.created_at >= now - timedelta(seconds=PUBLIC_WEBHOOK_RATE_WINDOW_SECONDS),
        )
    )
    if _count_from_result(result) >= PUBLIC_WEBHOOK_RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Webhook rate limit exceeded")

    session.add(SystemOutbox(
        app_name=bucket,
        job_type="github_ingest",
        payload={"source_id": source_id},
        status="completed",
        attempts=1,
        completed_at=now,
        result={"accepted": True},
    ))
    await session.flush()


def _parse_themes(value: str | None) -> list[str]:
    try:
        return _THEMES_ADAPTER.validate_json(value or "[]", strict=True)
    except (ValidationError, ValueError, TypeError):
        return []


def _encode_feedback_cursor(created_at: datetime, entry_id: int) -> str:
    payload = json.dumps({
        "created_at": (_as_aware_utc(created_at) or _utc_now()).isoformat(),
        "id": entry_id,
    }, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _decode_feedback_cursor(cursor: str) -> tuple[datetime, int]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
        created_at = datetime.fromisoformat(payload["created_at"])
        entry_id = int(payload["id"])
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid feedback cursor") from exc
    aware_created_at = _as_aware_utc(created_at)
    if aware_created_at is None or entry_id < 1:
        raise ValueError("Invalid feedback cursor")
    return aware_created_at, entry_id


def _serialize(entry: FeedbackEntry) -> dict:
    created_at = _as_aware_utc(entry.created_at) or _utc_now()
    updated_at = _as_aware_utc(getattr(entry, "updated_at", None)) or created_at
    analyzed_at = _as_aware_utc(getattr(entry, "analyzed_at", None))
    return {
        "id": entry.id,
        "text": entry.text,
        "sentiment": entry.sentiment,
        "confidence": entry.confidence,
        "themes": _parse_themes(entry.themes_json),
        "is_urgent": entry.is_urgent,
        "draft_reply": entry.draft_reply,
        "analysis_engine": entry.analysis_engine,
        "analyzed_at": analyzed_at.isoformat() if analyzed_at else None,
        "created_at": created_at.isoformat(),
        "updated_at": updated_at.isoformat(),
        "source": getattr(entry, "source", "manual"),
        "author": getattr(entry, "author", ""),
        "source_url": getattr(entry, "source_url", ""),
        "source_message_id": getattr(entry, "source_message_id", ""),
        "cluster_slug": getattr(entry, "cluster_slug", ""),
        "priority": getattr(entry, "priority", "low"),
    }


def _normalize_feedback_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text.lower())
    cleaned = "".join(
        char if char.isspace() or unicodedata.category(char)[0] in {"L", "N"} else " "
        for char in normalized
    )
    return re.sub(r"\s+", " ", cleaned).strip()


def _stem_feedback_token(token: str) -> str:
    normalized = _normalize_feedback_text(token)
    if not normalized or " " in normalized:
        return normalized
    return _ENGLISH_STEMMER.stemWord(normalized)


def _feedback_tokens(text: str) -> set[str]:
    normalized = _normalize_feedback_text(text)
    return {
        _stem_feedback_token(token)
        for token in normalized.split()
        if len(token) > 2 and token not in FEEDBACK_STOPWORDS
    }


def _semantic_similarity(left: str, right: str) -> float:
    left_normalized = _normalize_feedback_text(left)
    right_normalized = _normalize_feedback_text(right)
    if not left_normalized or not right_normalized:
        return 0.0
    if left_normalized == right_normalized:
        return 1.0

    left_tokens = _feedback_tokens(left)
    right_tokens = _feedback_tokens(right)
    sequence_ratio = SequenceMatcher(None, left_normalized, right_normalized).ratio()
    if len(left_tokens) < 3 or len(right_tokens) < 3:
        return sequence_ratio

    intersection = left_tokens & right_tokens
    union = left_tokens | right_tokens
    jaccard = len(intersection) / len(union) if union else 0.0
    overlap = len(intersection) / min(len(left_tokens), len(right_tokens))
    length_ratio = min(len(left_tokens), len(right_tokens)) / max(len(left_tokens), len(right_tokens))
    weighted_overlap = overlap if length_ratio >= 0.65 else overlap * length_ratio
    return max(sequence_ratio, jaccard, weighted_overlap)


def _simhash_tokens(text: str) -> list[str]:
    tokens = sorted(_feedback_tokens(text))
    bigrams = [f"{tokens[index]}:{tokens[index + 1]}" for index in range(len(tokens) - 1)]
    return tokens + bigrams


def _simhash(text: str) -> int:
    features = _simhash_tokens(text)
    if not features:
        return 0
    weights = [0] * 64
    for feature in features:
        digest = hashlib.sha256(feature.encode("utf-8")).digest()
        value = int.from_bytes(digest[:8], "big")
        for bit in range(64):
            weights[bit] += 1 if value & (1 << bit) else -1
    fingerprint = 0
    for bit, weight in enumerate(weights):
        if weight >= 0:
            fingerprint |= 1 << bit
    return fingerprint


def _hamming_distance(left: int, right: int) -> int:
    return (left ^ right).bit_count()


def _find_duplicate_simhash(text: str, candidates: list[FeedbackEntry]) -> FeedbackEntry | None:
    text_hash = _simhash(text)
    text_features = set(_simhash_tokens(text))
    best_match = None
    best_score = 0.0
    best_distance = 65

    for candidate in candidates:
        candidate_text = getattr(candidate, "text", "") or ""
        candidate_features = set(_simhash_tokens(candidate_text))
        if not text_features or not candidate_features:
            continue

        distance = _hamming_distance(text_hash, _simhash(candidate_text))
        intersection = text_features & candidate_features
        overlap = len(intersection) / min(len(text_features), len(candidate_features))
        semantic_score = _semantic_similarity(text, candidate_text)

        if distance <= SIMHASH_HAMMING_THRESHOLD or (len(intersection) >= 3 and overlap >= 0.55):
            candidate_score = max(semantic_score, overlap, 1 - (distance / 64))
            if candidate_score > best_score or (candidate_score == best_score and distance < best_distance):
                best_score = candidate_score
                best_distance = distance
                best_match = candidate

    if best_match and best_score >= 0.55:
        return best_match
    return None


def _get_embedder():
    global _embedder
    if os.getenv("FEEDBACKLENS_ENABLE_EMBEDDINGS", "0").strip().lower() not in {"1", "true", "yes"}:
        raise RuntimeError("FeedbackLens embeddings are disabled; set FEEDBACKLENS_ENABLE_EMBEDDINGS=1 to opt in.")
    if _embedder is None:
        from transformers import AutoModel, AutoTokenizer
        model_name = os.getenv("FEEDBACKLENS_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModel.from_pretrained(model_name)
        _embedder = (tokenizer, model)
    return _embedder


async def _find_duplicate_embedding(text: str, candidates: list[FeedbackEntry]) -> FeedbackEntry | None:
    if not candidates or len(candidates) > 50:
        return None
    try:
        tokenizer, model = _get_embedder()
        import torch

        def embed(value: str):
            encoded = tokenizer(value, return_tensors="pt", truncation=True, max_length=256)
            with torch.no_grad():
                output = model(**encoded)
            vector = output.last_hidden_state.mean(dim=1)
            return vector / vector.norm(dim=1, keepdim=True)

        text_vector = await _run_in_thread(embed, text)
        best_match = None
        best_score = 0.0
        for candidate in candidates:
            candidate_vector = await _run_in_thread(embed, getattr(candidate, "text", "") or "")
            score = float((text_vector @ candidate_vector.T).item())
            if score > best_score:
                best_score = score
                best_match = candidate
        if best_match and best_score >= 0.86:
            return best_match
    except Exception as exc:
        logger.debug("Feedback embedding dedupe unavailable: %s", exc)
    return None


def _find_semantic_duplicate(text: str, candidates: list[FeedbackEntry]) -> FeedbackEntry | None:
    simhash_duplicate = _find_duplicate_simhash(text, candidates)
    if simhash_duplicate:
        return simhash_duplicate

    best_match = None
    best_score = 0.0
    for candidate in candidates:
        score = _semantic_similarity(text, getattr(candidate, "text", "") or "")
        if score > best_score:
            best_score = score
            best_match = candidate
    if best_match and best_score >= SEMANTIC_DUPLICATE_THRESHOLD:
        return best_match
    return None


def _find_source_message_duplicate(source: str, source_message_id: str, candidates: list[FeedbackEntry]) -> FeedbackEntry | None:
    if not source_message_id:
        return None
    for candidate in candidates:
        if getattr(candidate, "source", "") == source and getattr(candidate, "source_message_id", "") == source_message_id:
            return candidate
    return None


def _serialize_duplicate(entry: FeedbackEntry) -> dict:
    payload = _serialize(entry)
    payload["deduped"] = True
    payload["duplicate_of_id"] = entry.id
    return payload


def _build_dedupe_summary(entries: list[object]) -> dict:
    grouped_ids: set[int] = set()
    groups: list[dict] = []
    fingerprints = [_simhash(getattr(entry, "text", "") or "") for entry in entries]
    token_features = [set(_simhash_tokens(getattr(entry, "text", "") or "")) for entry in entries]

    for index, entry in enumerate(entries):
        entry_id = getattr(entry, "id", index)
        if entry_id in grouped_ids:
            continue

        members = [entry]
        scores: list[float] = []
        entry_text = getattr(entry, "text", "") or ""
        for candidate_index, candidate in enumerate(entries[index + 1:], start=index + 1):
            candidate_id = getattr(candidate, "id", None)
            if candidate_id in grouped_ids:
                continue
            left_features = token_features[index]
            right_features = token_features[candidate_index]
            intersection = left_features & right_features
            overlap = (
                len(intersection) / min(len(left_features), len(right_features))
                if left_features and right_features
                else 0.0
            )
            distance = _hamming_distance(fingerprints[index], fingerprints[candidate_index])
            if distance > SIMHASH_HAMMING_THRESHOLD and overlap < 0.55:
                continue
            score = _semantic_similarity(entry_text, getattr(candidate, "text", "") or "")
            if score >= SEMANTIC_DUPLICATE_THRESHOLD:
                members.append(candidate)
                scores.append(score)

        if len(members) < 2:
            continue

        member_ids = [getattr(member, "id", None) for member in members]
        grouped_ids.update(member_id for member_id in member_ids if member_id is not None)
        groups.append({
            "canonical_id": member_ids[0],
            "canonical_text": getattr(members[0], "text", ""),
            "entry_ids": member_ids,
            "duplicate_ids": member_ids[1:],
            "average_similarity": round(sum(scores) / len(scores), 3) if scores else 1.0,
        })

    duplicate_candidates = sum(len(group["entry_ids"]) for group in groups)
    total_feedback = len(entries)
    return {
        "total_feedback": total_feedback,
        "duplicate_groups": len(groups),
        "duplicate_candidates": duplicate_candidates,
        "dedupe_rate": round(duplicate_candidates / total_feedback, 4) if total_feedback else 0,
        "groups": groups,
    }


def _themes_for_entry(entry: object) -> list[str]:
    return _parse_themes(getattr(entry, "themes_json", "") or "[]")


def _cluster_id_for_entry(entry: object) -> str:
    stored = getattr(entry, "cluster_slug", "") or ""
    if stored:
        return stored
    return _cluster_slug_for_analysis(getattr(entry, "text", "") or "", _themes_for_entry(entry))


def _cluster_priority(entries: list[object]) -> str:
    priorities = [getattr(entry, "priority", "") for entry in entries]
    if "urgent" in priorities or any(getattr(entry, "is_urgent", False) for entry in entries):
        return "urgent"
    if "high" in priorities or len(entries) >= 2 or any(getattr(entry, "sentiment", "") == "negative" for entry in entries):
        return "high"
    return "low"


def _build_cluster_payloads(entries: list[object]) -> list[dict]:
    grouped: dict[str, list[object]] = {}
    for entry in entries:
        grouped.setdefault(_cluster_id_for_entry(entry), []).append(entry)

    priority_rank = {"urgent": 0, "high": 1, "low": 2}
    payloads: list[dict] = []
    for cluster_id, members in grouped.items():
        sentiment_counts = Counter(getattr(member, "sentiment", "neutral") or "neutral" for member in members)
        source_counts = Counter(getattr(member, "source", "manual") or "manual" for member in members)
        themes = Counter(theme for member in members for theme in _themes_for_entry(member))
        priority = _cluster_priority(members)
        quotes = [
            {
                "id": getattr(member, "id", None),
                "text": getattr(member, "text", ""),
                "source": getattr(member, "source", "manual"),
                "author": getattr(member, "author", ""),
                "source_url": getattr(member, "source_url", ""),
            }
            for member in members[:5]
        ]
        last_seen = max(
            (_as_aware_utc(getattr(member, "created_at", None)) or _utc_now() for member in members),
            default=_utc_now(),
        )
        payloads.append({
            "id": cluster_id,
            "label": cluster_id.replace("-", " ").title(),
            "priority": priority,
            "mention_count": len(members),
            "last_activity": last_seen.isoformat() if hasattr(last_seen, "isoformat") else str(last_seen),
            "sample_quotes": quotes,
            "source_counts": dict(source_counts),
            "sentiment_counts": dict(sentiment_counts),
            "top_themes": [theme for theme, _count in themes.most_common(5)],
            "status": "active",
        })

    payloads.sort(key=lambda item: (priority_rank.get(item["priority"], 3), -item["mention_count"], item["id"]))
    return payloads


def _build_digest_payload(entries: list[object]) -> dict:
    clusters = _build_cluster_payloads(entries)
    urgent = [cluster for cluster in clusters if cluster["priority"] == "urgent"]
    high = [cluster for cluster in clusters if cluster["priority"] == "high"]
    low = [cluster for cluster in clusters if cluster["priority"] == "low"]
    return {
        "generated_at": _utc_now().isoformat(),
        "urgent": urgent,
        "high": high,
        "low": low,
        "summary": {
            "total_feedback": len(entries),
            "clusters_active": len(clusters),
            "urgent_clusters": len(urgent),
            "high_clusters": len(high),
            "low_clusters": len(low),
        },
    }


def _github_issue_body(cluster: dict) -> str:
    lines = [
        f"FeedbackLens cluster: {cluster['label']}",
        f"Priority: {cluster['priority']}",
        f"Mentions: {cluster['mention_count']}",
        "",
        "Representative feedback:",
    ]
    for quote in cluster["sample_quotes"][:5]:
        source = quote.get("source", "manual")
        author = quote.get("author", "")
        lines.append(f"- {quote.get('text', '')} ({source}{', ' + author if author else ''})")
        if quote.get("source_url"):
            lines.append(f"  Source: {quote['source_url']}")
    return "\n".join(lines)


def _github_issue_labels(cluster: dict, requested: list[str]) -> list[str]:
    labels = {"feedback-lens", *requested}
    if cluster["priority"] == "urgent":
        labels.add("bug")
    if any(term in cluster["id"] for term in ["checkout", "payment", "billing", "login", "crash", "export"]):
        labels.add("bug")
    if any(term in cluster["id"] for term in ["dark-mode", "mobile", "feature"]):
        labels.add("feature")
    return sorted(label for label in labels if label)


def _post_github_issue(repo: str, token: str, payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = url_request.Request(
        f"https://api.github.com/repos/{repo}/issues",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "DevForge-FeedbackLens",
        },
    )
    try:
        with url_request.urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8")
    except url_error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        raise HTTPException(status_code=502, detail=f"GitHub issue creation failed: {raw}") from exc
    return json.loads(raw) if raw else {}


async def _poll_twitter_source(source: FeedbackSource) -> list[dict]:
    config = _source_config(source)
    query = config.get("query") or source.handle or source.display_name
    access_token = decrypt_secret(source.access_token)
    if not access_token or not query:
        return []
    params = urlencode({"query": query, "max_results": 10, "tweet.fields": "author_id,created_at"})
    data = _http_json(
        f"https://api.twitter.com/2/tweets/search/recent?{params}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    items = []
    for tweet in data.get("data", []):
        tweet_id = str(tweet.get("id", ""))
        items.append({
            "text": tweet.get("text", ""),
            "author": str(tweet.get("author_id", "")),
            "source_url": f"https://x.com/i/web/status/{tweet_id}" if tweet_id else "",
            "source_message_id": tweet_id,
        })
    return items


async def _poll_reddit_source(source: FeedbackSource) -> list[dict]:
    config = _source_config(source)
    query = config.get("query") or source.handle or source.display_name
    subreddit = config.get("subreddit", "")
    access_token = decrypt_secret(source.access_token)
    if not access_token or not query:
        return []
    base = f"https://oauth.reddit.com/r/{subreddit}/search" if subreddit else "https://oauth.reddit.com/search"
    params = urlencode({"q": query, "sort": "new", "limit": 10, "restrict_sr": bool(subreddit)})
    data = _http_json(
        f"{base}?{params}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    items = []
    for child in data.get("data", {}).get("children", []):
        post = child.get("data", {})
        post_id = str(post.get("id", ""))
        text = _combine_feedback_text(post.get("title", ""), post.get("selftext", ""))
        items.append({
            "text": text,
            "author": post.get("author", ""),
            "source_url": f"https://reddit.com{post.get('permalink', '')}" if post.get("permalink") else "",
            "source_message_id": post_id,
        })
    return items


async def _poll_github_source(source: FeedbackSource) -> list[dict]:
    config = _source_config(source)
    repo = config.get("repo", "")
    access_token = decrypt_secret(source.access_token)
    if not access_token or not repo:
        return []
    params = urlencode({"state": "open", "per_page": 20})
    data = _http_json(
        f"https://api.github.com/repos/{repo}/issues?{params}",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
        },
    )
    if not isinstance(data, list):
        return []
    items = []
    for issue in data:
        if issue.get("pull_request"):
            continue
        issue_id = str(issue.get("id", ""))
        text = _combine_feedback_text(issue.get("title", ""), issue.get("body", ""))
        items.append({
            "text": text,
            "author": (issue.get("user") or {}).get("login", ""),
            "source_url": issue.get("html_url", ""),
            "source_message_id": issue_id,
        })
    return items


def _refresh_oauth_source(source: FeedbackSource) -> bool:
    refresh_token = decrypt_secret(source.refresh_token)
    if not refresh_token:
        return False

    if source.source_type == "twitter":
        client_id = _twitter_client_id()
        if not client_id:
            return False
        client_secret = _twitter_client_secret()
        token_payload = _http_form_json(
            "https://api.x.com/2/oauth2/token",
            payload={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
            },
            basic_auth=(client_id, client_secret) if client_secret else None,
        )
    elif source.source_type == "reddit":
        client_id = _reddit_client_id()
        client_secret = _reddit_client_secret()
        if not client_id or not client_secret:
            return False
        token_payload = _http_form_json(
            "https://www.reddit.com/api/v1/access_token",
            payload={"grant_type": "refresh_token", "refresh_token": refresh_token},
            basic_auth=(client_id, client_secret),
        )
    else:
        return False

    access_token = str(token_payload.get("access_token") or "").strip()
    if not access_token:
        return False
    source.access_token = encrypt_secret(access_token)
    rotated_refresh = str(token_payload.get("refresh_token") or "").strip()
    if rotated_refresh:
        source.refresh_token = encrypt_secret(rotated_refresh)
    source.updated_at = _utc_now()
    return True


async def _poll_source_feedback(source: FeedbackSource) -> list[dict]:
    if source.source_type == "twitter":
        return await _poll_twitter_source(source)
    if source.source_type == "reddit":
        return await _poll_reddit_source(source)
    if source.source_type == "github":
        return await _poll_github_source(source)
    return []


def _source_is_due(source: FeedbackSource, now: datetime | None = None) -> bool:
    frequency = _source_poll_frequency_hours(source.source_type)
    if frequency is None or source.status != "connected":
        return False
    if not source.access_token:
        return False
    if not source.last_polled_at:
        return True
    current = _as_aware_utc(now) or _utc_now()
    last_polled = _as_aware_utc(source.last_polled_at)
    if not last_polled:
        return True
    return last_polled <= current - timedelta(hours=frequency)


async def poll_feedback_sources() -> dict:
    async with get_managed_session() as session:
        result = await session.execute(
            select(FeedbackSource).where(
                FeedbackSource.status == "connected",
                FeedbackSource.source_type.in_(["twitter", "reddit", "github"]),
            )
        )
        sources = list(result.scalars().all())
        now = _utc_now()
        ingested = 0
        skipped_duplicates = 0
        failed: list[dict] = []
        for source in sources:
            if not _source_is_due(source, now):
                continue
            try:
                try:
                    items = await _poll_source_feedback(source)
                except SourceAuthorizationError:
                    refreshed = await _run_in_thread(_refresh_oauth_source, source)
                    if not refreshed:
                        raise
                    session.add(source)
                    await session.flush()
                    items = await _poll_source_feedback(source)
                for item in items:
                    try:
                        created = await _create_processed_feedback(
                            user_id=source.user_id,
                            text=item.get("text", ""),
                            source=source.source_type,
                            author=item.get("author", ""),
                            source_url=item.get("source_url", ""),
                            source_message_id=item.get("source_message_id", ""),
                            session=session,
                        )
                        if created.get("deduped"):
                            skipped_duplicates += 1
                        else:
                            ingested += 1
                    except SpamDetectedError:
                        continue
                    except HTTPException:
                        raise
                source.last_polled_at = now
                source.updated_at = now
                session.add(source)
            except Exception as exc:
                logger.warning("Feedback source polling failed for %s: %s", source.id, exc)
                failed.append({"source_id": source.id, "source_type": source.source_type, "error": str(exc)})
        await session.commit()
        return {
            "status": "success",
            "sources_checked": len(sources),
            "ingested": ingested,
            "duplicates_skipped": skipped_duplicates,
            "failed": failed,
        }


async def _load_dedupe_candidates(
    user_id: int,
    session: AsyncSession,
    *,
    text: str = "",
) -> list[FeedbackEntry]:
    query = select(FeedbackEntry).where(
        FeedbackEntry.user_id == user_id,
        FeedbackEntry.created_at >= _utc_now() - timedelta(days=DEDUPE_LOOKBACK_DAYS),
    )
    candidate_terms = sorted(_feedback_tokens(text), key=lambda term: (-len(term), term))[:4]
    if candidate_terms:
        query = query.where(or_(*(FeedbackEntry.text.ilike(f"%{term}%") for term in candidate_terms)))
    result = await session.execute(
        query.order_by(FeedbackEntry.created_at.desc()).limit(DEDUPE_LOOKBACK_LIMIT)
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
feedback_router = APIRouter(prefix="/feedback", tags=["feedback"], dependencies=[Depends(require_product_access("feedbacklens"))])
settings_router = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(require_product_access("feedbacklens"))])
sources_router = APIRouter(prefix="/sources", tags=["sources"], dependencies=[Depends(require_product_access("feedbacklens"))])
clusters_router = APIRouter(prefix="/clusters", tags=["clusters"], dependencies=[Depends(require_product_access("feedbacklens"))])
connect_router = APIRouter(prefix="/connect", tags=["connectors"], dependencies=[Depends(require_product_access("feedbacklens"))])
digest_router = APIRouter(tags=["digest"], dependencies=[Depends(require_product_access("feedbacklens"))])
cron_router = APIRouter(prefix="/feedback", tags=["cron"])
public_ingest_router = APIRouter(prefix="/feedback", tags=["ingest"])


@settings_router.get("/feedback-prefs")
async def get_feedback_prefs(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(FeedbackSettings).where(FeedbackSettings.user_id == user.id))
    prefs = result.scalar_one_or_none()
    if not prefs:
        prefs = FeedbackSettings(user_id=user.id)
        session.add(prefs)
        await session.flush()
    return {
        "custom_prompt": prefs.custom_prompt,
        "negative_threshold": prefs.negative_threshold,
        "alert_email": prefs.alert_email,
        "weekly_summary_enabled": prefs.weekly_summary_enabled,
        "timezone": prefs.timezone,
        "last_weekly_digest_at": prefs.last_weekly_digest_at.isoformat() if prefs.last_weekly_digest_at else None,
    }


@settings_router.put("/feedback-prefs")
async def update_feedback_prefs(body: FeedbackPrefsUpdate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(FeedbackSettings).where(FeedbackSettings.user_id == user.id))
    prefs = result.scalar_one_or_none()
    if not prefs:
        prefs = FeedbackSettings(user_id=user.id)
    prefs.custom_prompt = body.custom_prompt
    prefs.negative_threshold = body.negative_threshold
    prefs.alert_email = str(body.alert_email or "")
    prefs.weekly_summary_enabled = body.weekly_summary_enabled
    prefs.timezone = body.timezone or "UTC"
    session.add(prefs)
    await session.flush()
    return {"ok": True}


def _serialize_source(source: FeedbackSource) -> dict:
    config = _source_config(source)
    created_at = _as_aware_utc(source.created_at) or _utc_now()
    updated_at = _as_aware_utc(source.updated_at) or created_at
    last_polled_at = _as_aware_utc(source.last_polled_at)
    payload = {
        "id": source.id,
        "source_type": source.source_type,
        "display_name": source.display_name,
        "handle": source.handle,
        "status": source.status,
        "poll_frequency_hours": _source_poll_frequency_hours(source.source_type),
        "config": config,
        "created_at": created_at.isoformat(),
        "updated_at": updated_at.isoformat(),
        "last_polled_at": last_polled_at.isoformat() if last_polled_at else None,
    }
    if source.source_type == "email":
        payload["forward_address"] = f"feedback-{source.forward_token}@feedbacklens.devforgeapp.pro"
    if source.source_type == "canny":
        payload["webhook_path"] = "/feedback/ingest/canny"
    return payload


@sources_router.get("")
async def list_sources(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(FeedbackSource)
        .where(FeedbackSource.user_id == user.id, FeedbackSource.status != "deleted")
        .order_by(FeedbackSource.created_at.desc())
    )
    return [_serialize_source(source) for source in result.scalars().all()]


@sources_router.post("")
async def create_source(body: FeedbackSourceCreate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    await _enforce_source_limit(user, body.source_type, session)
    config = dict(body.config or {})
    if body.repo:
        config["repo"] = body.repo
    if body.handle:
        config["handle"] = body.handle
    source = FeedbackSource(
        user_id=user.id,
        source_type=body.source_type,
        display_name=body.display_name or body.handle or body.repo or body.source_type.title(),
        handle=body.handle,
        access_token=encrypt_secret(body.access_token),
        refresh_token=encrypt_secret(body.refresh_token),
        webhook_secret=encrypt_secret(body.webhook_secret),
        config_json=json.dumps(config),
        status="connected" if body.source_type in {"email", "manual", "canny"} or body.access_token else "needs_auth",
    )
    session.add(source)
    await session.flush()
    await session.refresh(source)
    return _serialize_source(source)


@sources_router.delete("/{source_id}")
async def delete_source(source_id: int, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(FeedbackSource).where(FeedbackSource.id == source_id, FeedbackSource.user_id == user.id)
    )
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Feedback source not found")

    source.status = "deleted"
    source.access_token = ""
    source.refresh_token = ""
    source.webhook_secret = ""
    source.updated_at = _utc_now()
    session.add(source)
    await session.flush()
    payload = _serialize_source(source)
    payload["feedback_retention"] = "kept"
    return payload


async def _create_processed_feedback(
    *,
    user_id: int,
    text: str,
    source: str,
    author: str = "",
    source_url: str = "",
    source_message_id: str = "",
    session: AsyncSession,
    candidates: list[FeedbackEntry] | None = None,
) -> dict:
    cleaned = _clean_feedback_text(text)
    if not cleaned:
        raise HTTPException(status_code=400, detail="Feedback text is required")

    candidate_pool = candidates
    if source_message_id:
        exact_result = await session.execute(
            select(FeedbackEntry).where(
                FeedbackEntry.user_id == user_id,
                FeedbackEntry.source == source,
                FeedbackEntry.source_message_id == source_message_id,
            ).limit(1)
        )
        external_duplicate = exact_result.scalar_one_or_none()
    else:
        external_duplicate = None
    if external_duplicate:
        return _serialize_duplicate(external_duplicate)
    if candidate_pool is None:
        candidate_pool = await _load_dedupe_candidates(user_id, session, text=cleaned)
    duplicate = _find_semantic_duplicate(cleaned, candidate_pool)
    if duplicate:
        return _serialize_duplicate(duplicate)

    entry = FeedbackEntry(
        user_id=user_id,
        text=cleaned,
        source=source,
        author=author,
        source_url=source_url,
        source_message_id=source_message_id,
    )
    await _apply_local_processing_async(entry)
    session.add(entry)
    try:
        await session.flush()
    except IntegrityError as exc:
        if hasattr(session, "rollback"):
            await session.rollback()
        raise HTTPException(status_code=409, detail="Duplicate source message") from exc
    await session.refresh(entry)
    await _queue_urgent_feedback_alert(entry, session)
    candidate_pool.append(entry)
    return _serialize(entry)


def _entry_from_payload(payload: dict, user_id: int) -> FeedbackEntry:
    if not isinstance(payload, dict):
        raise ValueError("Feedback payload must be an object")
    text = payload.get("text", "")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Feedback payload text is required")
    themes = payload.get("themes", [])
    if not isinstance(themes, list):
        themes = []

    def _safe_str(value: Any, default: str = "") -> str:
        if value is None:
            return default
        if isinstance(value, (str, int, float, bool)):
            return str(value)
        return default

    entry_id = payload.get("id")
    if entry_id is not None and not isinstance(entry_id, int):
        raise ValueError("Feedback payload id must be an integer")
    return FeedbackEntry(
        id=entry_id,
        user_id=user_id,
        text=_clean_feedback_text(text),
        sentiment=_safe_str(payload.get("sentiment")) or None,
        confidence=payload.get("confidence") if isinstance(payload.get("confidence"), (int, float)) else None,
        themes_json=json.dumps([_safe_str(theme) for theme in themes if _safe_str(theme)]),
        is_urgent=bool(payload.get("is_urgent")),
        source=_safe_str(payload.get("source"), "manual") or "manual",
        author=_safe_str(payload.get("author")),
        source_url=_safe_str(payload.get("source_url")),
        source_message_id=_safe_str(payload.get("source_message_id")),
        cluster_slug=_safe_str(payload.get("cluster_slug")),
        priority=_safe_str(payload.get("priority"), "low") or "low",
    )


async def _queue_urgent_feedback_alert(entry: FeedbackEntry, session: AsyncSession) -> None:
    if not entry.is_urgent:
        return
    prefs_result = await session.execute(select(FeedbackSettings).where(FeedbackSettings.user_id == entry.user_id))
    prefs = prefs_result.scalar_one_or_none()
    alert_email = getattr(prefs, "alert_email", "") if prefs else ""
    if not alert_email:
        return
    preview = html.escape(entry.text[:500], quote=True)
    source = html.escape(entry.source or "manual", quote=True)
    author = html.escape(entry.author or "Unknown", quote=True)
    cluster = html.escape(entry.cluster_slug or "review needed", quote=True)
    session.add(SystemOutbox(
        app_name="feedbacklens",
        job_type="send_email",
        payload={
            "to": alert_email,
            "subject": f"Urgent feedback detected: {entry.cluster_slug or 'review needed'}",
            "html_body": (
                "<div style=\"font-family:sans-serif;max-width:640px;margin:0 auto;\">"
                "<h2>Urgent feedback detected</h2>"
                f"<p><strong>Cluster:</strong> {cluster}</p>"
                f"<p><strong>Source:</strong> {source}</p>"
                f"<p><strong>Author:</strong> {author}</p>"
                f"<p>{preview}</p>"
                "</div>"
            ),
        },
        priority=2,
    ))


@feedback_router.post("")
async def create_feedback(body: FeedbackCreate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    await _enforce_feedback_limit(user, 1, session)
    return await _create_processed_feedback(user_id=user.id, text=body.text, source="manual", session=session)


@feedback_router.post("/ingest/email")
async def ingest_email_feedback(body: EmailIngestRequest, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    await _enforce_feedback_limit(user, 1, session)
    text = _combine_email_feedback_text(body)
    return await _create_processed_feedback(
        user_id=user.id,
        text=text,
        source="email",
        author=body.from_email,
        source_url=body.source_url,
        source_message_id=body.message_id,
        session=session,
    )


@feedback_router.post("/ingest/canny")
async def ingest_canny_feedback(body: CannyIngestRequest, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    await _enforce_feedback_limit(user, 1, session)
    text = _combine_feedback_text(body.title, body.body)
    return await _create_processed_feedback(
        user_id=user.id,
        text=text,
        source="canny",
        author=body.author,
        source_url=body.url,
        source_message_id=body.post_id,
        session=session,
    )


def _verify_github_signature(secret: str, raw_body: bytes, signature_header: str | None) -> None:
    if not secret:
        raise HTTPException(status_code=401, detail="GitHub webhook secret is required")
    if not signature_header or not signature_header.startswith("sha256="):
        raise HTTPException(status_code=401, detail="Missing GitHub signature")
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    received = signature_header.split("=", 1)[1]
    if not hmac.compare_digest(expected, received):
        raise HTTPException(status_code=401, detail="Invalid GitHub signature")


@public_ingest_router.post("/ingest/github")
async def ingest_github_issue_webhook(
    request: Request,
    source_id: int = Query(...),
    session: AsyncSession = Depends(get_session),
):
    source_result = await session.execute(
        select(FeedbackSource).where(FeedbackSource.id == source_id, FeedbackSource.status != "deleted")
    )
    source = source_result.scalar_one_or_none()
    if not source or source.source_type != "github":
        raise HTTPException(status_code=404, detail="GitHub source not found")

    raw_body = await request.body()
    _verify_github_signature(decrypt_secret(source.webhook_secret), raw_body, request.headers.get("x-hub-signature-256"))
    await _enforce_public_webhook_rate_limit(source_id, session)
    try:
        payload = GitHubWebhookPayload.model_validate_json(raw_body)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail="Invalid GitHub webhook payload") from exc
    action = payload.action
    issue = payload.issue
    if action not in {"opened", "edited", "reopened"} or not issue:
        return {"status": "ignored", "action": action}
    text = _combine_feedback_text(issue.title, issue.body)
    return await _create_processed_feedback(
        user_id=source.user_id,
        text=text,
        source="github",
        author=issue.user.login,
        source_url=issue.html_url,
        source_message_id=str(issue.id),
        session=session,
    )


async def _list_feedback_payload(
    priority: str,
    source: str,
    user: User,
    session: AsyncSession,
    *,
    limit: int,
    cursor: str,
) -> tuple[list[dict], str]:
    query = select(FeedbackEntry).where(FeedbackEntry.user_id == user.id)
    if priority:
        query = query.where(FeedbackEntry.priority == priority)
    if source:
        query = query.where(FeedbackEntry.source == source)
    if cursor:
        try:
            cursor_at, cursor_id = _decode_feedback_cursor(cursor)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        query = query.where(tuple_(FeedbackEntry.created_at, FeedbackEntry.id) < (cursor_at, cursor_id))
    result = await session.execute(
        query.order_by(FeedbackEntry.created_at.desc(), FeedbackEntry.id.desc()).limit(limit + 1)
    )
    entries = list(result.scalars().all())
    has_more = len(entries) > limit
    page = entries[:limit]
    next_cursor = ""
    if has_more and page:
        last = page[-1]
        next_cursor = _encode_feedback_cursor(last.created_at, last.id)
    return [_serialize(entry) for entry in page], next_cursor


@feedback_router.get("")
async def list_feedback_root(
    response: Response,
    priority: str = Query(default=""),
    source: str = Query(default=""),
    limit: int = Query(default=100, ge=1, le=200),
    cursor: str = Query(default=""),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    items, next_cursor = await _list_feedback_payload(
        priority, source, user, session, limit=limit, cursor=cursor
    )
    if next_cursor:
        response.headers["X-Next-Cursor"] = next_cursor
    return items


@feedback_router.get("/list")
async def list_feedback(
    response: Response,
    priority: str = Query(default=""),
    source: str = Query(default=""),
    limit: int = Query(default=100, ge=1, le=200),
    cursor: str = Query(default=""),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    items, next_cursor = await _list_feedback_payload(
        priority, source, user, session, limit=limit, cursor=cursor
    )
    if next_cursor:
        response.headers["X-Next-Cursor"] = next_cursor
    return items


@feedback_router.get("/dedupe/summary")
async def get_dedupe_summary(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(FeedbackEntry)
        .where(FeedbackEntry.user_id == user.id)
        .order_by(FeedbackEntry.created_at.desc())
        .limit(DEDUPE_LOOKBACK_LIMIT)
    )
    return _build_dedupe_summary(list(result.scalars().all()))


@feedback_router.delete("/{entry_id}")
async def delete_feedback(
    entry_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(FeedbackEntry).where(FeedbackEntry.id == entry_id, FeedbackEntry.user_id == user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Feedback not found")
    await session.execute(
        delete(FeedbackEntry).where(FeedbackEntry.id == entry_id, FeedbackEntry.user_id == user.id)
    )
    await session.commit()
    return {"status": "deleted", "feedback_id": entry_id}


@clusters_router.get("")
async def list_clusters(
    days: int = Query(default=30, ge=1, le=365),
    priority: str = Query(default=""),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    since = _utc_now() - timedelta(days=days)
    result = await session.execute(
        select(FeedbackEntry)
        .where(FeedbackEntry.user_id == user.id, FeedbackEntry.created_at >= since)
        .order_by(FeedbackEntry.created_at.desc())
        .limit(1000)
    )
    clusters = _build_cluster_payloads(list(result.scalars().all()))
    if priority:
        clusters = [cluster for cluster in clusters if cluster["priority"] == priority]
    return {"clusters": clusters, "total": len(clusters), "days": days}


@clusters_router.get("/{cluster_id}")
async def get_cluster_detail(cluster_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(FeedbackEntry)
        .where(
            FeedbackEntry.user_id == user.id,
            FeedbackEntry.cluster_slug == cluster_id,
        )
        .order_by(FeedbackEntry.created_at.desc())
        .limit(1000)
    )
    clusters = _build_cluster_payloads(list(result.scalars().all()))
    if clusters:
        return clusters[0]
    raise HTTPException(status_code=404, detail="Cluster not found")


@clusters_router.post("/{cluster_id}/github-issue")
async def create_cluster_github_issue(
    cluster_id: str,
    body: GitHubIssueRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(FeedbackEntry)
        .where(
            FeedbackEntry.user_id == user.id,
            FeedbackEntry.cluster_slug == cluster_id,
        )
        .order_by(FeedbackEntry.created_at.desc())
        .limit(1000)
    )
    clusters = _build_cluster_payloads(list(result.scalars().all()))
    cluster = next((item for item in clusters if item["id"] == cluster_id), None)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    source_result = await session.execute(
        select(FeedbackSource).where(
            FeedbackSource.user_id == user.id,
            FeedbackSource.source_type == "github",
            FeedbackSource.status == "connected",
        )
    )
    source = source_result.scalar_one_or_none()
    source_config = _source_config(source) if source else {}
    repo = body.repo or source_config.get("repo", "")
    token = decrypt_secret(getattr(source, "access_token", "")) if source else ""
    if not repo or not token:
        raise HTTPException(status_code=400, detail="Connect GitHub with a repo and read/write issue token first.")

    issue_payload = {
        "title": f"FeedbackLens: {cluster['label']} ({cluster['mention_count']} mentions)",
        "body": _github_issue_body(cluster),
        "labels": _github_issue_labels(cluster, body.labels),
    }
    created = _post_github_issue(repo, token, issue_payload)
    return {
        "cluster_id": cluster_id,
        "issue_url": created.get("html_url", ""),
        "issue_number": created.get("number"),
        "payload": issue_payload,
    }


@digest_router.get("/feedbacklens/digest")
async def get_digest(days: int = Query(default=7, ge=1, le=90), user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    since = _utc_now() - timedelta(days=days)
    result = await session.execute(
        select(FeedbackEntry)
        .where(FeedbackEntry.user_id == user.id, FeedbackEntry.created_at >= since)
        .order_by(FeedbackEntry.created_at.desc())
        .limit(1000)
    )
    payload = _build_digest_payload(list(result.scalars().all()))
    payload["days"] = days
    return payload


def _twitter_client_id() -> str:
    return os.getenv("FEEDBACKLENS_TWITTER_CLIENT_ID") or os.getenv("FEEDBACKLENS_X_CLIENT_ID", "")


def _twitter_client_secret() -> str:
    return os.getenv("FEEDBACKLENS_TWITTER_CLIENT_SECRET") or os.getenv("FEEDBACKLENS_X_CLIENT_SECRET", "")


def _reddit_client_id() -> str:
    return os.getenv("FEEDBACKLENS_REDDIT_CLIENT_ID", "")


def _reddit_client_secret() -> str:
    return os.getenv("FEEDBACKLENS_REDDIT_CLIENT_SECRET", "")


@connect_router.post("/twitter")
async def connect_twitter(body: TwitterConnectRequest, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    await _enforce_source_limit(user, "twitter", session)
    client_id = _twitter_client_id()
    redirect_uri = body.redirect_uri or os.getenv("FEEDBACKLENS_TWITTER_REDIRECT_URI", "")
    if not client_id or not redirect_uri:
        raise HTTPException(status_code=503, detail="Twitter/X OAuth client is not configured.")
    state = uuid.uuid4().hex
    code_verifier, code_challenge = _pkce_pair()
    query = body.query or body.handle
    config = {
        "query": query,
        "handle": body.handle,
        "oauth_state": state,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
    }
    source = FeedbackSource(
        user_id=user.id,
        source_type="twitter",
        display_name=body.handle or "Twitter/X",
        handle=body.handle,
        status="pending_oauth",
        config_json=json.dumps(config),
    )
    session.add(source)
    await session.flush()
    params = urlencode({
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "tweet.read users.read offline.access",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    })
    return {
        "authorization_url": f"https://x.com/i/oauth2/authorize?{params}",
        "state": state,
        "source_id": source.id,
    }


@connect_router.post("/reddit")
async def connect_reddit(body: RedditConnectRequest, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    await _enforce_source_limit(user, "reddit", session)
    client_id = _reddit_client_id()
    redirect_uri = body.redirect_uri or os.getenv("FEEDBACKLENS_REDDIT_REDIRECT_URI", "")
    if not client_id or not redirect_uri:
        raise HTTPException(status_code=503, detail="Reddit OAuth client is not configured.")
    state = uuid.uuid4().hex
    query = body.query or body.subreddit
    config = {
        "query": query,
        "subreddit": body.subreddit,
        "oauth_state": state,
        "redirect_uri": redirect_uri,
    }
    source = FeedbackSource(
        user_id=user.id,
        source_type="reddit",
        display_name=body.subreddit or "Reddit",
        handle=body.subreddit,
        status="pending_oauth",
        config_json=json.dumps(config),
    )
    session.add(source)
    await session.flush()
    params = urlencode({
        "client_id": client_id,
        "response_type": "code",
        "state": state,
        "redirect_uri": redirect_uri,
        "duration": "permanent",
        "scope": "read",
    })
    return {
        "authorization_url": f"https://www.reddit.com/api/v1/authorize?{params}",
        "state": state,
        "source_id": source.id,
    }


@connect_router.post("/github")
async def connect_github(body: GitHubConnectRequest, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    await _enforce_source_limit(user, "github", session)
    client_id = os.getenv("FEEDBACKLENS_GITHUB_CLIENT_ID") or os.getenv("GITHUB_CLIENT_ID")
    redirect_uri = body.redirect_uri or os.getenv("FEEDBACKLENS_GITHUB_REDIRECT_URI", "")
    if not client_id:
        raise HTTPException(status_code=503, detail="GitHub OAuth client is not configured.")
    state = uuid.uuid4().hex
    config = {"repo": body.repo, "oauth_state": state, "redirect_uri": redirect_uri}
    source = FeedbackSource(
        user_id=user.id,
        source_type="github",
        display_name="GitHub Issues",
        status="pending_oauth",
        config_json=json.dumps(config),
    )
    session.add(source)
    await session.flush()
    scope = "repo"
    redirect_param = f"&redirect_uri={redirect_uri}" if redirect_uri else ""
    auth_url = f"https://github.com/login/oauth/authorize?client_id={client_id}&scope={scope}&state={state}{redirect_param}"
    return {"authorization_url": auth_url, "state": state, "source_id": source.id}


def _exchange_oauth_code(provider: str, code: str, redirect_uri: str = "", code_verifier: str = "") -> dict:
    if provider == "github":
        client_id = os.getenv("FEEDBACKLENS_GITHUB_CLIENT_ID") or os.getenv("GITHUB_CLIENT_ID", "")
        client_secret = os.getenv("FEEDBACKLENS_GITHUB_CLIENT_SECRET") or os.getenv("GITHUB_CLIENT_SECRET", "")
        if not client_id or not client_secret:
            raise HTTPException(status_code=503, detail="GitHub OAuth client is not configured.")
        payload = {"client_id": client_id, "client_secret": client_secret, "code": code}
        if redirect_uri:
            payload["redirect_uri"] = redirect_uri
        return _http_form_json("https://github.com/login/oauth/access_token", payload=payload)

    if provider == "twitter":
        client_id = _twitter_client_id()
        if not client_id or not redirect_uri or not code_verifier:
            raise HTTPException(status_code=503, detail="Twitter/X OAuth client is not configured.")
        payload = {
            "grant_type": "authorization_code",
            "client_id": client_id,
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        }
        secret = _twitter_client_secret()
        return _http_form_json(
            "https://api.x.com/2/oauth2/token",
            payload=payload,
            basic_auth=(client_id, secret) if secret else None,
        )

    if provider == "reddit":
        client_id = _reddit_client_id()
        client_secret = _reddit_client_secret()
        if not client_id or not client_secret or not redirect_uri:
            raise HTTPException(status_code=503, detail="Reddit OAuth client is not configured.")
        return _http_form_json(
            "https://www.reddit.com/api/v1/access_token",
            payload={"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri},
            basic_auth=(client_id, client_secret),
        )

    raise HTTPException(status_code=400, detail="Unsupported OAuth provider")


async def _complete_oauth_callback(
    provider: Literal["github", "twitter", "reddit"],
    state: str,
    code: str,
    user: User,
    session: AsyncSession,
) -> dict:
    result = await session.execute(
        select(FeedbackSource).where(
            FeedbackSource.user_id == user.id,
            FeedbackSource.source_type == provider,
            FeedbackSource.status == "pending_oauth",
        )
    )
    sources = list(result.scalars().all())
    source = None
    config: dict[str, Any] = {}
    for candidate in sources:
        candidate_config = _source_config(candidate)
        if candidate_config.get("oauth_state") == state:
            source = candidate
            config = candidate_config
            break
    if not source:
        raise HTTPException(status_code=400, detail=f"Invalid {provider} OAuth state.")

    token_payload = _exchange_oauth_code(
        provider,
        code,
        config.get("redirect_uri", ""),
        config.get("code_verifier", ""),
    )
    access_token = token_payload.get("access_token", "")
    if not access_token:
        raise HTTPException(status_code=502, detail=f"{provider.title()} OAuth did not return an access token.")
    source.access_token = encrypt_secret(access_token)
    source.refresh_token = encrypt_secret(token_payload.get("refresh_token", ""))
    source.status = "connected"
    source.updated_at = _utc_now()
    session.add(source)
    await session.flush()
    return {"status": "connected", "source_id": source.id, "source_type": provider, "config": config}


@connect_router.get("/github/callback")
async def connect_github_callback(
    state: str,
    code: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    payload = await _complete_oauth_callback("github", state, code, user, session)
    return {"status": payload["status"], "source_id": payload["source_id"], "repo": payload["config"].get("repo", "")}


@connect_router.get("/twitter/callback")
async def connect_twitter_callback(
    state: str,
    code: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    payload = await _complete_oauth_callback("twitter", state, code, user, session)
    return {"status": payload["status"], "source_id": payload["source_id"], "query": payload["config"].get("query", "")}


@connect_router.get("/reddit/callback")
async def connect_reddit_callback(
    state: str,
    code: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    payload = await _complete_oauth_callback("reddit", state, code, user, session)
    return {"status": payload["status"], "source_id": payload["source_id"], "query": payload["config"].get("query", "")}


@feedback_router.post("/{entry_id}/analyze")
async def analyze_feedback(entry_id: int, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    """
    Runs local feedback analysis. Users never need to provide a provider key.
    """
    result = await session.execute(
        select(FeedbackEntry).where(FeedbackEntry.id == entry_id, FeedbackEntry.user_id == user.id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Not found")

    prefs_result = await session.execute(select(FeedbackSettings).where(FeedbackSettings.user_id == user.id))
    prefs = prefs_result.scalar_one_or_none()
    await _apply_local_processing_async(entry, getattr(prefs, "custom_prompt", ""))
    session.add(entry)
    await session.commit()
    await session.refresh(entry)

    return _serialize(entry)


async def process_feedback_analysis(payload: dict):
    entry_id = payload.get("entry_id")
    user_id = payload.get("user_id")
    
    if not entry_id or not user_id:
        raise ValueError("Missing entry_id or user_id in payload")
        
    async with get_managed_session() as session:
        result = await session.execute(
            select(FeedbackEntry).where(FeedbackEntry.id == entry_id, FeedbackEntry.user_id == user_id)
        )
        entry = result.scalar_one_or_none()
        if not entry:
            return {"status": "skipped", "reason": "entry not found"}

        # Fetch user's local analysis focus terms.
        s_res = await session.execute(select(FeedbackSettings).where(FeedbackSettings.user_id == user_id))
        prefs = s_res.scalar_one_or_none()
        custom_prompt = getattr(prefs, "custom_prompt", "")

        analysis = await _apply_local_processing_async(entry, custom_prompt)

        session.add(entry)
        await session.commit()
        
    return {"status": "success", "entry_id": entry_id, "engine": analysis["engine"]}

# Register the handler
register_job_handler("feedbacklens", "analyze_feedback", process_feedback_analysis)


async def handle_feedback_email(payload: dict):
    await _run_in_thread(
        send_email,
        to=payload["to"],
        subject=payload["subject"],
        html_body=payload["html_body"],
    )
    return {"status": "sent", "to": payload["to"]}


register_job_handler("feedbacklens", "send_email", handle_feedback_email)


@feedback_router.get("/summary/weekly")
async def get_weekly_summary(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    """Returns a structured weekly digest for the dashboard."""
    now = _utc_now()
    one_week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)
    result = await session.execute(
        select(FeedbackEntry).where(
            FeedbackEntry.user_id == user.id,
            FeedbackEntry.created_at >= one_week_ago,
        )
    )
    entries = result.scalars().all()
    previous_result = await session.execute(
        select(FeedbackEntry).where(
            FeedbackEntry.user_id == user.id,
            FeedbackEntry.created_at >= two_weeks_ago,
            FeedbackEntry.created_at < one_week_ago,
        )
    )
    previous_entries = previous_result.scalars().all()

    previous_negative = sum(1 for e in previous_entries if e.sentiment == "negative")
    previous_urgent = sum(1 for e in previous_entries if e.is_urgent)

    def trend_payload(current_negative: int, current_urgent: int) -> dict:
        return {
            "previous_total": len(previous_entries),
            "total_delta": len(entries) - len(previous_entries),
            "previous_negative": previous_negative,
            "negative_delta": current_negative - previous_negative,
            "previous_urgent": previous_urgent,
            "urgent_delta": current_urgent - previous_urgent,
        }

    if not entries:
        return {
            "summary_text": "No feedback received this week.",
            "total": 0,
            "generated_at": _utc_now().isoformat(),
            "sentiment_stats": {"positive": 0, "negative": 0, "neutral": 0},
            "top_themes": [],
            "urgent_count": 0,
            "trend": trend_payload(0, 0),
        }

    all_themes: list[str] = []
    sentiments = {"positive": 0, "negative": 0, "neutral": 0}
    urgent_count = 0

    for e in entries:
        if e.themes_json:
            try:
                all_themes.extend(json.loads(e.themes_json))
            except Exception:
                pass
        if e.sentiment in sentiments:
            sentiments[e.sentiment] += 1
        if e.is_urgent:
            urgent_count += 1

    top_themes = [t for t, _ in Counter(all_themes).most_common(5)]

    summary = f"You received {len(entries)} feedback items this week. "
    if sentiments["negative"] > 0:
        summary += f"{sentiments['negative']} negative and "
    summary += f"{sentiments['positive']} positive reviews. "
    if urgent_count > 0:
        summary += f"⚠️ {urgent_count} items flagged as urgent."
    if top_themes:
        summary += f" Top topics: {', '.join(top_themes)}."

    return {
        "summary_text": summary,
        "total": len(entries),
        "generated_at": _utc_now().isoformat(),
        "sentiment_stats": sentiments,
        "top_themes": top_themes,
        "urgent_count": urgent_count,
        "trend": trend_payload(sentiments["negative"], urgent_count),
    }


def _aware_utc(now: datetime | None = None) -> datetime:
    current = now or _utc_now()
    if current.tzinfo is None:
        return current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc)


def _user_timezone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name or "UTC")
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _should_send_weekly_digest(prefs: FeedbackSettings, now: datetime | None = None) -> bool:
    current_utc = _aware_utc(now)
    local_now = current_utc.astimezone(_user_timezone(getattr(prefs, "timezone", "UTC")))
    if local_now.weekday() != 0 or local_now.hour != 9:
        return False

    last_sent = getattr(prefs, "last_weekly_digest_at", None)
    if last_sent:
        last_local = _aware_utc(last_sent).astimezone(local_now.tzinfo)
        if last_local.date() == local_now.date():
            return False
    return True


async def weekly_summary_cron(now: datetime | None = None):
    """Cron: sends weekly digest emails to all users who enabled it."""
    current_utc = _aware_utc(now)
    async with get_managed_session() as session:
        prefs_result = await session.execute(
            select(FeedbackSettings).where(FeedbackSettings.weekly_summary_enabled == True)  # noqa: E712
        )
        all_prefs = prefs_result.scalars().all()

        one_week_ago = current_utc - timedelta(days=7)

        for prefs in all_prefs:
            if not prefs.alert_email:
                continue
            if not _should_send_weekly_digest(prefs, current_utc):
                continue

            entries_result = await session.execute(
                select(FeedbackEntry).where(
                    FeedbackEntry.user_id == prefs.user_id,
                    FeedbackEntry.created_at >= one_week_ago,
                )
            )
            entries = entries_result.scalars().all()
            if not entries:
                continue

            sentiments = {"positive": 0, "negative": 0, "neutral": 0}
            urgent_count = 0
            for e in entries:
                if e.sentiment in sentiments:
                    sentiments[e.sentiment] += 1
                if e.is_urgent:
                    urgent_count += 1

            html = f"""
            <div style="font-family:sans-serif;max-width:600px;margin:0 auto;">
              <h2 style="color:#6366f1;">📊 Weekly Feedback Digest</h2>
              <p>Here's your summary for the past 7 days:</p>
              <table style="width:100%;border-collapse:collapse;">
                <tr><td style="padding:8px;border:1px solid #eee;">Total Feedback</td><td style="padding:8px;border:1px solid #eee;"><strong>{len(entries)}</strong></td></tr>
                <tr><td style="padding:8px;border:1px solid #eee;">✅ Positive</td><td style="padding:8px;border:1px solid #eee;"><strong>{sentiments['positive']}</strong></td></tr>
                <tr><td style="padding:8px;border:1px solid #eee;">❌ Negative</td><td style="padding:8px;border:1px solid #eee;"><strong>{sentiments['negative']}</strong></td></tr>
                <tr><td style="padding:8px;border:1px solid #eee;">⚠️ Urgent</td><td style="padding:8px;border:1px solid #eee;"><strong>{urgent_count}</strong></td></tr>
              </table>
              <p style="margin-top:20px;color:#666;">Log in to FeedbackLens to see the full report.</p>
            </div>
            """
            try:
                send_email(to=prefs.alert_email, subject="📊 Your Weekly Feedback Digest", html_body=html)
                prefs.last_weekly_digest_at = current_utc
                session.add(prefs)
            except Exception as e:
                logger.error(f"Failed to send weekly digest to {prefs.alert_email}: {e}")


@cron_router.post("/cron/summary", tags=["cron"])
async def cron_feedback_summary(authorization: str | None = Header(default=None)):
    """cron-job.org endpoint — sends weekly digest emails."""
    expected = os.getenv("CRON_SECRET")
    if expected and authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    await weekly_summary_cron()
    return {"status": "success", "task": "weekly_summary"}


@cron_router.post("/cron/poll", tags=["cron"])
async def cron_poll_feedback_sources(authorization: str | None = Header(default=None)):
    expected = os.getenv("CRON_SECRET")
    if expected and authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    return await poll_feedback_sources()


# ---------------------------------------------------------------------------
# Export endpoint — Skill: backend-architect + react-patterns
# ---------------------------------------------------------------------------
EXPORT_COLUMNS = [
    "id", "text", "sentiment", "confidence", "themes", "is_urgent",
    "draft_reply", "analysis_engine", "created_at",
]


def _export_row(entry: FeedbackEntry) -> dict[str, Any]:
    created_at = _as_aware_utc(entry.created_at) or _utc_now()
    return {
        "id": entry.id,
        "text": entry.text,
        "sentiment": entry.sentiment or "",
        "confidence": round(entry.confidence * 100, 1) if entry.confidence is not None else None,
        "themes": ", ".join(_parse_themes(entry.themes_json)),
        "is_urgent": entry.is_urgent,
        "draft_reply": entry.draft_reply or "",
        "analysis_engine": entry.analysis_engine or "",
        "created_at": created_at.isoformat(),
    }


async def _iter_export_batches(user_id: int, session: AsyncSession):
    cursor_at: datetime | None = None
    cursor_id: int | None = None
    while True:
        query = select(FeedbackEntry).where(FeedbackEntry.user_id == user_id)
        if cursor_at is not None and cursor_id is not None:
            query = query.where(tuple_(FeedbackEntry.created_at, FeedbackEntry.id) < (cursor_at, cursor_id))
        result = await session.execute(
            query.order_by(FeedbackEntry.created_at.desc(), FeedbackEntry.id.desc()).limit(EXPORT_BATCH_SIZE)
        )
        batch = list(result.scalars().all())
        if not batch:
            break
        yield batch
        last = batch[-1]
        cursor_at = _as_aware_utc(last.created_at) or _utc_now()
        cursor_id = int(last.id)
        if len(batch) < EXPORT_BATCH_SIZE:
            break


async def _stream_csv_export(user_id: int, session: AsyncSession):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=EXPORT_COLUMNS, lineterminator="\n")
    writer.writeheader()
    yield buffer.getvalue().encode("utf-8")
    buffer.seek(0)
    buffer.truncate(0)
    async for batch in _iter_export_batches(user_id, session):
        for entry in batch:
            writer.writerow(_export_row(entry))
        yield buffer.getvalue().encode("utf-8")
        buffer.seek(0)
        buffer.truncate(0)


async def _stream_json_export(user_id: int, session: AsyncSession):
    yield b"["
    first = True
    async for batch in _iter_export_batches(user_id, session):
        for entry in batch:
            if not first:
                yield b","
            yield json.dumps(_export_row(entry), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            first = False
    yield b"]"


async def _stream_xlsx_export(user_id: int, session: AsyncSession):
    from openpyxl import Workbook

    with tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b") as temp_file:
        workbook = Workbook(write_only=True)
        sheet = workbook.create_sheet("Feedback")
        sheet.append(EXPORT_COLUMNS)
        async for batch in _iter_export_batches(user_id, session):
            for entry in batch:
                row = _export_row(entry)
                sheet.append([row[column] for column in EXPORT_COLUMNS])
        workbook.save(temp_file)
        temp_file.seek(0)
        while chunk := temp_file.read(64 * 1024):
            yield chunk


@feedback_router.get("/export")
async def export_feedback(
    format: Literal["csv", "xlsx", "json"] = Query(default="csv"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Export feedback with bounded Neon queries and streaming output."""
    if format == "json":
        return StreamingResponse(
            _stream_json_export(user.id, session),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=feedbacklens_export.json"}
        )
    if format == "xlsx":
        return StreamingResponse(
            _stream_xlsx_export(user.id, session),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=feedbacklens_export.xlsx"},
        )
    return StreamingResponse(
        _stream_csv_export(user.id, session),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=feedbacklens_export.csv"},
    )


# ---------------------------------------------------------------------------
# Bulk Import — Skill: backend-architect
# ---------------------------------------------------------------------------
class BulkImportRequest(BaseModel):
    texts: List[str]  # array of feedback texts to import

@feedback_router.post("/bulk")
async def bulk_import_feedback(
    body: BulkImportRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Import multiple feedback texts and process each through the production pipeline."""
    if len(body.texts) > 500:
        raise HTTPException(status_code=400, detail="Max 500 items per bulk import")
    non_empty = [text for text in body.texts if text and text.strip()]
    await _enforce_feedback_limit(user, len(non_empty), session)
    created_items: list[dict] = []
    batch_candidates = await _load_dedupe_candidates(user.id, session)
    duplicates_skipped = 0
    spam_rejected = 0
    for text in non_empty:
        try:
            cleaned = _clean_feedback_text(text)
        except SpamDetectedError:
            spam_rejected += 1
            continue
        if _find_semantic_duplicate(cleaned, batch_candidates):
            duplicates_skipped += 1
            continue
        try:
            created = await _create_processed_feedback(
                user_id=user.id,
                text=cleaned,
                source="manual",
                session=session,
                candidates=batch_candidates,
            )
        except SpamDetectedError:
            spam_rejected += 1
            continue
        if created.get("deduped"):
            duplicates_skipped += 1
            continue
        created_items.append(created)
    await session.commit()
    return {
        "created": len(created_items),
        "ids": [item["id"] for item in created_items],
        "items": created_items,
        "duplicates_skipped": duplicates_skipped,
        "spam_rejected": spam_rejected,
    }


@feedback_router.post("/bulk-csv")
async def bulk_import_csv(
    file: UploadFile = File(...),
    column: str = Query(default="text", description="Column name containing the feedback text"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Import feedback from a CSV file. Reads the specified column as feedback texts."""
    allowed_content_types = {"text/csv", "application/vnd.ms-excel"}
    content_type = (file.content_type or "").split(";", 1)[0].lower()
    if content_type and content_type not in allowed_content_types:
        raise HTTPException(status_code=415, detail="CSV upload must use text/csv or application/vnd.ms-excel")
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="CSV limited to 5MB for bulk import")
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV: {e}")
    if column not in df.columns:
        raise HTTPException(status_code=400, detail=f"Column '{column}' not found. Available: {list(df.columns)}")

    texts = [text for text in df[column].dropna().astype(str).tolist() if text.strip()]
    await _enforce_feedback_limit(user, len(texts), session)
    created_items: list[dict] = []
    batch_candidates = await _load_dedupe_candidates(user.id, session)
    duplicates_skipped = 0
    spam_rejected = 0
    for text in texts[:500]:
        try:
            cleaned = _clean_feedback_text(text)
        except SpamDetectedError:
            spam_rejected += 1
            continue
        if _find_semantic_duplicate(cleaned, batch_candidates):
            duplicates_skipped += 1
            continue
        try:
            created = await _create_processed_feedback(
                user_id=user.id,
                text=cleaned,
                source="manual",
                session=session,
                candidates=batch_candidates,
            )
        except SpamDetectedError:
            spam_rejected += 1
            continue
        if created.get("deduped"):
            duplicates_skipped += 1
            continue
        created_items.append(created)
    await session.commit()
    return {
        "created": len(created_items),
        "ids": [item["id"] for item in created_items],
        "items": created_items,
        "duplicates_skipped": duplicates_skipped,
        "spam_rejected": spam_rejected,
        "total_rows": len(df),
    }


# ---------------------------------------------------------------------------
# Draft Reply Generator
# ---------------------------------------------------------------------------
@feedback_router.post("/{feedback_id}/draft-reply")
async def generate_draft_reply(
    feedback_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Generates a deterministic support reply from local sentiment metadata.
    """
    entry = await session.get(FeedbackEntry, feedback_id)
    if not entry or entry.user_id != user.id:
        raise HTTPException(status_code=404, detail="Feedback not found")

    draft = _support_draft(entry.sentiment or "neutral", entry.is_urgent, _parse_themes(entry.themes_json))

    entry.draft_reply = draft
    entry.updated_at = _utc_now()
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return _serialize(entry)


app = create_app(
    title="Feedback Lens",
    description="Enhanced local sentiment analysis with optional DistilBERT transformers and deterministic fallbacks.",
    domain_routers=[
        feedback_router,
        settings_router,
        sources_router,
        clusters_router,
        connect_router,
        digest_router,
        public_ingest_router,
        cron_router,
    ]
)


@app.exception_handler(SpamDetectedError)
async def _spam_detected_handler(_request: Request, exc: SpamDetectedError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8005, reload=True)
