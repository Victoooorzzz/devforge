import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "packages"))

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel, select
from typing import Optional, List
from datetime import datetime, timezone
import pandas as pd
import io
import boto3

from fastapi.concurrency import run_in_threadpool
from backend_core import create_app, get_current_user, get_session, User

# SQL migrations needed for new columns on existing DB:
# ALTER TABLE processed_files ADD COLUMN IF NOT EXISTS rows_original INTEGER DEFAULT 0;
# ALTER TABLE processed_files ADD COLUMN IF NOT EXISTS rows_clean INTEGER DEFAULT 0;
# ALTER TABLE processed_files ADD COLUMN IF NOT EXISTS duplicates_removed INTEGER DEFAULT 0;
# ALTER TABLE processed_files ADD COLUMN IF NOT EXISTS empty_removed INTEGER DEFAULT 0;
# ALTER TABLE processed_files ADD COLUMN IF NOT EXISTS whitespace_fixed INTEGER DEFAULT 0;

# --- Models ---
class ProcessedFile(SQLModel, table=True):
    __tablename__ = "processed_files"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    original_name: str
    size_bytes: int
    status: str = Field(default="processing")
    download_url: Optional[str] = None
    # Cleanup stats
    rows_original: int = Field(default=0)
    rows_clean: int = Field(default=0)
    duplicates_removed: int = Field(default=0)
    empty_removed: int = Field(default=0)
    whitespace_fixed: int = Field(default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def _get_s3_client():
    return boto3.client(
        's3',
        endpoint_url=os.getenv("R2_ENDPOINT_URL"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
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


# --- Router ---
file_router = APIRouter(prefix="/files", tags=["files"])


@file_router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if not user.has_access:
        raise HTTPException(status_code=403, detail="Active subscription or trial required")

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

    try:
        def process_dataframe(file_content: bytes, fname: str):
            df = _load_df(file_content, fname)
            rows_original = len(df)

            # Step 1: Remove completely empty rows
            df_before_empty = len(df)
            df.dropna(how='all', inplace=True)
            empty_removed = df_before_empty - len(df)

            # Step 2: Strip whitespace on string columns — count cells changed
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
            process_dataframe, content, record.original_name
        )

        bucket_name = os.getenv("R2_BUCKET_NAME")
        if bucket_name:
            s3 = _get_s3_client()
            object_name = f"cleaned/{record.id}_{record.original_name}"
            s3.upload_fileobj(out_buf, bucket_name, object_name)

        record.status = "complete"
        record.download_url = f"/files/{record.id}/download"
        record.rows_original = rows_original
        record.rows_clean = rows_clean
        record.duplicates_removed = dups
        record.empty_removed = empty
        record.whitespace_fixed = ws
        session.add(record)
        await session.commit()
        await session.refresh(record)

    except Exception as e:
        record.status = "error"
        session.add(record)
        await session.commit()

    return {
        "id": record.id,
        "status": record.status,
        "download_url": record.download_url,
        "report": {
            "rows_original": record.rows_original,
            "rows_clean": record.rows_clean,
            "duplicates_removed": record.duplicates_removed,
            "empty_removed": record.empty_removed,
            "whitespace_fixed": record.whitespace_fixed,
            "rows_saved": record.rows_original - record.rows_clean,
        }
    }


@file_router.post("/fuzzy-check")
async def fuzzy_check(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    threshold: int = 85,
):
    """
    Detecta duplicados 'blandos' usando fuzzy matching (thefuzz).
    Retorna grupos de filas similares pero no idénticas.
    threshold: similitud mínima 0-100 (default 85).
    """
    if not user.has_access:
        raise HTTPException(status_code=403, detail="Active subscription or trial required")

    content = await file.read()

    def run_fuzzy(file_content: bytes, fname: str, thresh: int):
        try:
            from thefuzz import fuzz
        except ImportError:
            return {"error": "thefuzz not installed. Run: pip install thefuzz[speedup]", "groups": []}

        df = _load_df(file_content, fname)

        # Convertir cada fila a string para comparar
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
                groups.append({
                    "rows": group,
                    "sample": str_rows[i][:200],
                    "count": len(group),
                })

        return {
            "total_rows": n,
            "fuzzy_groups_found": len(groups),
            "rows_affected": sum(g["count"] for g in groups),
            "threshold_used": thresh,
            "groups": groups[:50],  # Limit preview to 50 groups
        }

    result = await run_in_threadpool(run_fuzzy, content, file.filename or "file.csv", threshold)
    return result


@file_router.post("/magic-clean")
async def magic_clean(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Normalización avanzada: estandariza fechas, teléfonos, emails, precios y texto.
    Retorna el archivo limpio para descarga + reporte de cambios.
    """
    if not user.has_access:
        raise HTTPException(status_code=403, detail="Active subscription or trial required")

    content = await file.read()

    def run_magic(file_content: bytes, fname: str):
        import re

        df = _load_df(file_content, fname)
        changes: dict = {}

        for col in df.columns:
            col_lower = col.lower()
            series = df[col]

            # --- Email columns ---
            if any(k in col_lower for k in ["email", "correo", "mail"]):
                before = series.copy()
                df[col] = series.astype(str).str.strip().str.lower().str.replace(r"\s+", "", regex=True)
                changed = (df[col] != before.astype(str)).sum()
                if changed: changes[col] = f"{changed} emails normalizados"

            # --- Phone columns ---
            elif any(k in col_lower for k in ["phone", "telefono", "tel", "celular", "mobile"]):
                before = series.copy()
                def normalize_phone(v):
                    if pd.isna(v): return v
                    digits = re.sub(r"\D", "", str(v))
                    if len(digits) == 9: return f"+51 {digits[:3]} {digits[3:6]} {digits[6:]}"
                    if len(digits) == 10: return f"+1 ({digits[:3]}) {digits[3:6]}-{digits[6:]}"
                    return digits if digits else str(v)
                df[col] = series.apply(normalize_phone)
                changed = (df[col].astype(str) != before.astype(str)).sum()
                if changed: changes[col] = f"{changed} teléfonos normalizados"

            # --- Price / amount columns ---
            elif any(k in col_lower for k in ["price", "precio", "amount", "monto", "cost", "costo", "total", "importe"]):
                before = series.copy()
                def clean_price(v):
                    if pd.isna(v): return v
                    cleaned = re.sub(r"[^\d.,]", "", str(v)).replace(",", ".")
                    try: return float(cleaned)
                    except: return v
                df[col] = series.apply(clean_price)
                changed = (df[col].astype(str) != before.astype(str)).sum()
                if changed: changes[col] = f"{changed} precios normalizados"

            # --- Date columns ---
            elif any(k in col_lower for k in ["date", "fecha", "created", "updated", "nacimiento", "birthday"]):
                before = series.copy()
                df[col] = pd.to_datetime(series, dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d').where(
                    pd.to_datetime(series, dayfirst=True, errors='coerce').notna(), other=series.astype(str)
                )
                changed = (df[col].astype(str) != before.astype(str)).sum()
                if changed: changes[col] = f"{changed} fechas estandarizadas (YYYY-MM-DD)"

            # --- Name / text columns ---
            elif any(k in col_lower for k in ["name", "nombre", "apellido", "last", "first", "ciudad", "city"]):
                before = series.copy()
                df[col] = series.astype(str).str.strip().str.title()
                changed = (df[col] != before.astype(str)).sum()
                if changed: changes[col] = f"{changed} nombres formateados (Title Case)"

        # Final: remove duplicate + empty rows after normalization
        rows_before = len(df)
        df.dropna(how='all', inplace=True)
        df.drop_duplicates(inplace=True)
        rows_after = len(df)

        buf = _save_df(df, fname)
        return buf, changes, rows_before, rows_after

    out_buf, changes, rows_before, rows_after = await run_in_threadpool(
        run_magic, content, file.filename or "file.csv"
    )

    # Save to R2 with magic-clean prefix
    bucket_name = os.getenv("R2_BUCKET_NAME")
    download_url = None
    if bucket_name:
        s3 = _get_s3_client()
        object_name = f"magic-clean/{user.id}_{file.filename}"
        s3.upload_fileobj(out_buf, bucket_name, object_name)
        download_url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': object_name},
            ExpiresIn=3600
        )

    return {
        "status": "complete",
        "download_url": download_url,
        "report": {
            "columns_cleaned": changes,
            "rows_before": rows_before,
            "rows_after": rows_after,
            "rows_removed": rows_before - rows_after,
        }
    }


@file_router.get("/list")
async def list_files(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(ProcessedFile).where(ProcessedFile.user_id == user.id).order_by(ProcessedFile.created_at.desc())
    )
    return [
        {
            "id": f.id,
            "name": f.original_name,
            "size": f.size_bytes,
            "status": f.status,
            "download_url": f.download_url,
            "created_at": f.created_at.isoformat(),
            "report": {
                "rows_original": f.rows_original,
                "rows_clean": f.rows_clean,
                "duplicates_removed": f.duplicates_removed,
                "empty_removed": f.empty_removed,
                "whitespace_fixed": f.whitespace_fixed,
            }
        }
        for f in result.scalars().all()
    ]


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


# --- Standalone app (dev) ---
app = create_app(title="File Cleaner", description="Upload, process, and clean your files", domain_routers=[file_router])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
