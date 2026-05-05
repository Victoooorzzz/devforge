import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "packages"))

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel, select
from typing import Optional
from datetime import datetime, timezone
import pandas as pd
import io
import boto3
import logging

from fastapi.concurrency import run_in_threadpool
from backend_core import create_app, get_current_user, get_session, User, require_user_access
from backend_core.database import get_managed_session
from backend_core.outbox_models import SystemOutbox
from backend_core.worker import register_job_handler

logger = logging.getLogger(__name__)

# ALTER TABLE processed_files ADD COLUMN IF NOT EXISTS whitespace_fixed INTEGER DEFAULT 0;
# ALTER TABLE processed_files ADD COLUMN IF NOT EXISTS job_status VARCHAR DEFAULT 'queued';

async def cron_cleanup_files():
    """
    Periodic task to delete files older than 24 hours from S3/R2 and database.
    """
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    
    async with get_managed_session() as session:
        result = await session.execute(
            select(ProcessedFile).where(ProcessedFile.created_at < cutoff)
        )
        old_files = result.scalars().all()
        
        if not old_files:
            return 0
            
        bucket_name = os.getenv("R2_BUCKET_NAME")
        s3 = _get_s3_client()
        
        count = 0
        for f in old_files:
            # Delete from R2
            if bucket_name:
                for prefix in ["raw", "cleaned", "magic-clean"]:
                    try:
                        s3.delete_object(Bucket=bucket_name, Key=f"{prefix}/{f.id}_{f.original_name}")
                    except:
                        pass
            # Delete from DB
            await session.delete(f)
            count += 1
            
        await session.commit()
        return count

MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB


# --- Models ---
class ProcessedFile(SQLModel, table=True):
    __tablename__ = "processed_files"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    original_name: str
    size_bytes: int
    status: str = Field(default="queued")    # "queued" | "processing" | "complete" | "error"
    download_url: Optional[str] = None
    # Cleanup stats
    rows_original: int = Field(default=0)
    rows_clean: int = Field(default=0)
    duplicates_removed: int = Field(default=0)
    empty_removed: int = Field(default=0)
    whitespace_fixed: int = Field(default=0)
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def _get_s3_client():
    return boto3.client(
        's3',
        endpoint_url=os.getenv("S3_ENDPOINT_URL"),
        aws_access_key_id=os.getenv("S3_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY"),
        region_name="auto"
    )

def _load_df(content: bytes, filename: str) -> pd.DataFrame:
    if filename.lower().endswith('.csv'):
        return pd.read_csv(io.BytesIO(content))
    return pd.read_excel(io.BytesIO(content))

def _save_df(df: pd.DataFrame, filename: str) -> io.BytesIO:
    buf = io.BytesIO()
    if filename.lower().endswith('.csv'):
        df.to_csv(buf, index=False)
    else:
        df.to_excel(buf, index=False)
    buf.seek(0)
    return buf


async def handle_process_csv(payload: dict):
    record_id = payload["record_id"]
    object_key = payload["object_key"]
    filename = payload["filename"]
    
    bucket_name = os.getenv("R2_BUCKET_NAME")
    s3 = _get_s3_client()
    
    # Download raw file
    raw_buf = io.BytesIO()
    s3.download_fileobj(bucket_name, object_key, raw_buf)
    content = raw_buf.getvalue()

    async with get_managed_session() as session:
        record = await session.get(ProcessedFile, record_id)
        if not record:
            return

        try:
            record.status = "processing"
            session.add(record)
            await session.commit()

            def process_dataframe(file_content: bytes, fname: str):
                df = _load_df(file_content, fname)
                rows_original = len(df)

                # Step 1: Remove completely empty rows
                df_before_empty = len(df)
                df.dropna(how='all', inplace=True)
                empty_removed = df_before_empty - len(df)

                # Step 2: Strip whitespace on string columns
                ws_fixed = 0
                for col in df.select_dtypes(include='object').columns:
                    stripped = df[col].str.strip()
                    ws_fixed += (stripped != df[col]).sum()
                    df[col] = stripped

                # Step 3: Remove exact duplicates
                df_before_dup = len(df)
                df.drop_duplicates(inplace=True)
                duplicates_removed = df_before_dup - len(df)

                rows_clean = len(df)
                buf = _save_df(df, fname)
                return buf, rows_original, rows_clean, duplicates_removed, empty_removed, int(ws_fixed)

            out_buf, rows_original, rows_clean, dups, empty, ws = await run_in_threadpool(
                process_dataframe, content, filename
            )

            object_name = f"cleaned/{record.id}_{filename}"
            s3.upload_fileobj(out_buf, bucket_name, object_name)

            record.status = "complete"
            record.download_url = f"/files/{record.id}/download"
            record.rows_original = rows_original
            record.rows_clean = rows_clean
            record.duplicates_removed = dups
            record.empty_removed = empty
            record.whitespace_fixed = ws

        except Exception as e:
            logger.error(f"Background file processing failed for record {record_id}: {e}")
            record.status = "error"
            record.error_message = str(e)[:500]

        session.add(record)
        await session.commit()

register_job_handler("filecleaner", "process_csv", handle_process_csv)


# --- Routers ---
file_router = APIRouter(prefix="/files", tags=["files"], dependencies=[Depends(require_user_access)])
settings_router = APIRouter(prefix="/settings", tags=["settings"])


@file_router.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Accepts a file, creates a DB record immediately (status=queued), and
    processes it in the background. Returns {id, status} so the client can poll.
    """
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (200MB max)")

    ext = (file.filename or "file.csv").rsplit(".", 1)[-1].lower()
    if ext not in ("csv", "xlsx", "xls"):
        raise HTTPException(status_code=400, detail="Unsupported file type. Use CSV or Excel.")

    record = ProcessedFile(
        user_id=user.id,
        original_name=file.filename or "unnamed",
        size_bytes=len(content),
        status="queued",
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)

    # Upload raw to R2
    bucket_name = os.getenv("R2_BUCKET_NAME")
    if not bucket_name:
        raise HTTPException(status_code=500, detail="Storage not configured")
        
    s3 = _get_s3_client()
    raw_key = f"raw/{record.id}_{record.original_name}"
    s3.upload_fileobj(io.BytesIO(content), bucket_name, raw_key)

    # Enqueue to system_outbox
    job = SystemOutbox(
        app_name="filecleaner",
        job_type="process_csv",
        payload={
            "record_id": record.id,
            "object_key": raw_key,
            "filename": record.original_name
        },
        priority=5
    )
    session.add(job)
    await session.commit()

    return {"id": record.id, "status": "queued", "name": record.original_name}


@file_router.get("/{file_id}/status")
async def get_file_status(
    file_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Poll endpoint — returns current processing status and report when complete."""
    record = await session.get(ProcessedFile, file_id)
    if not record or record.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")

    response: dict = {
        "id": record.id,
        "name": record.original_name,
        "status": record.status,
    }

    if record.status == "complete":
        response["download_url"] = record.download_url
        response["report"] = {
            "rows_original": record.rows_original,
            "rows_clean": record.rows_clean,
            "duplicates_removed": record.duplicates_removed,
            "empty_removed": record.empty_removed,
            "whitespace_fixed": record.whitespace_fixed,
            "rows_saved": record.rows_original - record.rows_clean,
            "reduction_pct": round((1 - record.rows_clean / max(record.rows_original, 1)) * 100, 1),
        }
    elif record.status == "error":
        response["error"] = record.error_message

    return response


@file_router.get("/list")
async def list_files(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(ProcessedFile)
        .where(ProcessedFile.user_id == user.id)
        .order_by(ProcessedFile.created_at.desc())
        .limit(50)
    )
    files = result.scalars().all()
    return [
        {
            "id": f.id,
            "name": f.original_name,
            "size": f.size_bytes,
            "status": f.status,
            "download_url": f.download_url,
            "report": {
                "rows_original": f.rows_original,
                "rows_clean": f.rows_clean,
                "duplicates_removed": f.duplicates_removed,
                "empty_removed": f.empty_removed,
                "whitespace_fixed": f.whitespace_fixed,
                "rows_saved": f.rows_original - f.rows_clean,
                "reduction_pct": round((1 - f.rows_clean / max(f.rows_original, 1)) * 100, 1),
            } if f.status == "complete" else None,
        }
        for f in files
    ]


@file_router.post("/fuzzy-check")
async def fuzzy_check(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    threshold: int = 85,
):
    """
    Detecta duplicados 'blandos' usando fuzzy matching (thefuzz).
    threshold: similitud mínima 0-100 (default 85).
    """
    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Fuzzy check limited to 20MB")

    def run_fuzzy(file_content: bytes, fname: str, thresh: int):
        try:
            from thefuzz import fuzz
        except ImportError:
            return {"error": "thefuzz not installed. Run: pip install thefuzz[speedup]", "groups": []}

        df = _load_df(file_content, fname)
        str_rows = df.astype(str).apply(lambda r: " | ".join(r.values), axis=1).tolist()
        n = len(str_rows)
        visited = set()
        groups = []

        for i in range(n):
            if i in visited:
                continue
            group = [i]
            for j in range(i + 1, n):
                if j in visited:
                    continue
                score = fuzz.token_sort_ratio(str_rows[i], str_rows[j])
                if score >= thresh:
                    group.append(j)
                    visited.add(j)
            if len(group) > 1:
                visited.add(i)
                groups.append({"rows": group, "sample": str_rows[i][:200], "count": len(group)})

        return {
            "total_rows": n,
            "fuzzy_groups_found": len(groups),
            "rows_affected": sum(g["count"] for g in groups),
            "threshold_used": thresh,
            "groups": groups[:50],
        }

    return await run_in_threadpool(run_fuzzy, content, file.filename or "file.csv", threshold)


@file_router.post("/magic-clean")
async def magic_clean(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Normalización avanzada: estandariza fechas, teléfonos, emails, precios.
    Procesa en background y retorna un job_id para polling.
    """
    content = await file.read()

    record = ProcessedFile(
        user_id=user.id,
        original_name=file.filename or "unnamed",
        size_bytes=len(content),
        status="queued",
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)

    # Upload raw to R2
    bucket_name = os.getenv("R2_BUCKET_NAME")
    if not bucket_name:
        raise HTTPException(status_code=500, detail="Storage not configured")
        
    s3 = _get_s3_client()
    raw_key = f"raw/{record.id}_{record.original_name}"
    s3.upload_fileobj(io.BytesIO(content), bucket_name, raw_key)

    # Enqueue to system_outbox
    job = SystemOutbox(
        app_name="filecleaner",
        job_type="magic_clean",
        payload={
            "record_id": record.id,
            "object_key": raw_key,
            "filename": record.original_name
        },
        priority=5
    )
    session.add(job)
    await session.commit()

    return {"id": record.id, "status": "queued"}

async def handle_magic_clean(payload: dict):
    record_id = payload["record_id"]
    object_key = payload["object_key"]
    filename = payload["filename"]
    
    bucket_name = os.getenv("R2_BUCKET_NAME")
    s3 = _get_s3_client()
    
    # Download raw file
    raw_buf = io.BytesIO()
    s3.download_fileobj(bucket_name, object_key, raw_buf)
    content = raw_buf.getvalue()

    async with get_managed_session() as bg_session:
        rec = await bg_session.get(ProcessedFile, record_id)
        if not rec:
            return
        try:
            import re
            rec.status = "processing"
            bg_session.add(rec)
            await bg_session.commit()

            def run_magic(fc: bytes, fn: str):
                df = _load_df(fc, fn)
                for col in df.columns:
                    col_lower = col.lower()
                    s = df[col]
                    if any(k in col_lower for k in ["email", "correo", "mail"]):
                        df[col] = s.astype(str).str.strip().str.lower()
                    elif any(k in col_lower for k in ["phone", "telefono", "tel", "celular"]):
                        def norm_phone(v):
                            if pd.isna(v): return v
                            d = re.sub(r"\D", "", str(v))
                            if len(d) == 9: return f"+51 {d[:3]} {d[3:6]} {d[6:]}"
                            if len(d) == 10: return f"+1 ({d[:3]}) {d[3:6]}-{d[6:]}"
                            return d if d else str(v)
                        df[col] = s.apply(norm_phone)
                    elif any(k in col_lower for k in ["price", "precio", "amount", "monto", "cost", "total"]):
                        def clean_price(v):
                            if pd.isna(v): return v
                            cleaned = re.sub(r"[^\d.,]", "", str(v)).replace(",", ".")
                            try: return float(cleaned)
                            except: return v
                        df[col] = s.apply(clean_price)
                    elif any(k in col_lower for k in ["date", "fecha", "created", "updated"]):
                        df[col] = pd.to_datetime(s, dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d').where(
                            pd.to_datetime(s, dayfirst=True, errors='coerce').notna(), other=s.astype(str)
                        )
                    elif any(k in col_lower for k in ["name", "nombre", "city", "ciudad"]):
                        df[col] = s.astype(str).str.strip().str.title()
                rows_before = len(df)
                df.dropna(how='all', inplace=True)
                df.drop_duplicates(inplace=True)
                return df, rows_before, len(df)

            df_clean, rows_orig, rows_clean = await run_in_threadpool(run_magic, content, filename)
            out_buf = _save_df(df_clean, filename)

            object_name = f"magic-clean/{rec.id}_{filename}"
            s3.upload_fileobj(out_buf, bucket_name, object_name)

            rec.status = "complete"
            rec.download_url = f"/files/{rec.id}/download"
            rec.rows_original = rows_orig
            rec.rows_clean = rows_clean
        except Exception as e:
            logger.error(f"Magic clean failed for {record_id}: {e}", exc_info=True)
            rec.status = "error"
            rec.error_message = str(e)[:500]
        bg_session.add(rec)
        await bg_session.commit()

register_job_handler("filecleaner", "magic_clean", handle_magic_clean)


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
        s3 = _get_s3_client()
        object_name = f"cleaned/{record.id}_{record.original_name}"
        url = s3.generate_presigned_url('get_object', Params={'Bucket': bucket_name, 'Key': object_name}, ExpiresIn=3600)
        return RedirectResponse(url)
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
        s3 = _get_s3_client()
        for prefix in ["cleaned", "magic-clean"]:
            try:
                s3.delete_object(Bucket=bucket_name, Key=f"{prefix}/{record.id}_{record.original_name}")
            except Exception:
                pass

    await session.delete(record)
    await session.commit()
    return {"message": "Deleted successfully"}


# --- App ---
app = create_app(
    title="File Cleaner",
    description="Upload, process, and clean your CSV/Excel datasets",
    domain_routers=[file_router, settings_router]
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
