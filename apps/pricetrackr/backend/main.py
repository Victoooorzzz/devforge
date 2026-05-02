import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "packages"))

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel, select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import asyncio
import logging

from backend_core import create_app, get_current_user, get_session, User, scraper
from backend_core.email_service import send_email

logger = logging.getLogger(__name__)

class TrackedUrl(SQLModel, table=True):
    __tablename__ = "tracked_urls"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    url: str
    label: str
    current_price: Optional[float] = None
    previous_price: Optional[float] = None
    last_checked: Optional[datetime] = None
    status: str = Field(default="active")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TrackerSettings(SQLModel, table=True):
    __tablename__ = "tracker_settings"
    user_id: int = Field(primary_key=True)
    alert_email: str = Field(default="")
    frequency: str = Field(default="24h")

class TrackerCreate(BaseModel):
    url: str
    label: str

class TrackerPrefsUpdate(BaseModel):
    alert_email: str
    frequency: str

tracker_router = APIRouter(prefix="/trackers", tags=["trackers"])
settings_router = APIRouter(prefix="/settings", tags=["settings"])

@settings_router.get("/tracker-prefs")
async def get_tracker_prefs(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(TrackerSettings).where(TrackerSettings.user_id == user.id))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = TrackerSettings(user_id=user.id)
        session.add(settings)
        await session.flush()
    return {"alert_email": settings.alert_email, "frequency": settings.frequency}

@settings_router.put("/tracker-prefs")
async def update_tracker_prefs(body: TrackerPrefsUpdate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(TrackerSettings).where(TrackerSettings.user_id == user.id))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = TrackerSettings(user_id=user.id, alert_email=body.alert_email, frequency=body.frequency)
    else:
        settings.alert_email = body.alert_email
        settings.frequency = body.frequency
    session.add(settings)
    await session.flush()
    return {"alert_email": settings.alert_email, "frequency": settings.frequency}

async def run_price_updates():
    """Background task to update all prices safely and send alerts."""
    from backend_core.database import SessionLocal
    async with SessionLocal() as session:
        result = await session.execute(select(TrackedUrl).where(TrackedUrl.status == "active"))
        trackers = result.scalars().all()
        for t in trackers:
            try:
                new_price = await scraper.fetch_price(t.url)

                if new_price and new_price != t.current_price:
                    t.previous_price = t.current_price
                    t.current_price = new_price
                    t.last_checked = datetime.now(timezone.utc)
                    session.add(t)

                    # Send price-change alert if user configured an email
                    settings_req = await session.execute(
                        select(TrackerSettings).where(TrackerSettings.user_id == t.user_id)
                    )
                    user_settings = settings_req.scalar_one_or_none()

                    if user_settings and user_settings.alert_email:
                        direction = "dropped" if new_price < (t.previous_price or 0) else "changed"
                        await send_email(
                            to=user_settings.alert_email,
                            subject=f"Price Alert: {t.label} has {direction}!",
                            html_body=(
                                f"The price of {t.label} has {direction} "
                                f"from ${t.previous_price:,.2f} to ${t.current_price:,.2f}.<br><br>"
                                f"Check it out: <a href='{t.url}'>{t.url}</a>"
                            )
                        )
                        logger.info(f"Alert sent to {user_settings.alert_email} for {t.label}")

            except Exception as e:
                logger.error(f"Error scraping {t.url}: {e}")

            # Anti-ban: mandatory pause between requests
            await asyncio.sleep(3)

        await session.commit()

@tracker_router.post("")
async def create_tracker(body: TrackerCreate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Active subscription required")
    
    # Fetch initial price
    initial_price = await scraper.fetch_price(body.url)
    
    t = TrackedUrl(
        user_id=user.id, 
        url=body.url, 
        label=body.label,
        current_price=initial_price,
        last_checked=datetime.now(timezone.utc) if initial_price else None
    )
    session.add(t)
    await session.flush()
    await session.refresh(t)
    return t

@tracker_router.get("/list")
async def list_trackers(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(TrackedUrl).where(TrackedUrl.user_id == user.id).order_by(TrackedUrl.created_at.desc()))
    return result.scalars().all()

@tracker_router.delete("/{tracker_id}")
async def delete_tracker(tracker_id: int, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(TrackedUrl).where(TrackedUrl.id == tracker_id, TrackedUrl.user_id == user.id))
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Not found")
    await session.delete(t)
    return {"status": "deleted"}

app = create_app(
    title="Price Tracker", 
    description="Monitor competitor prices and get alerts", 
    domain_routers=[tracker_router, settings_router]
)

@app.on_event("startup")
async def schedule_price_jobs():
    app.state.scheduler.add_job(
        run_price_updates,
        "interval",
        hours=24,
        id="price_update_job"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8003, reload=True)
