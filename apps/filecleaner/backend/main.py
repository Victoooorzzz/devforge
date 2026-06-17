import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "packages"))

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, BackgroundTasks, Query
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel, select
from typing import Optional, Literal
from datetime import datetime, timezone
import pandas as pd
import io
import json
import boto3
import logging

from fastapi.concurrency import run_in_threadpool
from backend_core import create_app, get_current_user, get_session, User, require_product_access, get_settings
from backend_core.database import get_managed_session
from backend_core.data_limits import DEFAULT_MAX_FUZZY_ROWS, is_fuzzy_row_count_allowed
from backend_core.file_utilities import process_image_file
from backend_core.outbox_models import SystemOutbox
from backend_core.product_insights import summarize_files
from backend_core.worker import register_job_handler

settings = get_settings()

logger = logging.getLogger(__name__)

# ALTER TABLE processed_files ADD COLUMN IF NOT EXISTS whitespace_fixed INTEGER DEFAULT 0;
# ALTER TABLE processed_files ADD COLUMN IF NOT EXISTS job_status VARCHAR DEFAULT 'queued';

async def cron_cleanup_files():
    """
    Periodic task to delete files older than 24 hours from S3/R2 and database.
    """
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(hours=24)
    
    async with get_managed_session() as session:
        result = await session.execute(
            select(ProcessedFile).where(ProcessedFile.created_at < cutoff)
        )
        old_files = result.scalars().all()
        
        if not old_files:
            return 0
            
        bucket_name = settings.s3_bucket_name
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
    created_at: datetime = Field(default_factory=datetime.utcnow)


def _get_s3_client():
    return boto3.client(
        's3',
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
        region_name="auto"
    )

def _load_df(content: bytes, filename: str) -> pd.DataFrame:
    normalized = filename.lower()
    if normalized.endswith('.csv'):
        return pd.read_csv(io.BytesIO(content))
    if normalized.endswith('.json'):
        df = pd.read_json(io.BytesIO(content))
        if isinstance(df, pd.Series):
            df = df.to_frame().T
        return df
    return pd.read_excel(io.BytesIO(content))

def _save_df(df: pd.DataFrame, filename: str) -> io.BytesIO:
    buf = io.BytesIO()
    normalized = filename.lower()
    if normalized.endswith('.csv'):
        df.to_csv(buf, index=False)
    elif normalized.endswith('.json'):
        buf.write(df.to_json(orient="records", force_ascii=False, indent=2).encode("utf-8"))
    else:
        df.to_excel(buf, index=False)
    buf.seek(0)
    return buf


async def handle_process_csv(payload: dict):
    record_id = payload["record_id"]
    object_key = payload["object_key"]
    filename = payload["filename"]
    
    bucket_name = settings.s3_bucket_name
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
file_router = APIRouter(prefix="/files", tags=["files"], dependencies=[Depends(require_product_access("filecleaner"))])
demo_router = APIRouter(prefix="/files", tags=["demo"])
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
    # Get file size without reading into memory
    file_size = file.size or 0
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (200MB max)")

    ext = (file.filename or "file.csv").rsplit(".", 1)[-1].lower()
    if ext not in ("csv", "xlsx", "xls", "json"):
        raise HTTPException(status_code=400, detail="Unsupported file type. Use CSV, JSON, or Excel.")

    record = ProcessedFile(
        user_id=user.id,
        original_name=file.filename or "unnamed",
        size_bytes=file_size,
        status="queued",
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)

    # Upload raw to R2 via streaming
    bucket_name = settings.s3_bucket_name
    if not bucket_name:
        raise HTTPException(status_code=500, detail="Storage not configured")
        
    s3 = _get_s3_client()
    raw_key = f"raw/{record.id}_{record.original_name}"
    
    # Run upload_fileobj in a threadpool to avoid blocking event loop
    await run_in_threadpool(
        s3.upload_fileobj, file.file, bucket_name, raw_key
    )

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


@file_router.post("/utility")
async def process_file_utility(
    file: UploadFile = File(...),
    output_format: Optional[Literal["png", "jpg", "jpeg", "webp"]] = Query(default=None),
    quality: int = Query(default=82, ge=1, le=95),
    user: User = Depends(get_current_user),
):
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Utility processing is limited to 50MB")

    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in {"png", "jpg", "jpeg", "webp", "heic", "heif", "svg", "pdf"}:
        raise HTTPException(status_code=400, detail="Use PNG, JPG, WEBP, HEIC, SVG, or PDF.")

    try:
        processed = await run_in_threadpool(
            process_image_file,
            content,
            file.filename or "file",
            output_format=output_format,
            quality=quality,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    headers = {
        "Content-Disposition": f'attachment; filename="{processed.filename}"',
        "X-DevForge-Metadata-Removed": "true" if processed.metadata_removed else "false",
        "X-DevForge-Bytes-Saved": str(processed.bytes_saved),
        "X-DevForge-Output-Count": str(processed.output_count),
    }
    return StreamingResponse(io.BytesIO(processed.content), media_type=processed.media_type, headers=headers)


@demo_router.post("/demo/upload")
async def demo_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    """
    Public demo endpoint — no signup required.
    Uses a hardcoded GUEST_USER_ID (0).
    """
    GUEST_USER_ID = 0
    file_size = file.size or 0
    if file_size > 5 * 1024 * 1024:  # Limit demo to 5MB
        raise HTTPException(status_code=413, detail="Demo limited to 5MB")

    ext = (file.filename or "demo_file.csv").rsplit(".", 1)[-1].lower()
    if ext not in ("csv", "xlsx", "xls", "json"):
        raise HTTPException(status_code=400, detail="Unsupported file type. Use CSV, JSON, or Excel.")

    record = ProcessedFile(
        user_id=GUEST_USER_ID,
        original_name=file.filename or "demo_file.csv",
        size_bytes=file_size,
        status="queued",
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)

    bucket_name = settings.s3_bucket_name
    if not bucket_name:
        raise HTTPException(status_code=500, detail="Storage not configured")
        
    s3 = _get_s3_client()
    raw_key = f"demo/{record.id}_{record.original_name}"
    
    # Run upload_fileobj in a threadpool to avoid blocking event loop
    await run_in_threadpool(
        s3.upload_fileobj, file.file, bucket_name, raw_key
    )

    job = SystemOutbox(
        app_name="filecleaner",
        job_type="process_csv",
        payload={
            "record_id": record.id,
            "object_key": raw_key,
            "filename": record.original_name
        },
        priority=10 # Demo jobs have lower priority
    )
    session.add(job)
    await session.commit()

    return {"id": record.id, "status": "queued", "name": record.original_name}


@demo_router.get("/demo/{file_id}/status")
async def get_demo_file_status(
    file_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Public poll endpoint for demo."""
    record = await session.get(ProcessedFile, file_id)
    if not record or record.user_id != 0:
        raise HTTPException(status_code=404, detail="Demo file not found")

    response: dict = {
        "id": record.id,
        "name": record.original_name,
        "status": record.status,
    }

    if record.status == "complete":
        response["download_url"] = f"/files/demo/{record.id}/download"
        response["report"] = {
            "rows_original": record.rows_original,
            "rows_clean": record.rows_clean,
            "duplicates_removed": record.duplicates_removed,
            "empty_removed": record.empty_removed,
            "whitespace_fixed": record.whitespace_fixed,
            "rows_saved": record.rows_original - record.rows_clean,
            "reduction_pct": round((1 - record.rows_clean / max(record.rows_original, 1)) * 100, 1),
        }
    return response


@demo_router.get("/demo/{file_id}/download")
async def download_demo_file(
    file_id: int,
    session: AsyncSession = Depends(get_session),
):
    record = await session.get(ProcessedFile, file_id)
    if not record or record.user_id != 0:
        raise HTTPException(status_code=404, detail="File not found")

    bucket_name = settings.s3_bucket_name
    if bucket_name:
        s3 = _get_s3_client()
        object_name = f"cleaned/{record.id}_{record.original_name}"
        url = s3.generate_presigned_url('get_object', Params={'Bucket': bucket_name, 'Key': object_name}, ExpiresIn=3600)
        return RedirectResponse(url)
    raise HTTPException(status_code=404, detail="Storage not configured")


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


@file_router.get("/summary")
async def get_file_summary(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(ProcessedFile)
        .where(ProcessedFile.user_id == user.id)
        .order_by(ProcessedFile.created_at.desc())
        .limit(500)
    )
    return summarize_files(result.scalars().all())


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
        if not is_fuzzy_row_count_allowed(n):
            return {
                "error": f"Fuzzy check limited to {DEFAULT_MAX_FUZZY_ROWS} rows",
                "code": "too_many_rows",
                "total_rows": n,
                "groups": [],
            }
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

    result = await run_in_threadpool(run_fuzzy, content, file.filename or "file.csv", threshold)
    if result.get("code") == "too_many_rows":
        raise HTTPException(status_code=413, detail=result["error"])
    return result


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
    bucket_name = settings.s3_bucket_name
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
    
    bucket_name = settings.s3_bucket_name
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
            rec.download_url = f"/files/{rec.id}/download?type=magic"
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
    type: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    record = await session.get(ProcessedFile, file_id)
    if not record or record.user_id != user.id:
        raise HTTPException(status_code=404, detail="File not found")

    bucket_name = settings.s3_bucket_name
    if bucket_name:
        s3 = _get_s3_client()
        prefix = "magic-clean" if type == "magic" else "cleaned"
        object_name = f"{prefix}/{record.id}_{record.original_name}"
        url = s3.generate_presigned_url('get_object', Params={'Bucket': bucket_name, 'Key': object_name}, ExpiresIn=3600)
        return RedirectResponse(url)
    raise HTTPException(status_code=404, detail="Storage not configured")


# ---------------------------------------------------------------------------
# Export endpoint — Skill: backend-architect + react-patterns
# ---------------------------------------------------------------------------
@file_router.get("/export")
async def export_files(
    format: Literal["csv", "xlsx", "json"] = Query(default="csv"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Export all processed files metadata as CSV, XLSX, or JSON.
    Uses pandas (already in stack) — no S3 required.
    """
    result = await session.execute(
        select(ProcessedFile)
        .where(ProcessedFile.user_id == user.id, ProcessedFile.status == "complete")
        .order_by(ProcessedFile.created_at.desc())
    )
    records = result.scalars().all()

    rows = [{
        "id": r.id,
        "name": r.original_name,
        "size_bytes": r.size_bytes,
        "rows_original": r.rows_original,
        "rows_clean": r.rows_clean,
        "duplicates_removed": r.duplicates_removed,
        "empty_removed": r.empty_removed,
        "whitespace_fixed": r.whitespace_fixed,
        "reduction_pct": round((1 - r.rows_clean / max(r.rows_original, 1)) * 100, 1),
        "processed_at": r.created_at.isoformat(),
    } for r in records]

    if format == "json":
        return StreamingResponse(
            io.BytesIO(json.dumps(rows, indent=2).encode()),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=filecleaner_export.json"}
        )

    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    if format == "xlsx":
        df.to_excel(buf, index=False, engine="openpyxl")
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = "filecleaner_export.xlsx"
    else:
        df.to_csv(buf, index=False)
        media_type = "text/csv"
        filename = "filecleaner_export.csv"
    buf.seek(0)
    return StreamingResponse(buf, media_type=media_type, headers={"Content-Disposition": f"attachment; filename={filename}"})


# ---------------------------------------------------------------------------
# AI Analyze endpoint — Skill: gemini-api-dev
# ---------------------------------------------------------------------------
@file_router.post("/ai-analyze")
async def ai_analyze_file(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """
    Reads first 20 rows of the CSV/JSON/Excel and uses Gemini Flash to suggest
    cleanup rules. Falls back to heuristic analysis if no API key.
    """
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="AI analyze limited to 10MB")

    def analyze_locally(file_content: bytes, fname: str):
        df = _load_df(file_content, fname)
        preview = df.head(20)
        suggestions = []
        for col in preview.columns:
            null_pct = preview[col].isnull().mean()
            if null_pct > 0.5:
                suggestions.append({"column": col, "issue": f"{int(null_pct*100)}% valores nulos", "fix": "Considerar eliminar esta columna", "severity": "high"})
            elif preview[col].dtype == object:
                has_spaces = preview[col].dropna().str.strip().ne(preview[col].dropna()).any()
                if has_spaces:
                    suggestions.append({"column": col, "issue": "Espacios en blanco al inicio/fin", "fix": "Aplicar strip() automáticamente", "severity": "low"})
            if preview[col].dtype == object:
                dup_ratio = 1 - preview[col].nunique() / max(len(preview[col].dropna()), 1)
                if dup_ratio > 0.8:
                    suggestions.append({"column": col, "issue": f"{int(dup_ratio*100)}% valores duplicados", "fix": "Alta repetición — revisar si es categórico", "severity": "medium"})
        return {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "preview_rows": 20,
            "suggestions": suggestions,
            "engine": "heuristic",
        }

    async def analyze_with_gemini(file_content: bytes, fname: str):
        if not settings.gemini_api_key:
            return None
        try:
            df = await run_in_threadpool(_load_df, file_content, fname)
            preview_csv = df.head(20).to_csv(index=False)
            from google import genai
            client = genai.Client(api_key=settings.gemini_api_key)
            prompt = f"""Analiza este CSV y sugiere reglas de limpieza de datos. Responde en JSON:
{{
  "total_rows": number,
  "total_columns": number,
  "suggestions": [
    {{"column": "nombre_columna", "issue": "descripcion del problema", "fix": "accion recomendada", "severity": "high|medium|low"}}
  ],
  "summary": "resumen general de calidad de los datos"
}}

Primeras 20 filas del CSV:
{preview_csv[:3000]}"""
            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=prompt,
                config={"response_mime_type": "application/json"}
            )
            result = json.loads(response.text)
            result["engine"] = "gemini"
            result["preview_rows"] = min(20, len(df))
            return result
        except Exception as e:
            logger.warning(f"Gemini AI analyze failed: {e}")
            return None

    result = await analyze_with_gemini(content, file.filename or "file.csv")
    if result is None:
        result = await run_in_threadpool(analyze_locally, content, file.filename or "file.csv")
    return result


@file_router.delete("/{file_id}")
async def delete_file(
    file_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    record = await session.get(ProcessedFile, file_id)
    if not record or record.user_id != user.id:
        raise HTTPException(status_code=404, detail="File not found")

    bucket_name = settings.s3_bucket_name
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
    domain_routers=[file_router, demo_router, settings_router]
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
