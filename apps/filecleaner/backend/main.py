import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "packages"))

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel, select
from typing import Optional
from datetime import datetime, timezone
import pandas as pd
import io
import boto3

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
        status="processing",
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)

    is_csv = record.original_name.lower().endswith('.csv')
    try:
        if is_csv:
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))
            
        df.dropna(how='all', inplace=True)
        df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        df.drop_duplicates(inplace=True)
        
        out_buf = io.BytesIO()
        if is_csv:
            df.to_csv(out_buf, index=False)
        else:
            df.to_excel(out_buf, index=False)
        out_buf.seek(0)
        
        bucket_name = os.getenv("R2_BUCKET_NAME")
        if bucket_name:
            s3 = boto3.client(
                's3',
                endpoint_url=os.getenv("R2_ENDPOINT_URL"),
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name="auto"
            )
            object_name = f"cleaned/{record.id}_{record.original_name}"
            s3.upload_fileobj(out_buf, bucket_name, object_name)
        
        record.status = "complete"
        record.download_url = f"/files/{record.id}/download"
        session.add(record)
        await session.commit()
        await session.refresh(record)
    except Exception as e:
        record.status = "error"
        session.add(record)
        await session.commit()

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

@file_router.get("/{file_id}/download")
async def download_file(
    file_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    record = await session.get(ProcessedFile, file_id)
    if not record or record.user_id != user.id:
        raise HTTPException(status_code=404, detail="File not found")
        
    bucket_name = os.getenv("R2_BUCKET_NAME")
    if bucket_name:
        s3 = boto3.client(
            's3',
            endpoint_url=os.getenv("R2_ENDPOINT_URL"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name="auto"
        )
        object_name = f"cleaned/{record.id}_{record.original_name}"
        url = s3.generate_presigned_url('get_object', Params={'Bucket': bucket_name, 'Key': object_name}, ExpiresIn=3600)
        return RedirectResponse(url)
    else:
        raise HTTPException(status_code=404, detail="Storage not configured")

@file_router.delete("/{file_id}")
async def delete_file(
    file_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    record = await session.get(ProcessedFile, file_id)
    if not record or record.user_id != user.id:
        raise HTTPException(status_code=404, detail="File not found")
        
    bucket_name = os.getenv("R2_BUCKET_NAME")
    if bucket_name:
        s3 = boto3.client(
            's3',
            endpoint_url=os.getenv("R2_ENDPOINT_URL"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name="auto"
        )
        object_name = f"cleaned/{record.id}_{record.original_name}"
        try:
            s3.delete_object(Bucket=bucket_name, Key=object_name)
        except Exception:
            pass
            
    await session.delete(record)
    await session.commit()
    return {"message": "Deleted successfully"}

# --- App ---
app = create_app(title="File Cleaner", description="Upload, process, and clean your files", domain_routers=[file_router])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
