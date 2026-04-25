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

# Importar modelos y routers de cada app
# Nota: Al importar los modelos aquí, SQLModel los registra para crearlos en la DB
from apps.feedbacklens.backend.main import feedback_router, FeedbackEntry
from apps.filecleaner.backend.main import file_router, ProcessedFile
from apps.invoicefollow.backend.main import invoice_router, Invoice, send_overdue_reminders
from apps.pricetrackr.backend.main import tracker_router, TrackedUrl, run_price_updates
from apps.webhookmonitor.backend.main import webhook_router as wm_router, ingestion_router, WebhookEndpoint, WebhookRequest

settings = get_settings()

# Unificar todos los routers de dominio
all_domain_routers = [
    feedback_router,
    file_router,
    invoice_router,
    tracker_router,
    wm_router,
    ingestion_router
]

app = create_app(
    title="DevForge Empire API",
    description="Unified API for all DevForge Micro-SaaS products",
    domain_routers=all_domain_routers
)

@app.on_event("startup")
async def schedule_all_jobs():
    # Tareas de InvoiceFollow (Cada día a las 9 AM)
    app.state.scheduler.add_job(
        send_overdue_reminders,
        "cron",
        hour=9,
        minute=0,
        id="invoice_reminder_job"
    )
    
    # Tareas de PriceTrackr (Cada 24 horas)
    app.state.scheduler.add_job(
        run_price_updates,
        "interval",
        hours=24,
        id="price_update_job"
    )

if __name__ == "__main__":
    import uvicorn
    # En producción se usará el comando de Railway/Render
    uvicorn.run("packages.backend_core.universal_main:app", host="0.0.0.0", port=8000, reload=True)
