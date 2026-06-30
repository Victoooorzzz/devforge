import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "packages"))

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel, select, text
from pydantic import BaseModel
from typing import Optional, List, Literal
from datetime import datetime, timezone, timedelta
import asyncio, logging, io, json, random, uuid, re
import pandas as pd

from backend_core import create_app, get_current_user, get_session, User, scraper, require_product_access, get_settings
from backend_core.database import get_managed_session
from backend_core.email_service import send_email
from backend_core.price_alerts import build_price_alerts
from backend_core.product_insights import build_tracker_health, summarize_trackers
from backend_core.plan_limits import (
    get_pricetrackr_limits,
    reject_price_frequency_if_needed,
    reject_tracker_count_if_needed,
)
from backend_core.security_utils import is_public_http_url
from backend_core.worker import register_job_handler
from backend_core.outbox_models import SystemOutbox

logger = logging.getLogger(__name__)
settings = get_settings()

# SQL migrations needed for new columns on existing DB:
# ALTER TABLE tracked_urls ADD COLUMN IF NOT EXISTS min_price FLOAT;
# ALTER TABLE tracked_urls ADD COLUMN IF NOT EXISTS in_stock BOOLEAN;
# (PriceHistory is a new table — created automatically by SQLModel)


class TrackedUrl(SQLModel, table=True):
    __tablename__ = "tracked_urls"
    __table_args__ = {"extend_existing": True}
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
    alert_threshold: Optional[float] = None
    status: str = Field(default="active")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # New fields for Rev. 3 spec
    selector_1: Optional[str] = None
    selector_2: Optional[str] = None
    selector_3: Optional[str] = None
    last_text: Optional[str] = None
    is_public: bool = Field(default=True)
    slack_webhook_url: Optional[str] = None
    discord_webhook_url: Optional[str] = None
    slug: Optional[str] = None

    # Flagged review fields
    pending_price: Optional[float] = None
    pending_stock: Optional[bool] = None
    pending_text: Optional[str] = None


class PriceHistory(SQLModel, table=True):
    __tablename__ = "price_history"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    tracker_id: int = Field(index=True)
    price: Optional[float] = None
    in_stock: Optional[bool] = None
    recorded_at: datetime = Field(default_factory=datetime.utcnow)
    text_content: Optional[str] = None
    metadata_json: str = Field(default="{}")


class TrackerSettings(SQLModel, table=True):
    __tablename__ = "tracker_settings"
    __table_args__ = {"extend_existing": True}
    user_id: int = Field(primary_key=True)
    alert_email: str = Field(default="")
    frequency: str = Field(default="24h")


class ScrapeLog(SQLModel, table=True):
    __tablename__ = "scrape_logs"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    tracker_id: int = Field(index=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_agent: str
    status_code: int
    retry: bool


class ScrapeControl(SQLModel, table=True):
    __tablename__ = "scrape_control"
    __table_args__ = {"extend_existing": True}
    id: int = Field(default=1, primary_key=True)
    locked_at: Optional[datetime] = None
    consecutive_high_pressure: int = Field(default=0)


class PriceTrackrExportJob(SQLModel, table=True):
    __tablename__ = "pt_export_jobs"
    __table_args__ = {"extend_existing": True}
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: int = Field(index=True)
    status: str = Field(default="pending")  # pending, processing, completed, failed
    format: str = Field(default="csv")      # csv, xlsx, json
    r2_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None




def generate_slug(label: str) -> str:
    slug = label.lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    if not slug:
        slug = "product"
    uid = uuid.uuid4().hex[:6]
    return f"{slug}-{uid}"


class TrackerCreate(BaseModel):
    url: str
    label: str
    check_frequency_hours: int = 24  # 1, 6, 12, or 24
    selector_1: Optional[str] = None
    selector_2: Optional[str] = None
    selector_3: Optional[str] = None
    slack_webhook_url: Optional[str] = None
    discord_webhook_url: Optional[str] = None


class TrackerUpdate(BaseModel):
    label: Optional[str] = None
    url: Optional[str] = None
    check_frequency_hours: Optional[int] = None
    alert_threshold: Optional[float] = None
    selector_1: Optional[str] = None
    selector_2: Optional[str] = None
    selector_3: Optional[str] = None
    slack_webhook_url: Optional[str] = None
    discord_webhook_url: Optional[str] = None
    is_public: Optional[bool] = None


class TrackerFrequencyUpdate(BaseModel):
    hours: int  # must be 1, 6, 12, or 24


class TrackerPrefsUpdate(BaseModel):
    alert_email: str
    frequency: str



tracker_router = APIRouter(prefix="/trackers", tags=["trackers"], dependencies=[Depends(require_product_access("pricetrackr"))])
settings_router = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(require_product_access("pricetrackr"))])
cron_router = APIRouter(prefix="/trackers", tags=["cron"])

@cron_router.post("/cron/update", tags=["cron"])
async def cron_update_prices(authorization: str | None = Header(default=None)):
    """Endpoint para cron-job.org."""
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
    """Cron job: enqueues price checks for trackers whose next_check_at <= NOW()."""
    from datetime import timedelta
    async with get_managed_session() as session:
        # Check control lock
        ctrl_res = await session.execute(select(ScrapeControl).where(ScrapeControl.id == 1))
        ctrl = ctrl_res.scalar_one_or_none()
        if not ctrl:
            ctrl = ScrapeControl(id=1, locked_at=None)
            session.add(ctrl)
            await session.flush()

        now = datetime.utcnow()
        if ctrl.locked_at is not None:
            if now - ctrl.locked_at < timedelta(minutes=5):
                logger.info("Scraping lock is active and younger than 5 minutes. Skipping.")
                return {"status": "skipped", "reason": "Locked"}
            else:
                logger.warning("Scraping lock expired (>5 mins). Forcing unlock.")

        # Acquire lock
        ctrl.locked_at = now
        session.add(ctrl)
        await session.flush()

        # Only fetch trackers that are due for a check
        result = await session.execute(
            select(TrackedUrl).where(
                TrackedUrl.status == "active",
                (TrackedUrl.next_check_at == None) | (TrackedUrl.next_check_at <= now),  # noqa: E711
            )
        )
        trackers = result.scalars().all()
        logger.info(f"Price cron: {len(trackers)} trackers due for check, enqueueing jobs...")

        for t in trackers:
            job = SystemOutbox(
                app_name="pricetrackr",
                job_type="price_check",
                payload={"tracker_id": t.id, "url": t.url},
                status="pending"
            )
            session.add(job)

            # Anti-duplicate: Set next check to future immediately
            t.next_check_at = datetime.utcnow() + timedelta(hours=t.check_frequency_hours)
            session.add(t)

        # Queue pressure check
        one_hour_ago = now - timedelta(hours=1)
        # Pendientes
        pending_res = await session.execute(
            select(func.count(TrackedUrl.id)).where(
                TrackedUrl.status == "active",
                (TrackedUrl.next_check_at == None) | (TrackedUrl.next_check_at <= now)
            )
        )
        pending_count = pending_res.scalar_one()

        # Procesadas
        processed_res = await session.execute(
            select(func.count(ScrapeLog.id)).where(ScrapeLog.timestamp >= one_hour_ago)
        )
        processed_count = processed_res.scalar_one()

        # Ensure we have at least 3 runs of history to calculate pressure (to prevent division by zero or noisy alerts at bootstrap)
        total_logs_res = await session.execute(select(func.count(ScrapeLog.id)))
        total_logs_count = total_logs_res.scalar_one()

        if total_logs_count >= 3 and processed_count > 0:
            pressure = pending_count / processed_count
            logger.info(f"Queue pressure: {pressure:.2f} (pending: {pending_count}, processed last hour: {processed_count})")
            if pressure > 1.5:
                logger.warning(f"High queue pressure detected: {pressure:.2f}")

            if pressure > 2.0:
                ctrl.consecutive_high_pressure += 1
                if ctrl.consecutive_high_pressure >= 3:
                    # Alert admin
                    admin_email = os.getenv("SMTP_FROM", "admin@pricetrackr.com")
                    try:
                        await asyncio.to_thread(
                            send_email,
                            to=admin_email,
                            subject="⚠️ CRITICAL: High Queue Pressure in PriceTrackr",
                            html_body=(
                                f"<p>Queue pressure has been above 2.0 for 3 consecutive runs.</p>"
                                f"<p>Current pressure: <strong>{pressure:.2f}</strong></p>"
                                f"<p>Please consider upgrading to Render Starter or reducing check frequencies.</p>"
                            )
                        )
                        logger.critical("High queue pressure alert sent to admin.")
                    except Exception as e:
                        logger.error(f"Failed to send admin pressure alert: {e}")
            else:
                ctrl.consecutive_high_pressure = 0

        # Release lock at the end of enqueuing
        ctrl.locked_at = None
        session.add(ctrl)
        await session.commit()


PRICE_REGEX = re.compile(
    r"(?:[$\u20ac\u00a3\u00a5]|USD|EUR|GBP|S/\.?)?\s*"
    r"(\d+(?:[,.\s]\d{3})*(?:[.,]\d{1,2})?)"
)

def extract_price(text: str) -> float | None:
    cleaned = text.strip().replace("\xa0", " ")
    match = PRICE_REGEX.search(cleaned)
    if match:
        num_str = match.group(1).replace(" ", "")
        if "," in num_str and "." in num_str:
            if num_str.rfind(",") > num_str.rfind("."):
                num_str = num_str.replace(".", "").replace(",", ".")
            else:
                num_str = num_str.replace(",", "")
        elif "," in num_str:
            if re.search(r",\d{1,2}$", num_str):
                num_str = num_str.replace(",", ".")
            else:
                num_str = num_str.replace(",", "")
        try:
            val = float(num_str)
            if 0.01 <= val <= 999_999:
                return val
        except ValueError:
            pass
    return None


ALERT_CACHE = {}  # Deprecated in favor of DB rate limiting, kept for backward compatibility

async def trigger_alerts(t: TrackedUrl, previous_price: float | None, new_price: float | None, previous_stock: bool | None, new_stock: bool | None, last_text: str | None, new_text: str | None, session: AsyncSession):
    now = datetime.utcnow()

    # 1. Determine alert conditions
    alerts_to_send = [] # list of (change_type, direction, subject, html_body, slack_body, discord_body)

    # Price drop alert
    if previous_price is not None and new_price is not None and new_price < previous_price:
        direction = "bajó"
        subject = f"📉 Bajada de precio: {t.label}"
        min_msg = "🎯 ¡Es el mínimo histórico registrado!" if new_price == t.min_price else ""
        html = (
            f"<p>El precio de <strong>{t.label}</strong> bajó de <strong>${previous_price:,.2f}</strong> a <strong>${new_price:,.2f}</strong>.</p>"
            f"<p>{min_msg}</p>"
            f"<p><a href='{t.url}'>Ver producto</a></p>"
        )
        slack = f"*📉 Bajada de precio: {t.label}*\nEl precio de <{t.url}|{t.label}> bajó de *${previous_price:,.2f}* a *${new_price:,.2f}*.\n{min_msg}"
        discord = f"El precio de **{t.label}** bajó de **${previous_price:,.2f}** a **${new_price:,.2f}**.\n{min_msg}"
        alerts_to_send.append(("price", "bajó", subject, html, slack, discord))

    # Price rise alert
    if previous_price is not None and new_price is not None and new_price > previous_price:
        subject = f"📈 Subida de precio: {t.label}"
        html = (
            f"<p>El precio de <strong>{t.label}</strong> subió de <strong>${previous_price:,.2f}</strong> a <strong>${new_price:,.2f}</strong>.</p>"
            f"<p><a href='{t.url}'>Ver producto</a></p>"
        )
        slack = f"*📈 Subida de precio: {t.label}*\nEl precio de <{t.url}|{t.label}> subió de *${previous_price:,.2f}* a *${new_price:,.2f}*."
        discord = f"El precio de **{t.label}** subió de **${previous_price:,.2f}** a **${new_price:,.2f}**."
        alerts_to_send.append(("price", "subió", subject, html, slack, discord))

    # Target price reached
    if t.alert_threshold is not None and new_price is not None and new_price <= t.alert_threshold and (previous_price is None or previous_price > t.alert_threshold):
        subject = f"🎯 Target price reached: {t.label}"
        html = (
            f"<p><strong>{t.label}</strong> alcanzó tu target price de <strong>${t.alert_threshold:,.2f}</strong>.</p>"
            f"<p>Precio actual: <strong>${new_price:,.2f}</strong></p>"
            f"<p><a href='{t.url}'>Ver producto</a></p>"
        )
        slack = f"*🎯 Target price reached: {t.label}*\n<{t.url}|{t.label}> alcanzó el target price de *${t.alert_threshold:,.2f}*. Precio actual: *${new_price:,.2f}*."
        discord = f"**{t.label}** alcanzó el target price de **${t.alert_threshold:,.2f}**. Precio actual: **${new_price:,.2f}**."
        alerts_to_send.append(("price", "target", subject, html, slack, discord))

    # Stock alert: Out of stock
    if previous_stock is not False and new_stock is False:
        subject = f"⚠️ Agotado: {t.label}"
        html = (
            f"<p><strong>{t.label}</strong> se ha agotado.</p>"
            f"<p><a href='{t.url}'>Ver producto</a></p>"
        )
        slack = f"*⚠️ Agotado: {t.label}*\n<{t.url}|{t.label}> se ha agotado."
        discord = f"**{t.label}** se ha agotado."
        alerts_to_send.append(("stock", "agotado", subject, html, slack, discord))

    # Stock alert: Back in stock
    if previous_stock is False and new_stock is True:
        subject = f"✅ Volvió al stock: {t.label}"
        html = (
            f"<p><strong>{t.label}</strong> volvió a estar disponible.</p>"
            f"<p>Precio actual: <strong>${new_price:,.2f}</strong></p>" if new_price else ""
            f"<p><a href='{t.url}'>Ver producto</a></p>"
        )
        slack = f"*✅ Volvió al stock: {t.label}*\n<{t.url}|{t.label}> volvió a estar disponible. Precio actual: *${new_price:,.2f}*."
        discord = f"**{t.label}** volvió a estar disponible."
        alerts_to_send.append(("stock", "disponible", subject, html, slack, discord))

    # Text structural change
    if last_text is not None and new_text is not None and last_text != new_text:
        subject = f"📝 Cambio estructural de texto: {t.label}"
        html = (
            f"<p>El texto de <strong>{t.label}</strong> cambió:</p>"
            f"<p>Antes: <code>{last_text}</code></p>"
            f"<p>Ahora: <code>{new_text}</code></p>"
            f"<p><a href='{t.url}'>Ver producto</a></p>"
        )
        slack = f"*📝 Cambio estructural de texto: {t.label}*\nAntes: `{last_text}`\nAhora: `{new_text}`"
        discord = f"El texto de **{t.label}** cambió:\nAntes: `{last_text}`\nAhora: `{new_text}`"
        alerts_to_send.append(("text", "structural", subject, html, slack, discord))

    # Promotional text alert
    if new_text is not None and any(word in new_text.lower() for word in ["sale", "discount", "off", "oferta", "promocion", "descuento"]):
        had_promo = last_text is not None and any(word in last_text.lower() for word in ["sale", "discount", "off", "oferta", "promocion", "descuento"])
        if not had_promo:
            subject = f"🏷️ Promoción detectada: {t.label}"
            html = (
                f"<p>Se detectó una promoción en <strong>{t.label}</strong>:</p>"
                f"<p>Texto: <code>{new_text}</code></p>"
                f"<p><a href='{t.url}'>Ver producto</a></p>"
            )
            slack = f"*🏷️ Promoción detectada: {t.label}*\nTexto: `{new_text}`\n<{t.url}|Ver producto>"
            discord = f"🏷️ Promoción detectada en **{t.label}**:\nTexto: `{new_text}`"
            alerts_to_send.append(("promo", "detected", subject, html, slack, discord))

    # Get alert email from TrackerSettings
    settings_res = await session.execute(
        select(TrackerSettings).where(TrackerSettings.user_id == t.user_id)
    )
    user_settings = settings_res.scalar_one_or_none()
    alert_email = user_settings.alert_email if user_settings else ""

    # 2. Process rate limits & Send
    for change_type, direction, subject, html_body, slack_body, discord_body in alerts_to_send:
        # Check rate limit using database
        limit_hours = 6 if change_type == "price" else 24
        limit_time = now - timedelta(hours=limit_hours)
        query = text(
            "SELECT sent_at FROM pt_alert_logs "
            "WHERE tracker_id = :tracker_id AND change_type = :change_type AND direction = :direction "
            "AND sent_at >= :limit_time ORDER BY sent_at DESC LIMIT 1"
        )
        res = await session.execute(
            query,
            {"tracker_id": t.id, "change_type": change_type, "direction": direction, "limit_time": limit_time}
        )
        row = res.fetchone()
        if row:
            logger.info(f"Alert ({t.id}, {change_type}, {direction}) rate limited (last sent at {row[0]})")
            continue

        # Insert alert log
        insert_query = text(
            "INSERT INTO pt_alert_logs (tracker_id, change_type, direction, sent_at) "
            "VALUES (:tracker_id, :change_type, :direction, :sent_at)"
        )
        await session.execute(
            insert_query,
            {"tracker_id": t.id, "change_type": change_type, "direction": direction, "sent_at": now}
        )
        await session.flush()

        # Send Email (asyncio.to_thread)
        if alert_email:
            try:
                await asyncio.to_thread(send_email, to=alert_email, subject=subject, html_body=html_body)
            except Exception as e:
                logger.error(f"Failed to send email alert: {e}")

        # Send Slack Webhook (httpx.AsyncClient)
        if t.slack_webhook_url:
            try:
                import httpx
                payload = {"text": slack_body}
                async with httpx.AsyncClient() as client:
                    await client.post(t.slack_webhook_url, json=payload, timeout=5.0)
            except Exception as e:
                logger.error(f"Failed to send Slack alert: {e}")

        # Send Discord Webhook (httpx.AsyncClient)
        if t.discord_webhook_url:
            try:
                import httpx
                payload = {
                    "embeds": [{
                        "title": subject,
                        "description": discord_body,
                        "url": t.url,
                        "color": 65280 if "Volvió" in subject or "Bajada" in subject else 16711680
                    }]
                }
                async with httpx.AsyncClient() as client:
                    await client.post(t.discord_webhook_url, json=payload, timeout=5.0)
            except Exception as e:
                logger.error(f"Failed to send Discord alert: {e}")


async def process_price_check(payload: dict):
    tracker_id = payload.get("tracker_id")
    url = payload.get("url")
    if not tracker_id or not url:
        raise ValueError("Missing tracker_id or url in payload")

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
    ]

    async with get_managed_session() as session:
        result = await session.execute(select(TrackedUrl).where(TrackedUrl.id == tracker_id))
        t = result.scalar_one_or_none()
        if not t or t.status != "active":
            return {"status": "skipped", "reason": "Tracker inactive or deleted"}

        # Removed 2s delay to avoid blocking the queue worker

        # Rotate UA and headers
        ua = random.choice(USER_AGENTS)
        headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.google.com/",
            "Connection": "keep-alive"
        }

        status_code = 200
        retry = False
        html_text = ""

        try:
            async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=15.0) as client:
                resp = await client.get(t.url)
                status_code = resp.status_code
                if resp.status_code in (403, 500, 502, 503, 504):
                    retry = True
                    ua2 = random.choice([u for u in USER_AGENTS if u != ua])
                    headers["User-Agent"] = ua2
                    await asyncio.sleep(1.0)
                    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=15.0) as client2:
                        resp2 = await client2.get(t.url)
                        status_code = resp2.status_code
                        html_text = resp2.text
                else:
                    html_text = resp.text
        except Exception as e:
            status_code = 500
            logger.error(f"Error fetching {t.url}: {e}")

        # Log UA vs response status code
        log = ScrapeLog(
            tracker_id=t.id,
            user_agent=headers["User-Agent"],
            status_code=status_code,
            retry=retry,
            timestamp=datetime.utcnow()
        )
        session.add(log)
        await session.flush()

        if not html_text:
            await session.commit()
            return {"status": "failed", "reason": "No HTML returned"}

        try:
            soup = BeautifulSoup(html_text, "html.parser")

            # Pre-check for SPA/JS-rendered sites: body text length < 500 characters
            body_text = soup.body.get_text(separator=" ").strip() if soup.body else ""
            if len(body_text) < 500:
                logger.warning(f"SPA warning: HTML body contains only {len(body_text)} characters for {t.url}")

            new_price = None
            new_text = None

            # Try custom selectors fallback
            selectors = [t.selector_1, t.selector_2, t.selector_3]
            for sel in selectors:
                if sel:
                    el = soup.select_one(sel)
                    if el:
                        new_text = el.get_text(separator=" ").strip()
                        new_price = extract_price(new_text)
                        if new_price is not None:
                            break

            # JSON-LD fallback
            if new_price is None:
                for script in soup.select('script[type="application/ld+json"]'):
                    try:
                        ld = json.loads(script.string or "")
                        items = ld if isinstance(ld, list) else [ld]
                        for item in items:
                            offers = item.get("offers", item.get("Offers", {}))
                            if isinstance(offers, list):
                                offers = offers[0] if offers else {}
                            p = offers.get("price") or offers.get("lowPrice")
                            if p:
                                new_price = float(p)
                                break
                    except Exception:
                        continue

            # Generic selectors fallback
            if new_price is None:
                from backend_core.scraper import _GENERIC_SELECTORS
                for sel in _GENERIC_SELECTORS:
                    el = soup.select_one(sel)
                    if el:
                        raw = el.get("content") or el.get("value") or el.get_text()
                        new_price = extract_price(str(raw))
                        if new_price is not None:
                            new_text = str(raw).strip()
                            break

            # Body text regex fallback
            if new_price is None:
                new_price = extract_price(body_text)
                if new_price is not None:
                    new_text = f"Extracted from text: {new_price}"

            # Stock detection
            oos_keywords = [
                "out of stock", "agotado", "no disponible", "sold out",
                "fuera de stock", "temporarily unavailable", "backorder"
            ]
            text_lower = body_text.lower()
            new_stock = not any(kw in text_lower for kw in oos_keywords)

            # Change detection
            if new_price is not None:
                now = datetime.utcnow()
                previous_price = t.current_price
                previous_stock = t.in_stock
                previous_text = t.last_text

                price_changed = new_price != previous_price
                stock_changed = new_stock != previous_stock
                text_changed = new_text != previous_text

                # Check for > 50% change flag
                if previous_price is not None and price_changed:
                    percentage_change = abs(new_price - previous_price) / previous_price
                    if percentage_change > 0.5:
                        t.pending_price = new_price
                        t.pending_stock = new_stock
                        t.pending_text = new_text
                        t.status = "flagged"
                        session.add(t)
                        await session.commit()
                        logger.warning(f"Tracker {t.id} flagged: price change is {percentage_change * 100:.1f}%")
                        return {"status": "flagged", "tracker_id": t.id, "price": new_price}

                # Apply changes normally
                if price_changed:
                    t.previous_price = previous_price
                    t.current_price = new_price
                    if t.min_price is None or new_price < t.min_price:
                        t.min_price = new_price

                t.in_stock = new_stock
                t.last_text = new_text

                if price_changed or stock_changed or text_changed:
                    t.last_checked = now
                    session.add(t)

                    # Record in price history
                    history = PriceHistory(
                        tracker_id=t.id,
                        price=new_price,
                        in_stock=new_stock,
                        recorded_at=now,
                        text_content=new_text,
                    )
                    session.add(history)

                    # Trigger alerts
                    await session.flush()
                    await trigger_alerts(t, previous_price, new_price, previous_stock, new_stock, previous_text, new_text, session)

        except Exception as e:
            logger.error(f"Error updating {t.url}: {e}")
            raise e
        finally:
            await session.commit()

    return {"status": "success", "tracker_id": tracker_id, "price": new_price, "stock": new_stock}


# Register the handler
register_job_handler("pricetrackr", "price_check", process_price_check)


async def process_csv_export(payload: dict):
    job_id_str = payload.get("job_id")
    user_id = payload.get("user_id")
    fmt = payload.get("format", "csv")
    if not job_id_str or not user_id:
        raise ValueError("Missing job_id or user_id in payload")

    job_uuid = uuid.UUID(job_id_str)

    async with get_managed_session() as session:
        # Update job to processing
        job_res = await session.execute(select(PriceTrackrExportJob).where(PriceTrackrExportJob.id == job_uuid))
        job = job_res.scalar_one_or_none()
        if not job:
            return {"status": "error", "message": "Job not found"}
        job.status = "processing"
        session.add(job)
        await session.commit()

    try:
        async with get_managed_session() as session:
            result = await session.execute(
                select(TrackedUrl).where(TrackedUrl.user_id == user_id).order_by(TrackedUrl.created_at.desc())
            )
            trackers = result.scalars().all()

            rows = []
            for t in trackers:
                rows.append({
                    "id": t.id,
                    "label": t.label,
                    "url": t.url,
                    "current_price": t.current_price,
                    "previous_price": t.previous_price,
                    "min_price_ever": t.min_price,
                    "in_stock": t.in_stock,
                    "alert_threshold": t.alert_threshold,
                    "last_checked": t.last_checked.isoformat() if t.last_checked else None,
                    "check_frequency_hours": t.check_frequency_hours,
                    "status": t.status,
                })

        if fmt == "json":
            content_bytes = json.dumps(rows, indent=2).encode()
            media_type = "application/json"
            file_ext = "json"
        else:
            df = pd.DataFrame(rows)
            buf = io.BytesIO()
            if fmt == "xlsx":
                df.to_excel(buf, index=False, engine="openpyxl")
                media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                file_ext = "xlsx"
            else:
                df.to_csv(buf, index=False)
                media_type = "text/csv"
                file_ext = "csv"
            content_bytes = buf.getvalue()

        import boto3
        s3 = boto3.client(
            's3',
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
            region_name="auto"
        )

        object_name = f"pricetrackr/exports/{user_id}/{job_id_str}.{file_ext}"
        bucket_name = settings.s3_bucket_name

        await asyncio.to_thread(
            s3.put_object,
            Bucket=bucket_name,
            Key=object_name,
            Body=content_bytes,
            ContentType=media_type
        )

        r2_url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': object_name},
            ExpiresIn=3600 * 24 * 7
        )

        async with get_managed_session() as session:
            job_res = await session.execute(select(PriceTrackrExportJob).where(PriceTrackrExportJob.id == job_uuid))
            job = job_res.scalar_one_or_none()
            if job:
                job.status = "completed"
                job.r2_url = r2_url
                job.completed_at = datetime.utcnow()
                session.add(job)
                await session.commit()

    except Exception as e:
        logger.error(f"Error processing export job {job_id_str}: {e}")
        async with get_managed_session() as session:
            job_res = await session.execute(select(PriceTrackrExportJob).where(PriceTrackrExportJob.id == job_uuid))
            job = job_res.scalar_one_or_none()
            if job:
                job.status = "failed"
                job.error_message = str(e)
                job.completed_at = datetime.utcnow()
                session.add(job)
                await session.commit()
        raise e

    return {"status": "success", "job_id": job_id_str}


register_job_handler("pricetrackr", "csv_export", process_csv_export)


class DetectRequest(BaseModel):
    url: str


@tracker_router.post("/detect")
async def detect_url_metadata(body: DetectRequest, user: User = Depends(get_current_user)):
    if not is_public_http_url(body.url):
        raise HTTPException(status_code=400, detail="Only public http(s) product URLs are allowed")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        import httpx
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=10.0) as client:
            resp = await client.get(body.url)
            resp.raise_for_status()
            html = resp.text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {str(e)}")

    soup = BeautifulSoup(html, "html.parser")
    body_len = len(soup.body.get_text(separator=" ").strip()) if soup.body else 0
    is_js_rendered = body_len < 500

    suggested_price = None
    matched_selector = None

    # Try store specific
    store = scraper._detect_store(body.url)
    if store:
        for sel in scraper._STORE_SELECTORS[store]:
            el = soup.select_one(sel)
            if el:
                raw = el.get("content") or el.get_text()
                price = scraper._extract_price_from_text(str(raw))
                if price:
                    suggested_price = price
                    matched_selector = sel
                    break

    # Try generic
    if not suggested_price:
        for sel in scraper._GENERIC_SELECTORS:
            el = soup.select_one(sel)
            if el:
                raw = el.get("content") or el.get("value") or el.get_text()
                price = scraper._extract_price_from_text(str(raw))
                if price:
                    suggested_price = price
                    matched_selector = sel
                    break

    # Try JSON-LD
    if not suggested_price:
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                ld = json.loads(script.string or "")
                items = ld if isinstance(ld, list) else [ld]
                for item in items:
                    offers = item.get("offers", item.get("Offers", {}))
                    if isinstance(offers, list):
                        offers = offers[0] if offers else {}
                    p = offers.get("price") or offers.get("lowPrice")
                    if p:
                        suggested_price = float(p)
                        matched_selector = 'JSON-LD offers.price'
                        break
            except Exception:
                continue

    # Detect stock
    oos_keywords = ["out of stock", "agotado", "no disponible", "sold out", "fuera de stock"]
    text_lower = soup.get_text().lower()
    in_stock = not any(kw in text_lower for kw in oos_keywords)

    return {
        "price": suggested_price,
        "selector": matched_selector,
        "in_stock": in_stock,
        "is_js_rendered": is_js_rendered,
        "body_length": body_len
    }


@tracker_router.post("")
async def create_tracker(body: TrackerCreate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    if not user.has_access:
        raise HTTPException(status_code=403, detail="Active subscription or trial required")
    if not is_public_http_url(body.url):
        raise HTTPException(status_code=400, detail="Only public http(s) product URLs are allowed")

    freq_hours = body.check_frequency_hours if body.check_frequency_hours in (1, 6, 12, 24) else 24
    plan, limits = await get_pricetrackr_limits(user, session)
    reject_price_frequency_if_needed(plan, limits, freq_hours)

    count_result = await session.execute(
        select(func.count(TrackedUrl.id)).where(
            TrackedUrl.user_id == user.id,
            TrackedUrl.status == "active",
        )
    )
    reject_tracker_count_if_needed(plan, limits, count_result.scalar_one())

    initial_price = await scraper.fetch_price(body.url)
    initial_stock = await scraper.fetch_stock(body.url)
    from datetime import timedelta

    # Generate unique slug
    slug = generate_slug(body.label)
    for _ in range(5):
        existing = await session.execute(
            select(TrackedUrl).where(TrackedUrl.slug == slug)
        )
        if not existing.scalar_one_or_none():
            break
        slug = generate_slug(body.label)

    t = TrackedUrl(
        user_id=user.id,
        url=body.url,
        label=body.label,
        current_price=initial_price,
        min_price=initial_price,
        in_stock=initial_stock,
        last_checked=datetime.utcnow() if initial_price else None,
        check_frequency_hours=freq_hours,
        next_check_at=datetime.utcnow() + timedelta(hours=freq_hours),
        selector_1=body.selector_1,
        selector_2=body.selector_2,
        selector_3=body.selector_3,
        slack_webhook_url=body.slack_webhook_url,
        discord_webhook_url=body.discord_webhook_url,
        slug=slug,
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


@tracker_router.get("/summary")
async def tracker_summary(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(TrackedUrl).where(TrackedUrl.user_id == user.id))
    return summarize_trackers(result.scalars().all())


@tracker_router.get("/health")
async def tracker_health(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(TrackedUrl).where(TrackedUrl.user_id == user.id))
    return build_tracker_health(result.scalars().all())


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
    plan, limits = await get_pricetrackr_limits(user, session)
    reject_price_frequency_if_needed(plan, limits, body.hours)

    result = await session.execute(
        select(TrackedUrl).where(TrackedUrl.id == tracker_id, TrackedUrl.user_id == user.id)
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Tracker not found")

    from datetime import timedelta
    t.check_frequency_hours = body.hours
    t.next_check_at = datetime.utcnow() + timedelta(hours=body.hours)
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


@tracker_router.put("/{tracker_id}")
async def update_tracker(
    tracker_id: int,
    body: TrackerUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(TrackedUrl).where(TrackedUrl.id == tracker_id, TrackedUrl.user_id == user.id)
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Tracker not found")

    if body.url is not None:
        if not is_public_http_url(body.url):
            raise HTTPException(status_code=400, detail="Only public http(s) product URLs are allowed")
        t.url = body.url

    if body.label is not None:
        t.label = body.label

    if body.check_frequency_hours is not None:
        if body.check_frequency_hours not in (1, 6, 12, 24):
            raise HTTPException(status_code=400, detail="Frequency must be 1, 6, 12, or 24 hours")
        plan, limits = await get_pricetrackr_limits(user, session)
        reject_price_frequency_if_needed(plan, limits, body.check_frequency_hours)
        t.check_frequency_hours = body.check_frequency_hours
        from datetime import timedelta
        t.next_check_at = datetime.utcnow() + timedelta(hours=body.check_frequency_hours)

    if body.alert_threshold is not None:
        t.alert_threshold = body.alert_threshold

    if body.selector_1 is not None:
        t.selector_1 = body.selector_1
    if body.selector_2 is not None:
        t.selector_2 = body.selector_2
    if body.selector_3 is not None:
        t.selector_3 = body.selector_3

    if body.slack_webhook_url is not None:
        t.slack_webhook_url = body.slack_webhook_url
    if body.discord_webhook_url is not None:
        t.discord_webhook_url = body.discord_webhook_url

    if body.is_public is not None:
        t.is_public = body.is_public

    session.add(t)
    await session.commit()
    return t


class ConfirmActionRequest(BaseModel):
    action: Literal["confirm", "dismiss"]


@tracker_router.post("/{tracker_id}/confirm")
async def confirm_tracker_change(
    tracker_id: int,
    body: ConfirmActionRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(TrackedUrl).where(TrackedUrl.id == tracker_id, TrackedUrl.user_id == user.id)
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Tracker not found")

    if body.action == "confirm":
        # Apply the pending changes
        previous_price = t.current_price
        previous_stock = t.in_stock
        previous_text = t.last_text

        t.previous_price = previous_price
        t.current_price = t.pending_price
        t.in_stock = t.pending_stock
        t.last_text = t.pending_text
        t.last_checked = datetime.utcnow()

        if t.pending_price is not None:
            if t.min_price is None or t.pending_price < t.min_price:
                t.min_price = t.pending_price

        # Record in price history
        history = PriceHistory(
            tracker_id=t.id,
            price=t.pending_price,
            in_stock=t.pending_stock,
            recorded_at=datetime.utcnow(),
            text_content=t.pending_text,
        )
        session.add(history)

        # Clear pending values
        t.pending_price = None
        t.pending_stock = None
        t.pending_text = None
        t.status = "active"

        session.add(t)
        await session.commit()

        # Send alerts
        await trigger_alerts(t, previous_price, t.current_price, previous_stock, t.in_stock, previous_text, t.last_text, session)
        await session.commit()
        return {"status": "confirmed"}
    else:
        # Dismiss pending changes
        t.pending_price = None
        t.pending_stock = None
        t.pending_text = None
        t.status = "active"
        session.add(t)
        await session.commit()
        return {"status": "dismissed"}



# ---------------------------------------------------------------------------
# Export endpoint — Skill: backend-architect
# ---------------------------------------------------------------------------
@tracker_router.post("/export")
async def trigger_export_job(
    format: Literal["csv", "xlsx", "json"] = Query(default="csv"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Trigger a background job to export trackers."""
    job = PriceTrackrExportJob(
        user_id=user.id,
        format=format,
        status="pending"
    )
    session.add(job)
    await session.flush()
    await session.refresh(job)

    # Enqueue in SystemOutbox
    outbox = SystemOutbox(
        app_name="pricetrackr",
        job_type="csv_export",
        payload={"job_id": str(job.id), "user_id": user.id, "format": format},
        status="pending"
    )
    session.add(outbox)
    await session.commit()

    return {
        "id": str(job.id),
        "status": job.status,
        "format": job.format,
        "created_at": job.created_at.isoformat()
    }


@tracker_router.get("/export/{job_id}")
async def get_export_job(
    job_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get the status and result of an export job."""
    result = await session.execute(
        select(PriceTrackrExportJob).where(PriceTrackrExportJob.id == job_id, PriceTrackrExportJob.user_id == user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")

    return {
        "id": str(job.id),
        "status": job.status,
        "format": job.format,
        "r2_url": job.r2_url,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat(),
        "completed_at": job.completed_at.isoformat() if job.completed_at else None
    }


# ---------------------------------------------------------------------------
# Alert threshold — Skill: backend-architect
# ---------------------------------------------------------------------------
class AlertThresholdRequest(BaseModel):
    alert_threshold: Optional[float] = None
    alert_email: Optional[str] = None

@tracker_router.patch("/{tracker_id}/alert-threshold")
async def update_alert_threshold(
    tracker_id: int,
    body: AlertThresholdRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Set a price alert threshold. Stores alert_email in TrackerSettings (no extra migration)."""
    result = await session.execute(select(TrackedUrl).where(TrackedUrl.id == tracker_id, TrackedUrl.user_id == user.id))
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Tracker not found")

    # Persist alert_email in TrackerSettings (already exists)
    if body.alert_email is not None:
        settings_res = await session.execute(select(TrackerSettings).where(TrackerSettings.user_id == user.id))
        user_settings = settings_res.scalar_one_or_none()
        if not user_settings:
            user_settings = TrackerSettings(user_id=user.id, alert_email=body.alert_email)
        else:
            user_settings.alert_email = body.alert_email
        session.add(user_settings)

    t.alert_threshold = body.alert_threshold
    session.add(t)
    await session.commit()
    return {"tracker_id": tracker_id, "alert_threshold": body.alert_threshold, "alert_email": body.alert_email}


@tracker_router.post("/{tracker_id}/test-alert")
async def test_price_alert(
    tracker_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Send a test alert email immediately to validate alert configuration."""
    result = await session.execute(select(TrackedUrl).where(TrackedUrl.id == tracker_id, TrackedUrl.user_id == user.id))
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Tracker not found")

    # Get alert email from user record
    alert_email = user.email
    price_display = f"${t.current_price:.2f}" if t.current_price else "N/A"
    html = f"""
    <div style="font-family:sans-serif;max-width:600px;margin:0 auto;">
      <h2 style="color:#6366f1;">&#128204; Price Alert Test — {t.label}</h2>
      <p>This is a <strong>test alert</strong> for your tracked product.</p>
      <table style="width:100%;border-collapse:collapse;">
        <tr><td style="padding:8px;border:1px solid #eee;">Product</td><td style="padding:8px;border:1px solid #eee;"><strong>{t.label}</strong></td></tr>
        <tr><td style="padding:8px;border:1px solid #eee;">Current Price</td><td style="padding:8px;border:1px solid #eee;"><strong style="color:#10B981;">{price_display}</strong></td></tr>
        <tr><td style="padding:8px;border:1px solid #eee;">URL</td><td style="padding:8px;border:1px solid #eee;"><a href="{t.url}">{t.url[:60]}...</a></td></tr>
      </table>
      <p style="margin-top:16px;color:#888;">Real alerts will be sent when the price drops below your configured threshold.</p>
    </div>
    """
    try:
        await asyncio.to_thread(send_email, to=alert_email, subject=f"[TEST] Price Alert — {t.label}", html_body=html)
        return {"status": "sent", "to": alert_email}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send test alert: {e}")


from fastapi import Response

public_router = APIRouter(prefix="/public/pricetrackr", tags=["public"])

class TakedownRequest(BaseModel):
    email: str
    reason: str

async def trigger_vercel_revalidation(slug: str):
    frontend_url = os.getenv("FRONTEND_URL") or settings.frontend_url
    secret = os.getenv("REVALIDATE_SECRET") or settings.jwt_secret
    if not frontend_url:
        logger.warning("FRONTEND_URL not configured. Skipping Vercel revalidation.")
        return
    url = f"{frontend_url.rstrip('/')}/api/revalidate"
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json={"secret": secret, "slug": slug})
            logger.info(f"Vercel revalidation for slug {slug} status: {resp.status_code}")
    except Exception as e:
        logger.error(f"Failed to trigger Vercel revalidation: {e}")

def generate_svg_chart(history_points: list) -> str:
    w = 600
    h = 240
    padding_x = 60
    padding_y = 40
    chart_w = w - padding_x * 2
    chart_h = h - padding_y * 2

    if not history_points:
        return f"""<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">
            <rect width="100%" height="100%" fill="#0a0a0a"/>
            <text x="{w//2}" y="{h//2}" fill="#888" font-family="sans-serif" font-size="14" text-anchor="middle">No price history available</text>
        </svg>"""

    prices = [p["price"] for p in history_points if p["price"] is not None]
    if not prices:
        return f"""<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">
            <rect width="100%" height="100%" fill="#0a0a0a"/>
            <text x="{w//2}" y="{h//2}" fill="#888" font-family="sans-serif" font-size="14" text-anchor="middle">No price history available</text>
        </svg>"""

    min_p = min(prices)
    max_p = max(prices)
    if max_p == min_p:
        min_p = max_p * 0.9 if max_p > 0 else -10
        max_p = max_p * 1.1 if max_p > 0 else 10

    diff = max_p - min_p
    min_p -= diff * 0.1
    max_p += diff * 0.1
    price_range = max_p - min_p

    points = []
    n = len(history_points)
    for i, pt in enumerate(history_points):
        if pt["price"] is None:
            continue
        x = padding_x + (i / max(1, n - 1)) * chart_w
        y = h - padding_y - ((pt["price"] - min_p) / price_range) * chart_h
        points.append((x, y))

    path_data = ""
    if points:
        path_data = f"M {points[0][0]},{points[0][1]} " + " ".join(f"L {x},{y}" for x, y in points[1:])

    area_path_data = ""
    if points:
        area_path_data = path_data + f" L {points[-1][0]},{h - padding_y} L {points[0][0]},{h - padding_y} Z"

    grid_lines = []
    grid_lines.append(f'<line x1="{padding_x}" y1="{padding_y}" x2="{padding_x}" y2="{h - padding_y}" stroke="#222" stroke-width="1"/>')
    grid_lines.append(f'<line x1="{w - padding_x}" y1="{padding_y}" x2="{w - padding_x}" y2="{h - padding_y}" stroke="#222" stroke-width="1"/>')

    labels = []
    for i in range(4):
        val = min_p + (i / 3) * price_range
        y = h - padding_y - (i / 3) * chart_h
        grid_lines.append(f'<line x1="{padding_x}" y1="{y}" x2="{w - padding_x}" y2="{y}" stroke="#1f1f1f" stroke-dasharray="3,3" stroke-width="1"/>')
        labels.append(f'<text x="{padding_x - 10}" y="{y + 4}" fill="#666" font-family="sans-serif" font-size="10" text-anchor="end">${val:,.2f}</text>')

    date_labels = []
    if len(history_points) > 1:
        try:
            first_date = datetime.fromisoformat(history_points[0]["recorded_at"]).strftime("%b %d")
            last_date = datetime.fromisoformat(history_points[-1]["recorded_at"]).strftime("%b %d")
        except Exception:
            first_date = "Start"
            last_date = "End"
        date_labels.append(f'<text x="{padding_x}" y="{h - padding_y + 18}" fill="#666" font-family="sans-serif" font-size="10" text-anchor="start">{first_date}</text>')
        date_labels.append(f'<text x="{w - padding_x}" y="{h - padding_y + 18}" fill="#666" font-family="sans-serif" font-size="10" text-anchor="end">{last_date}</text>')

    grid_str = "\n".join(grid_lines)
    label_str = "\n".join(labels)
    date_label_str = "\n".join(date_labels)

    points_svg = ""
    for x, y in points:
        points_svg += f'<circle cx="{x}" cy="{y}" r="3" fill="#6366f1" stroke="#0a0a0a" stroke-width="1"/>'

    svg = f"""<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="grad" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stop-color="#6366f1" stop-opacity="0.3"/>
                <stop offset="100%" stop-color="#6366f1" stop-opacity="0.0"/>
            </linearGradient>
        </defs>
        <rect width="100%" height="100%" fill="#0a0a0a" rx="12"/>
        {grid_str}
        {area_path_data and f'<path d="{area_path_data}" fill="url(#grad)"/>'}
        {path_data and f'<path d="{path_data}" fill="none" stroke="#6366f1" stroke-width="2"/>'}
        {points_svg}
        {label_str}
        {date_label_str}
    </svg>"""
    return svg

@public_router.post("/slug/{slug}/takedown")
async def request_takedown(
    slug: str,
    body: TakedownRequest,
    session: AsyncSession = Depends(get_session)
):
    """Public takedown request: unpublishes the product and triggers Vercel ISR revalidation."""
    result = await session.execute(select(TrackedUrl).where(TrackedUrl.slug == slug))
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Product not found")

    t.is_public = False
    session.add(t)
    await session.commit()

    await trigger_vercel_revalidation(t.slug)
    return {"status": "success", "message": "Product unpublished immediately."}

@public_router.get("/trackers/{tracker_id}/history.svg")
async def get_public_tracker_svg(
    tracker_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Generates an SVG chart for the price history of a tracker."""
    # Verify the tracker is public
    result = await session.execute(select(TrackedUrl).where(TrackedUrl.id == tracker_id))
    t = result.scalar_one_or_none()
    if not t or not t.is_public:
        raise HTTPException(status_code=404, detail="Tracker not found or not public")

    hist_res = await session.execute(
        select(PriceHistory)
        .where(PriceHistory.tracker_id == tracker_id)
        .order_by(PriceHistory.recorded_at.asc())
        .limit(30)
    )
    history = hist_res.scalars().all()
    points = [
        {
            "price": h.price,
            "recorded_at": h.recorded_at.isoformat(),
        }
        for h in history
    ]
    svg_content = generate_svg_chart(points)
    return Response(content=svg_content, media_type="image/svg+xml")


app = create_app(
    title="Price Tracker",
    description="Monitor competitor prices and get alerts",
    domain_routers=[tracker_router, settings_router, cron_router, public_router]
)

# Eliminado local APScheduler para compatibilidad con cron-job.org

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8003, reload=True)
