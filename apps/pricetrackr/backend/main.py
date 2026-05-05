import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "packages"))

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel, select
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import asyncio, logging

from backend_core import create_app, get_current_user, get_session, User, scraper, require_user_access
from backend_core.database import get_managed_session
from backend_core.email_service import send_email

logger = logging.getLogger(__name__)

# SQL migrations needed for new columns on existing DB:
# ALTER TABLE tracked_urls ADD COLUMN IF NOT EXISTS min_price FLOAT;
# ALTER TABLE tracked_urls ADD COLUMN IF NOT EXISTS in_stock BOOLEAN;
# (PriceHistory is a new table — created automatically by SQLModel)


class TrackedUrl(SQLModel, table=True):
    __tablename__ = "tracked_urls"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    url: str
    label: str
    current_price: Optional[float] = None
    previous_price: Optional[float] = None
    min_price: Optional[float] = None          # historical minimum
    in_stock: Optional[bool] = None            # stock status
    last_checked: Optional[datetime] = None
    next_check_at: Optional[datetime] = None   # when to check next (dynamic frequency)
    check_frequency_hours: int = Field(default=24)  # 1, 6, 12, or 24 hours
    status: str = Field(default="active")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PriceHistory(SQLModel, table=True):
    __tablename__ = "price_history"
    id: Optional[int] = Field(default=None, primary_key=True)
    tracker_id: int = Field(index=True)
    price: Optional[float] = None
    in_stock: Optional[bool] = None
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TrackerSettings(SQLModel, table=True):
    __tablename__ = "tracker_settings"
    user_id: int = Field(primary_key=True)
    alert_email: str = Field(default="")
    frequency: str = Field(default="24h")


class TrackerCreate(BaseModel):
    url: str
    label: str
    check_frequency_hours: int = 24  # 1, 6, 12, or 24


class TrackerFrequencyUpdate(BaseModel):
    hours: int  # must be 1, 6, 12, or 24


class TrackerPrefsUpdate(BaseModel):
    alert_email: str
    frequency: str


tracker_router = APIRouter(prefix="/trackers", tags=["trackers"], dependencies=[Depends(require_user_access)])
settings_router = APIRouter(prefix="/settings", tags=["settings"])

@tracker_router.post("/cron/update", tags=["cron"])
async def cron_update_prices(authorization: str = None):
    """Endpoint para Vercel Cron / QStash."""
    # Simple secret check (optional but recommended)
    expected = os.getenv("CRON_SECRET")
    if expected and authorization != f"Bearer {expected}":
         raise HTTPException(status_code=401, detail="Unauthorized cron request")
    
    await run_price_updates()
    return {"status": "success", "task": "price_updates"}


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
    """Cron job: updates prices and stock for trackers whose next_check_at <= NOW()."""
    from datetime import timedelta
    async with get_managed_session() as session:
        now = datetime.now(timezone.utc)
        # Only fetch trackers that are due for a check
        result = await session.execute(
            select(TrackedUrl).where(
                TrackedUrl.status == "active",
                (TrackedUrl.next_check_at == None) | (TrackedUrl.next_check_at <= now),  # noqa: E711
            )
        )
        trackers = result.scalars().all()
        logger.info(f"Price cron: {len(trackers)} trackers due for check")

        for t in trackers:
            try:
                new_price = await scraper.fetch_price(t.url)
                new_stock = await scraper.fetch_stock(t.url)
                now = datetime.now(timezone.utc)

                price_changed = new_price is not None and new_price != t.current_price
                stock_changed = new_stock is not None and new_stock != t.in_stock

                if price_changed:
                    t.previous_price = t.current_price
                    t.current_price = new_price
                    # Track historical minimum
                    if t.min_price is None or new_price < t.min_price:
                        t.min_price = new_price

                if new_stock is not None:
                    t.in_stock = new_stock

                if price_changed or stock_changed:
                    t.last_checked = now
                    session.add(t)

                    # Record in price history
                    history = PriceHistory(
                        tracker_id=t.id,
                        price=new_price,
                        in_stock=new_stock,
                        recorded_at=now,
                    )
                    session.add(history)

                # --- Alerts ---
                settings_res = await session.execute(
                    select(TrackerSettings).where(TrackerSettings.user_id == t.user_id)
                )
                user_settings = settings_res.scalar_one_or_none()
                alert_email = user_settings.alert_email if user_settings else ""

                if alert_email:
                    # Price drop alert
                    if price_changed and t.previous_price and new_price < t.previous_price:
                        direction = "bajó"
                        send_email(
                            to=alert_email,
                            subject=f"📉 Bajada de precio: {t.label}",
                            html_body=(
                                f"<p>El precio de <strong>{t.label}</strong> {direction} "
                                f"de <strong>${t.previous_price:,.2f}</strong> a <strong>${new_price:,.2f}</strong>.</p>"
                                f"<p>{'🎯 ¡Es el mínimo histórico registrado!' if new_price == t.min_price else ''}</p>"
                                f"<p><a href='{t.url}'>Ver producto</a></p>"
                            )
                        )

                    # Back in stock alert
                    if stock_changed and new_stock is True and t.in_stock is False:
                        send_email(
                            to=alert_email,
                            subject=f"✅ Volvió al stock: {t.label}",
                            html_body=(
                                f"<p><strong>{t.label}</strong> volvió a estar disponible.</p>"
                                f"<p>Precio actual: <strong>${new_price:,.2f}</strong></p>" if new_price else ""
                                f"<p><a href='{t.url}'>Ver producto</a></p>"
                            )
                        )
                        logger.info(f"Stock alert sent for {t.label}")

            except Exception as e:
                logger.error(f"Error updating {t.url}: {e}")
            finally:
                # Always update next_check_at based on individual tracker frequency
                from datetime import timedelta
                t.next_check_at = datetime.now(timezone.utc) + timedelta(hours=t.check_frequency_hours)
                session.add(t)

            await asyncio.sleep(3)  # Anti-ban delay

        await session.commit()


@tracker_router.post("")
async def create_tracker(body: TrackerCreate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    if not user.has_access:
        raise HTTPException(status_code=403, detail="Active subscription or trial required")

    initial_price = await scraper.fetch_price(body.url)
    initial_stock = await scraper.fetch_stock(body.url)
    freq_hours = body.check_frequency_hours if body.check_frequency_hours in (1, 6, 12, 24) else 24
    from datetime import timedelta

    t = TrackedUrl(
        user_id=user.id,
        url=body.url,
        label=body.label,
        current_price=initial_price,
        min_price=initial_price,
        in_stock=initial_stock,
        last_checked=datetime.now(timezone.utc) if initial_price else None,
        check_frequency_hours=freq_hours,
        next_check_at=datetime.now(timezone.utc) + timedelta(hours=freq_hours),
    )
    session.add(t)
    await session.flush()
    await session.refresh(t)

    # Record initial price history point
    if initial_price:
        history = PriceHistory(tracker_id=t.id, price=initial_price, in_stock=initial_stock)
        session.add(history)
        await session.flush()

    return t


@tracker_router.get("/list")
async def list_trackers(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(TrackedUrl).where(TrackedUrl.user_id == user.id).order_by(TrackedUrl.created_at.desc()))
    return result.scalars().all()


@tracker_router.get("/{tracker_id}/history")
async def get_price_history(tracker_id: int, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    """Retorna los últimos 30 puntos del historial de precios para graficar."""
    # Verify ownership
    t_res = await session.execute(select(TrackedUrl).where(TrackedUrl.id == tracker_id, TrackedUrl.user_id == user.id))
    t = t_res.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Tracker not found")

    hist_res = await session.execute(
        select(PriceHistory)
        .where(PriceHistory.tracker_id == tracker_id)
        .order_by(PriceHistory.recorded_at.asc())
        .limit(30)
    )
    history = hist_res.scalars().all()
    return [
        {
            "price": h.price,
            "in_stock": h.in_stock,
            "recorded_at": h.recorded_at.isoformat(),
        }
        for h in history
    ]


@tracker_router.patch("/{tracker_id}/frequency")
async def update_tracker_frequency(
    tracker_id: int,
    body: TrackerFrequencyUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Update the check frequency for a specific tracker.
    Allowed values: 1h, 6h, 12h, 24h.
    """
    if body.hours not in (1, 6, 12, 24):
        raise HTTPException(status_code=400, detail="Frequency must be 1, 6, 12, or 24 hours")

    result = await session.execute(
        select(TrackedUrl).where(TrackedUrl.id == tracker_id, TrackedUrl.user_id == user.id)
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Tracker not found")

    from datetime import timedelta
    t.check_frequency_hours = body.hours
    t.next_check_at = datetime.now(timezone.utc) + timedelta(hours=body.hours)
    session.add(t)
    await session.flush()
    return {
        "id": t.id,
        "label": t.label,
        "check_frequency_hours": t.check_frequency_hours,
        "next_check_at": t.next_check_at.isoformat(),
    }


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

# Eliminado local APScheduler para compatibilidad con Serverless (Vercel Crons)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8003, reload=True)
