import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "packages"))

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel, select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from backend_core import create_app, get_current_user, get_session, User, scraper

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

class TrackerCreate(BaseModel):
    url: str
    label: str

tracker_router = APIRouter(prefix="/trackers", tags=["trackers"])

async def run_price_updates():
    """Background task to update all prices."""
    from backend_core.database import SessionLocal
    async with SessionLocal() as session:
        result = await session.execute(select(TrackedUrl).where(TrackedUrl.status == "active"))
        trackers = result.scalars().all()
        for t in trackers:
            new_price = await scraper.fetch_price(t.url)
            if new_price and new_price != t.current_price:
                t.previous_price = t.current_price
                t.current_price = new_price
                t.last_checked = datetime.now(timezone.utc)
                session.add(t)
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
    domain_routers=[tracker_router]
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
