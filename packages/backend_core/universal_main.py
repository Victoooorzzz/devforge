# packages/backend_core/universal_main.py

import sys
import os
from typing import List
from fastapi import APIRouter

# Asegurar que el path incluya la raíz y packages para los imports
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
packages_path = os.path.join(root_path, "packages")
sys.path.insert(0, root_path)
sys.path.insert(0, packages_path)

from backend_core.main_factory import create_app
from backend_core.config import get_settings

# --- Importar modelos y routers de cada app ---
# Al importar los modelos aquí, SQLModel los registra para crear las tablas en la DB

# FeedbackLens
from apps.feedbacklens.backend.main import (
    feedback_router,
    settings_router as fl_settings_router,
    FeedbackEntry,
    FeedbackSettings,
    weekly_summary_cron,
)

# FileCleaner
from apps.filecleaner.backend.main import (
    file_router,
    ProcessedFile,
    cron_cleanup_files,
)

# InvoiceFollow
from apps.invoicefollow.backend.main import (
    invoice_router,
    settings_router as iv_settings_router,
    public_router as iv_public_router,
    Invoice,
    InvoiceSettings,
    enqueue_overdue_reminders,
)

# PriceTrackr
from apps.pricetrackr.backend.main import (
    tracker_router,
    settings_router as pt_settings_router,
    TrackedUrl,
    PriceHistory,
    TrackerSettings,
    run_price_updates,
)

# WebhookMonitor
from apps.webhookmonitor.backend.main import (
    webhook_router as wm_router,
    ingestion_router,
    settings_router as wm_settings_router,
    WebhookEndpoint,
    WebhookRequest,
    WebhookSettings,
    check_webhook_silences,
    cleanup_old_logs,
)

# Admin
from backend_core.admin_router import admin_router

settings = get_settings()

# Unificar todos los routers de dominio
all_domain_routers = [
    # FeedbackLens
    feedback_router,
    fl_settings_router,
    # FileCleaner
    file_router,
    # InvoiceFollow
    invoice_router,
    iv_settings_router,
    iv_public_router,
    # PriceTrackr
    tracker_router,
    pt_settings_router,
    # WebhookMonitor
    wm_router,
    ingestion_router,
    wm_settings_router,
    # Admin
    admin_router,
]

app = create_app(
    title="DevForge Empire API",
    description="Unified API for all DevForge Micro-SaaS products",
    domain_routers=all_domain_routers
)

from fastapi import Depends
from backend_core.worker import run_worker_cycle, verify_cron_secret

# --- Master Enqueuer for cron-job.org ---
@app.post("/worker/enqueue-periodic", tags=["Worker"])
async def enqueue_periodic_tasks(authenticated: bool = Depends(verify_cron_secret)):
    """
    Master trigger for all periodic tasks across all products.
    Should be called every hour by cron-job.org.
    It enqueues due periodic work and then runs one worker cycle.
    """
    
    results = {}
    
    # 1. PriceTrackr: Check which prices need updating
    try:
        await run_price_updates()
        results["pricetrackr"] = "enqueued"
    except Exception as e:
        results["pricetrackr"] = f"error: {str(e)}"
        
    # 2. InvoiceFollow: Check for overdue invoices
    try:
        await enqueue_overdue_reminders()
        results["invoicefollow"] = "enqueued"
    except Exception as e:
        results["invoicefollow"] = f"error: {str(e)}"
        
    # 3. FeedbackLens: Send weekly summaries (internally checks day of week)
    try:
        await weekly_summary_cron()
        results["feedbacklens"] = "enqueued"
    except Exception as e:
        results["feedbacklens"] = f"error: {str(e)}"

    # 4. WebhookMonitor: Silence checks and log cleanup
    try:
        await check_webhook_silences()
        await cleanup_old_logs()
        results["webhookmonitor"] = "enqueued"
    except Exception as e:
        results["webhookmonitor"] = f"error: {str(e)}"

    # 5. FileCleaner: Delete files older than 24h
    try:
        count = await cron_cleanup_files()
        results["filecleaner"] = f"cleaned {count} files"
    except Exception as e:
        results["filecleaner"] = f"error: {str(e)}"

    processed_jobs = await run_worker_cycle()
    return {"status": "success", "results": results, "processed_jobs": processed_jobs}

if __name__ == "__main__":
    import uvicorn
    # En producción se usará el comando de Railway/Render
    uvicorn.run("packages.backend_core.universal_main:app", host="0.0.0.0", port=8000, reload=True)
