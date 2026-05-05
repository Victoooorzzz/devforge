"""
Admin Router — Protected endpoint to view aggregate metrics across all 5 products.
Protected by ADMIN_SECRET environment variable (passed as Bearer token or X-Admin-Key header).
"""
import os
import logging
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text
from backend_core.database import get_managed_session

logger = logging.getLogger(__name__)

admin_router = APIRouter(prefix="/admin", tags=["admin"])


def _verify_admin(request: Request):
    secret = os.getenv("ADMIN_SECRET", "")
    if not secret:
        raise HTTPException(status_code=503, detail="Admin endpoint not configured")
    auth = request.headers.get("Authorization", "")
    key = request.headers.get("X-Admin-Key", "")
    token = auth.replace("Bearer ", "").strip()
    if token != secret and key != secret:
        raise HTTPException(status_code=403, detail="Forbidden")


@admin_router.get("/stats")
async def get_admin_stats(request: Request):
    """
    Returns aggregate metrics for all 5 micro-SaaS products.
    Protected by ADMIN_SECRET env var.
    """
    _verify_admin(request)

    async with get_managed_session() as session:
        stats: dict = {}

        # --- Users ---
        try:
            r = await session.execute(text("""
                SELECT
                    COUNT(*) as total_users,
                    COUNT(*) FILTER (WHERE is_active = true) as active_subscriptions,
                    COUNT(*) FILTER (
                        WHERE is_active = false
                        AND trial_ends_at > NOW()
                    ) as active_trials,
                    COUNT(*) FILTER (
                        WHERE is_active = false
                        AND trial_ends_at <= NOW()
                    ) as expired_trials
                FROM users
            """))
            row = r.mappings().first()
            stats["users"] = dict(row) if row else {}
        except Exception as e:
            logger.warning(f"Could not query users: {e}")
            stats["users"] = {"error": str(e)}

        # --- FileCleaner ---
        try:
            r = await session.execute(text("""
                SELECT
                    COUNT(*) as total_files,
                    COUNT(*) FILTER (WHERE status = 'complete') as files_cleaned,
                    SUM(rows_original - rows_clean) as total_rows_cleaned,
                    SUM(duplicates_removed) as total_duplicates_removed
                FROM processed_files
            """))
            row = r.mappings().first()
            stats["filecleaner"] = dict(row) if row else {}
        except Exception as e:
            stats["filecleaner"] = {"error": str(e)}

        # --- InvoiceFollow ---
        try:
            r = await session.execute(text("""
                SELECT
                    COUNT(*) as total_invoices,
                    COUNT(*) FILTER (WHERE status = 'paid') as paid_invoices,
                    COUNT(*) FILTER (WHERE status = 'overdue') as overdue_invoices,
                    SUM(amount) FILTER (WHERE status = 'paid') as total_revenue_tracked
                FROM invoices
            """))
            row = r.mappings().first()
            stats["invoicefollow"] = dict(row) if row else {}
        except Exception as e:
            stats["invoicefollow"] = {"error": str(e)}

        # --- PriceTrackr ---
        try:
            r = await session.execute(text("""
                SELECT
                    COUNT(*) as total_trackers,
                    COUNT(*) FILTER (WHERE status = 'active') as active_trackers,
                    COUNT(*) as total_price_checks
                FROM tracked_urls
            """))
            row = r.mappings().first()
            stats["pricetrackr"] = dict(row) if row else {}
        except Exception as e:
            stats["pricetrackr"] = {"error": str(e)}

        # --- WebhookMonitor ---
        try:
            r = await session.execute(text("""
                SELECT
                    COUNT(*) as total_webhooks_received,
                    COUNT(*) FILTER (WHERE received_at > NOW() - INTERVAL '24 hours') as webhooks_last_24h,
                    COUNT(*) FILTER (WHERE auto_retry_enabled = true) as pending_retries
                FROM webhook_requests
            """))
            row = r.mappings().first()
            stats["webhookmonitor"] = dict(row) if row else {}
        except Exception as e:
            stats["webhookmonitor"] = {"error": str(e)}

        # --- FeedbackLens ---
        try:
            r = await session.execute(text("""
                SELECT
                    COUNT(*) as total_feedback,
                    COUNT(*) FILTER (WHERE sentiment = 'negative') as negative_count,
                    COUNT(*) FILTER (WHERE sentiment = 'positive') as positive_count,
                    COUNT(*) FILTER (WHERE is_urgent = true) as urgent_count,
                    COUNT(*) FILTER (WHERE analysis_engine = 'gemini') as gemini_analyses,
                    COUNT(*) FILTER (WHERE analysis_engine = 'vader') as vader_analyses
                FROM feedback_entries
            """))
            row = r.mappings().first()
            stats["feedbacklens"] = dict(row) if row else {}
        except Exception as e:
            stats["feedbacklens"] = {"error": str(e)}

        # Convert all Decimal to float for JSON serialization
        import decimal
        def serialize(obj):
            if isinstance(obj, decimal.Decimal):
                return float(obj)
            return obj

        stats_serialized = {
            product: {k: serialize(v) for k, v in data.items()} if isinstance(data, dict) else data
            for product, data in stats.items()
        }

        return {
            "status": "ok",
            "generated_at": __import__("datetime").datetime.utcnow().isoformat(),
            "stats": stats_serialized,
        }
