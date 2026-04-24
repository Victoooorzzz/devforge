import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "packages"))

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel, select
from typing import Optional
from datetime import datetime, timezone

from backend_core import create_app, get_current_user, get_session, User

# --- Models ---
class ProcessedFile(SQLModel, table=True):
    __tablename__ = "processed_files"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    original_name: str
    size_bytes: int
    status: str = Field(default="processing")
    download_url: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# --- Router ---
file_router = APIRouter(prefix="/files", tags=["files"])

@file_router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Active subscription required")

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (50 MB max)")

    record = ProcessedFile(
        user_id=user.id,
        original_name=file.filename or "unnamed",
        size_bytes=len(content),
        status="complete",
        download_url=f"/files/download/{file.filename}",
    )
    session.add(record)
    await session.flush()
    await session.refresh(record)

    return {"id": record.id, "status": record.status, "download_url": record.download_url}

@file_router.get("/list")
async def list_files(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(ProcessedFile).where(ProcessedFile.user_id == user.id).order_by(ProcessedFile.created_at.desc())
    )
    return [{"id": f.id, "name": f.original_name, "size": f.size_bytes, "status": f.status, "download_url": f.download_url, "created_at": f.created_at.isoformat()} for f in result.scalars().all()]

# --- App ---
app = create_app(title="File Cleaner", description="Upload, process, and clean your files", domain_routers=[file_router])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
