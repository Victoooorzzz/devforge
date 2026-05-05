import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "packages"))

import json, logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel, select
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from collections import Counter

from backend_core import create_app, get_current_user, get_session, get_settings, User, require_user_access
from backend_core.database import get_managed_session
from backend_core.email_service import send_email
from backend_core.outbox_models import SystemOutbox
from backend_core.worker import register_job_handler

logger = logging.getLogger(__name__)
settings = get_settings()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class FeedbackEntry(SQLModel, table=True):
    __tablename__ = "feedback_entries"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    text: str
    sentiment: Optional[str] = None       # positive | negative | neutral
    confidence: Optional[float] = None
    themes_json: str = Field(default="[]")
    is_urgent: bool = Field(default=False)
    draft_reply: Optional[str] = None
    analysis_engine: Optional[str] = None  # "gemini" | "vader" | "keyword"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FeedbackSettings(SQLModel, table=True):
    __tablename__ = "feedback_settings"
    user_id: int = Field(primary_key=True)
    custom_prompt: str = Field(default="")
    negative_threshold: int = Field(default=5)
    alert_email: str = Field(default="")
    weekly_summary_enabled: bool = Field(default=True)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class FeedbackCreate(BaseModel):
    text: str

class FeedbackPrefsUpdate(BaseModel):
    custom_prompt: str = ""
    negative_threshold: int = 5
    alert_email: str = ""
    weekly_summary_enabled: bool = True

class FeedbackAnalysis(BaseModel):
    sentiment: str
    confidence: float
    themes: List[str]
    is_urgent: bool
    draft_reply: Optional[str]


# ---------------------------------------------------------------------------
# Analysis Engines (Gemini → VADER → Keyword fallback)
# ---------------------------------------------------------------------------

def _analyze_with_vader(text: str) -> dict:
    """
    Local sentiment analysis using VADER. No API key required.
    Returns same shape as Gemini analysis.
    """
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer  # type: ignore
        analyzer = SentimentIntensityAnalyzer()
        scores = analyzer.polarity_scores(text)
        compound = scores["compound"]

        if compound >= 0.05:
            sentiment = "positive"
        elif compound <= -0.05:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        confidence = min(abs(compound) + 0.5, 1.0)

        # Simple urgency heuristic
        urgent_keywords = ["broken", "not working", "can't", "cannot", "urgent", "immediately",
                           "refund", "charge", "error", "crash", "down", "bug", "lost", "critical"]
        is_urgent = any(k in text.lower() for k in urgent_keywords) and sentiment == "negative"

        # Extract simple themes from nouns (basic approach)
        words = text.lower().split()
        theme_candidates = [w for w in words if len(w) > 5 and w.isalpha()]
        themes = list(set(theme_candidates[:3]))

        draft = None
        if sentiment == "negative":
            draft = "Thank you for your feedback. We're sorry to hear about your experience and will address this as a priority."
        elif sentiment == "positive":
            draft = "Thank you for the kind words! We're glad to hear you're having a great experience."

        return {
            "sentiment": sentiment,
            "confidence": round(confidence, 2),
            "themes": themes,
            "is_urgent": is_urgent,
            "draft_reply": draft,
            "engine": "vader",
        }
    except ImportError:
        return _analyze_with_keywords(text)


def _analyze_with_keywords(text: str) -> dict:
    """Ultimate fallback: simple keyword matching. Always available."""
    text_lower = text.lower()
    positive_words = ["love", "great", "amazing", "excellent", "perfect", "best", "wonderful", "fantastic", "good", "thank"]
    negative_words = ["bad", "terrible", "worst", "hate", "broken", "awful", "horrible", "useless", "poor", "wrong"]
    urgent_words   = ["urgent", "immediately", "refund", "charge", "lost", "critical", "asap", "blocked"]

    pos_score = sum(1 for w in positive_words if w in text_lower)
    neg_score = sum(1 for w in negative_words if w in text_lower)
    is_urgent = any(w in text_lower for w in urgent_words) and neg_score > 0

    if pos_score > neg_score:
        sentiment, confidence = "positive", 0.65
        draft = "Thank you for the kind words!"
    elif neg_score > pos_score:
        sentiment, confidence = "negative", 0.65
        draft = "We're sorry about your experience. We'll look into this right away."
    else:
        sentiment, confidence = "neutral", 0.55
        draft = None

    return {
        "sentiment": sentiment,
        "confidence": confidence,
        "themes": [],
        "is_urgent": is_urgent,
        "draft_reply": draft,
        "engine": "keyword",
    }


async def _analyze_with_gemini(text: str, custom_prompt: str = "") -> dict | None:
    """
    Gemini analysis using the PLATFORM's API key (server-side).
    Users never provide their own key.
    Returns None on any failure so the caller can fall back.
    """
    if not settings.gemini_api_key:
        return None

    try:
        from google import genai

        client = genai.Client(api_key=settings.gemini_api_key)
        prompt = f"""{custom_prompt or "Analyze the following user feedback."}

Analyze this feedback and return structured JSON:
- sentiment: "positive" | "negative" | "neutral"
- confidence: float 0.0–1.0
- themes: list of short tags (max 5)
- is_urgent: true if critical bug, billing issue, or high frustration
- draft_reply: a concise empathetic support reply (1–2 sentences)

Feedback: "{text}"
"""
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config={"response_mime_type": "application/json", "response_schema": FeedbackAnalysis},
        )
        analysis = response.parsed
        return {
            "sentiment": analysis.sentiment,
            "confidence": analysis.confidence,
            "themes": analysis.themes,
            "is_urgent": analysis.is_urgent,
            "draft_reply": analysis.draft_reply,
            "engine": "gemini",
        }
    except Exception as e:
        logger.warning(f"Gemini analysis failed, falling back to VADER: {e}")
        return None


def _serialize(entry: FeedbackEntry) -> dict:
    return {
        "id": entry.id,
        "text": entry.text,
        "sentiment": entry.sentiment,
        "confidence": entry.confidence,
        "themes": json.loads(entry.themes_json or "[]"),
        "is_urgent": entry.is_urgent,
        "draft_reply": entry.draft_reply,
        "analysis_engine": entry.analysis_engine,
        "created_at": entry.created_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
feedback_router = APIRouter(prefix="/feedback", tags=["feedback"])
settings_router = APIRouter(prefix="/settings", tags=["settings"])


@settings_router.get("/feedback-prefs")
async def get_feedback_prefs(user: User = Depends(require_user_access), session: AsyncSession = Depends(get_session)):
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
    }


@settings_router.put("/feedback-prefs")
async def update_feedback_prefs(body: FeedbackPrefsUpdate, user: User = Depends(require_user_access), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(FeedbackSettings).where(FeedbackSettings.user_id == user.id))
    prefs = result.scalar_one_or_none()
    if not prefs:
        prefs = FeedbackSettings(user_id=user.id)
    prefs.custom_prompt = body.custom_prompt
    prefs.negative_threshold = body.negative_threshold
    prefs.alert_email = body.alert_email
    prefs.weekly_summary_enabled = body.weekly_summary_enabled
    session.add(prefs)
    await session.flush()
    return {"ok": True}


@feedback_router.post("")
async def create_feedback(body: FeedbackCreate, user: User = Depends(require_user_access), session: AsyncSession = Depends(get_session)):
    entry = FeedbackEntry(user_id=user.id, text=body.text)
    session.add(entry)
    await session.flush()
    await session.refresh(entry)
    return _serialize(entry)


@feedback_router.get("/list")
async def list_feedback(user: User = Depends(require_user_access), session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(FeedbackEntry)
        .where(FeedbackEntry.user_id == user.id)
        .order_by(FeedbackEntry.created_at.desc())
        .limit(100)
    )
    return [_serialize(e) for e in result.scalars().all()]


@feedback_router.post("/{entry_id}/analyze")
async def analyze_feedback(entry_id: int, user: User = Depends(require_user_access), session: AsyncSession = Depends(get_session)):
    """
    Enqueues feedback analysis using Gemini / VADER fallback.
    Users never need to provide an API key.
    """
    result = await session.execute(
        select(FeedbackEntry).where(FeedbackEntry.id == entry_id, FeedbackEntry.user_id == user.id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Not found")

    job = SystemOutbox(
        app_name="feedbacklens",
        job_type="analyze_feedback",
        payload={"entry_id": entry.id, "user_id": user.id},
        status="pending",
        max_attempts=3
    )
    session.add(job)
    await session.commit()
    
    return {"status": "queued", "message": "Analysis queued in system_outbox"}


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

        # Fetch user's custom prompt
        s_res = await session.execute(select(FeedbackSettings).where(FeedbackSettings.user_id == user_id))
        prefs = s_res.scalar_one_or_none()
        custom_prompt = prefs.custom_prompt if prefs else ""

        # Try Gemini first, then VADER, then keyword
        analysis = await _analyze_with_gemini(entry.text, custom_prompt)
        if analysis is None:
            analysis = _analyze_with_vader(entry.text)

        entry.sentiment = analysis["sentiment"]
        entry.confidence = analysis["confidence"]
        entry.themes_json = json.dumps(analysis["themes"])
        entry.is_urgent = analysis["is_urgent"]
        entry.draft_reply = analysis.get("draft_reply")
        entry.analysis_engine = analysis["engine"]

        session.add(entry)
        await session.commit()
        
    return {"status": "success", "entry_id": entry_id, "engine": analysis["engine"]}

# Register the handler
register_job_handler("feedbacklens", "analyze_feedback", process_feedback_analysis)


@feedback_router.get("/summary/weekly")
async def get_weekly_summary(user: User = Depends(require_user_access), session: AsyncSession = Depends(get_session)):
    """Returns a structured weekly digest for the dashboard."""
    one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    result = await session.execute(
        select(FeedbackEntry).where(
            FeedbackEntry.user_id == user.id,
            FeedbackEntry.created_at >= one_week_ago,
        )
    )
    entries = result.scalars().all()

    if not entries:
        return {
            "summary_text": "No feedback received this week.",
            "total": 0,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "sentiment_stats": {"positive": 0, "negative": 0, "neutral": 0},
            "top_themes": [],
            "urgent_count": 0,
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
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sentiment_stats": sentiments,
        "top_themes": top_themes,
        "urgent_count": urgent_count,
    }


async def weekly_summary_cron():
    """Cron: sends weekly digest emails to all users who enabled it."""
    async with get_managed_session() as session:
        prefs_result = await session.execute(
            select(FeedbackSettings).where(FeedbackSettings.weekly_summary_enabled == True)  # noqa: E712
        )
        all_prefs = prefs_result.scalars().all()

        one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)

        for prefs in all_prefs:
            if not prefs.alert_email:
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
            except Exception as e:
                logger.error(f"Failed to send weekly digest to {prefs.alert_email}: {e}")


@feedback_router.post("/cron/summary", tags=["cron"])
async def cron_feedback_summary(authorization: str = None):
    """Vercel Cron endpoint — sends weekly digest emails."""
    expected = os.getenv("CRON_SECRET")
    if expected and authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    await weekly_summary_cron()
    return {"status": "success", "task": "weekly_summary"}


app = create_app(
    title="Feedback Lens",
    description="AI-powered sentiment analysis — Gemini + VADER fallback",
    domain_routers=[feedback_router, settings_router]
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8005, reload=True)
