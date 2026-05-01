import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "packages"))

import json, logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel, select
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone

from backend_core import create_app, get_current_user, get_session, get_settings, User

logger = logging.getLogger(__name__)
settings = get_settings()

class FeedbackEntry(SQLModel, table=True):
    __tablename__ = "feedback_entries"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    text: str
    sentiment: Optional[str] = None
    confidence: Optional[float] = None
    themes_json: str = Field(default="[]")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class FeedbackSettings(SQLModel, table=True):
    __tablename__ = "feedback_settings"
    user_id: int = Field(primary_key=True)
    custom_prompt: str = Field(default="")
    negative_threshold: int = Field(default=5)

class FeedbackCreate(BaseModel):
    text: str

class FeedbackPrefsUpdate(BaseModel):
    custom_prompt: str
    negative_threshold: int

feedback_router = APIRouter(prefix="/feedback", tags=["feedback"])
settings_router = APIRouter(prefix="/settings", tags=["settings"])

@settings_router.get("/feedback-prefs")
async def get_feedback_prefs(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(FeedbackSettings).where(FeedbackSettings.user_id == user.id))
    settings_obj = result.scalar_one_or_none()
    if not settings_obj:
        settings_obj = FeedbackSettings(user_id=user.id)
        session.add(settings_obj)
        await session.flush()
    return {"custom_prompt": settings_obj.custom_prompt, "negative_threshold": settings_obj.negative_threshold}

@settings_router.put("/feedback-prefs")
async def update_feedback_prefs(body: FeedbackPrefsUpdate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(FeedbackSettings).where(FeedbackSettings.user_id == user.id))
    settings_obj = result.scalar_one_or_none()
    if not settings_obj:
        settings_obj = FeedbackSettings(user_id=user.id, custom_prompt=body.custom_prompt, negative_threshold=body.negative_threshold)
    else:
        settings_obj.custom_prompt = body.custom_prompt
        settings_obj.negative_threshold = body.negative_threshold
    session.add(settings_obj)
    await session.flush()
    return {"custom_prompt": settings_obj.custom_prompt, "negative_threshold": settings_obj.negative_threshold}

def _serialize(entry: FeedbackEntry) -> dict:
    return {"id": entry.id, "text": entry.text, "sentiment": entry.sentiment, "confidence": entry.confidence, "themes": json.loads(entry.themes_json), "created_at": entry.created_at.isoformat()}

class FeedbackAnalysis(BaseModel):
    sentiment: str
    confidence: float
    themes: List[str]

@feedback_router.post("")
async def create_feedback(body: FeedbackCreate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Active subscription required")
    entry = FeedbackEntry(user_id=user.id, text=body.text)
    session.add(entry)
    await session.flush()
    await session.refresh(entry)
    return _serialize(entry)

@feedback_router.get("/list")
async def list_feedback(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(FeedbackEntry).where(FeedbackEntry.user_id == user.id).order_by(FeedbackEntry.created_at.desc()))
    return [_serialize(e) for e in result.scalars().all()]

@feedback_router.post("/{entry_id}/analyze")
async def analyze_feedback(entry_id: int, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(FeedbackEntry).where(FeedbackEntry.id == entry_id, FeedbackEntry.user_id == user.id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Not found")

    if not settings.gemini_api_key:
        # Fallback: simple keyword analysis
        text_lower = entry.text.lower()
        if any(w in text_lower for w in ["love", "great", "amazing", "excellent", "perfect", "best"]):
            entry.sentiment = "positive"
            entry.confidence = 0.75
        elif any(w in text_lower for w in ["bad", "terrible", "worst", "hate", "broken", "awful"]):
            entry.sentiment = "negative"
            entry.confidence = 0.75
        else:
            entry.sentiment = "neutral"
            entry.confidence = 0.60
        entry.themes_json = "[]"
    else:
        try:
            from google import genai
            client = genai.Client(api_key=settings.gemini_api_key)
            
            s_res = await session.execute(select(FeedbackSettings).where(FeedbackSettings.user_id == user.id))
            f_settings = s_res.scalar_one_or_none()
            user_prompt = f_settings.custom_prompt if f_settings and f_settings.custom_prompt else "Analyze the following user feedback."
            
            prompt = f"""{user_prompt}
            
Feedback: "{entry.text}"
"""
            response = client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=prompt,
                config={
                    'response_mime_type': 'application/json',
                    'response_schema': FeedbackAnalysis,
                }
            )
            
            analysis = response.parsed
            entry.sentiment = analysis.sentiment
            entry.confidence = analysis.confidence
            entry.themes_json = json.dumps(analysis.themes)
        except Exception as exc:
            logger.error("Gemini analysis failed: %s", exc)
            entry.sentiment = "neutral"
            entry.confidence = 0.5
            entry.themes_json = "[]"

    session.add(entry)
    await session.flush()
    await session.refresh(entry)
    return _serialize(entry)

app = create_app(title="Feedback Analyzer", description="AI-powered sentiment analysis for user feedback", domain_routers=[feedback_router, settings_router])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8005, reload=True)
