import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "packages"))

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel, select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date, timezone
import logging

from backend_core import create_app, get_current_user, get_session, User
from backend_core.email_service import send_email

logger = logging.getLogger(__name__)

class Invoice(SQLModel, table=True):
    __tablename__ = "invoices"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    client_name: str
    client_email: str = Field(default="")
    amount: float
    due_date: date
    status: str = Field(default="pending")
    reminders_sent: int = Field(default=0)
    last_reminder_date: Optional[date] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class InvoiceSettings(SQLModel, table=True):
    __tablename__ = "invoice_settings"
    user_id: int = Field(primary_key=True)
    email_template: str = Field(default="Hello {client_name}, your invoice for {amount} is past due. Please settle it soon.")

class InvoiceCreate(BaseModel):
    client_name: str
    client_email: str
    amount: float
    due_date: date

class InvoiceTemplateUpdate(BaseModel):
    email_template: str

invoice_router = APIRouter(prefix="/invoices", tags=["invoices"])
settings_router = APIRouter(prefix="/settings", tags=["settings"])

@settings_router.get("/invoice-template")
async def get_invoice_template(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(InvoiceSettings).where(InvoiceSettings.user_id == user.id))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = InvoiceSettings(user_id=user.id)
        session.add(settings)
        await session.flush()
    return {"email_template": settings.email_template}

@settings_router.put("/invoice-template")
async def update_invoice_template(body: InvoiceTemplateUpdate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(InvoiceSettings).where(InvoiceSettings.user_id == user.id))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = InvoiceSettings(user_id=user.id, email_template=body.email_template)
    else:
        settings.email_template = body.email_template
    session.add(settings)
    await session.flush()
    return {"email_template": settings.email_template}

async def send_overdue_reminders():
    """Background task specifically for Railway (Long-running process)."""
    from backend_core.database import SessionLocal
    from datetime import timedelta
    async with SessionLocal() as session:
        today = date.today()
        # Find pending invoices past due date
        result = await session.execute(
            select(Invoice).where(Invoice.status == "pending", Invoice.due_date < today)
        )
        overdue_list = result.scalars().all()
        for inv in overdue_list:
            # Anti-Spam: Only send if never sent or at least 3 days passed
            if inv.last_reminder_date and (today - inv.last_reminder_date).days < 3:
                continue

            # Get user custom template
            settings_req = await session.execute(
                select(InvoiceSettings).where(InvoiceSettings.user_id == inv.user_id)
            )
            user_settings = settings_req.scalar_one_or_none()
            
            raw_template = user_settings.email_template if user_settings else "Hello {client_name}, your invoice for {amount} is past due. Please settle it soon."
            
            # Personalize template
            final_content = raw_template.replace("{amount}", f"${inv.amount:,.2f}").replace("{client_name}", inv.client_name)

            logger.info(f"Sending reminder for invoice {inv.id} to {inv.client_email}")
            send_email(
                to=inv.client_email,
                subject=f"Action Required: Overdue Invoice for {inv.client_name}",
                html_body=final_content
            )
            inv.reminders_sent += 1
            inv.last_reminder_date = today
            session.add(inv)
        await session.commit()

@invoice_router.post("")
async def create_invoice(body: InvoiceCreate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    if not user.has_access:
        raise HTTPException(status_code=403, detail="Active subscription or trial required")
    inv = Invoice(user_id=user.id, client_name=body.client_name, client_email=body.client_email, amount=body.amount, due_date=body.due_date)
    session.add(inv)
    await session.flush()
    await session.refresh(inv)
    return inv

@invoice_router.get("/list")
async def list_invoices(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Invoice).where(Invoice.user_id == user.id).order_by(Invoice.due_date))
    return result.scalars().all()

@invoice_router.put("/{invoice_id}/mark-paid")
async def mark_paid(invoice_id: int, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Invoice).where(Invoice.id == invoice_id, Invoice.user_id == user.id))
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    inv.status = "paid"
    session.add(inv)
    await session.flush()
    return {"status": "paid"}

app = create_app(
    title="Invoice Follow-up", 
    description="Track invoices and automate payment reminders", 
    domain_routers=[invoice_router, settings_router]
)

@app.on_event("startup")
async def schedule_reminder_job():
    # Railway long-running job: check every day at 9 AM
    app.state.scheduler.add_job(
        send_overdue_reminders,
        "cron",
        hour=9,
        minute=0,
        id="invoice_reminder_job"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
