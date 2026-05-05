import logging
import socket
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Dict

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.security import APIKeyHeader
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .database import get_session
from .outbox_models import SystemOutbox

logger = logging.getLogger(__name__)

# Job Handler Registry
# Format: { ("app_name", "job_type"): handler_function }
JobHandler = Callable[[Dict[str, Any]], Awaitable[Any]]
_JOB_HANDLERS: Dict[tuple[str, str], JobHandler] = {}

def register_job_handler(app_name: str, job_type: str, handler: JobHandler):
    _JOB_HANDLERS[(app_name, job_type)] = handler
    logger.info(f"Registered job handler for {app_name}.{job_type}")

def get_instance_id() -> str:
    return f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"

async def acquire_job(session: AsyncSession, filter_app: str | None = None) -> SystemOutbox | None:
    """Atomically lock and return the next available job."""
    instance_id = get_instance_id()
    
    app_filter_sql = f"AND app_name = '{filter_app}'" if filter_app else ""
    
    # We use raw SQL for FOR UPDATE SKIP LOCKED
    query = f"""
        UPDATE system_outbox 
        SET status = 'processing', 
            locked_at = NOW(),
            locked_by = :instance_id
        WHERE id = (
            SELECT id FROM system_outbox 
            WHERE status = 'pending' 
            AND next_retry_at <= NOW()
            AND (locked_at IS NULL OR locked_at < NOW() - INTERVAL '10 minutes')
            {app_filter_sql}
            ORDER BY priority ASC, created_at ASC
            LIMIT 1
            FOR UPDATE SKIP LOCKED
        )
        RETURNING *;
    """
    
    result = await session.execute(text(query), {"instance_id": instance_id})
    row = result.fetchone()
    
    if row:
        job_dict = dict(row._mapping)
        import json
        if isinstance(job_dict['payload'], str):
            job_dict['payload'] = json.loads(job_dict['payload'])
        if isinstance(job_dict.get('result'), str):
            job_dict['result'] = json.loads(job_dict['result'])
        return SystemOutbox(**job_dict)
    
    return None

async def complete_job(session: AsyncSession, job_id: uuid.UUID, result: Any):
    import json
    result_json = json.dumps(result) if result is not None else None
    query = text("""
        UPDATE system_outbox
        SET status = 'completed',
            completed_at = NOW(),
            result = :result,
            locked_at = NULL,
            locked_by = NULL,
            updated_at = NOW()
        WHERE id = :job_id
    """)
    await session.execute(query, {"job_id": job_id, "result": result_json})
    await session.commit()

async def fail_job(session: AsyncSession, job_id: uuid.UUID, error_message: str):
    job_query = text("SELECT attempts, max_attempts FROM system_outbox WHERE id = :job_id FOR UPDATE")
    res = await session.execute(job_query, {"job_id": job_id})
    job = res.fetchone()
    if not job:
        return
        
    attempts = job.attempts + 1
    max_attempts = job.max_attempts
    
    status = 'failed' if attempts >= max_attempts else 'pending'
    
    # Calculate backoff (exponential: 5min, 25min, etc)
    next_retry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=5 ** attempts)
    
    update_query = text("""
        UPDATE system_outbox
        SET status = :status,
            error_message = :error,
            attempts = :attempts,
            next_retry_at = :next_retry,
            locked_at = NULL,
            locked_by = NULL,
            updated_at = NOW()
        WHERE id = :job_id
    """)
    await session.execute(update_query, {
        "status": status,
        "error": error_message,
        "attempts": attempts,
        "next_retry": next_retry,
        "job_id": job_id
    })
    await session.commit()

async def execute_job(job: SystemOutbox) -> Any:
    handler = _JOB_HANDLERS.get((job.app_name, job.job_type))
    if not handler:
        raise ValueError(f"No handler registered for {job.app_name}.{job.job_type}")
    
    return await handler(job.payload)

async def run_worker_cycle(filter_app: str | None = None):
    """Processes jobs until no more are available or until max_duration is reached."""
    from .database import get_managed_session
    
    processed = 0
    start_time = time.time()
    max_duration = 240  # 4 minutes
    
    while time.time() - start_time < max_duration:
        async with get_managed_session() as session:
            job = await acquire_job(session, filter_app)
            if not job:
                break # No more jobs
                
            try:
                result = await execute_job(job)
                await complete_job(session, job.id, result)
            except Exception as e:
                logger.error(f"Job {job.id} failed: {e}", exc_info=True)
                await fail_job(session, job.id, str(e))
                
            processed += 1
            
    logger.info(f"Worker cycle finished. Processed {processed} jobs.")
    return processed

# --- Router for cron-job.org ---
worker_router = APIRouter(prefix="/worker", tags=["Worker"])
cron_auth = APIKeyHeader(name="Authorization", auto_error=True)

def verify_cron_secret(auth_header: str = Depends(cron_auth)):
    settings = get_settings()
    expected = f"Bearer {settings.cron_secret}"
    if auth_header != expected:
        raise HTTPException(status_code=401, detail="Invalid CRON_SECRET")
    return True

@worker_router.post("/process")
async def process_jobs(
    background_tasks: BackgroundTasks,
    filter: str | None = None,
    priority: str | None = None,
    authenticated: bool = Depends(verify_cron_secret)
):
    """
    Triggered by cron-job.org.
    Enqueues the run_worker_cycle in background.
    """
    background_tasks.add_task(run_worker_cycle, filter_app=filter)
    return {"status": "accepted", "message": f"Worker cycle started for {filter or 'all'}"}

@worker_router.post("/cleanup")
async def cleanup_old_jobs(
    background_tasks: BackgroundTasks,
    authenticated: bool = Depends(verify_cron_secret)
):
    """
    Cleanup completed/dead_letter jobs older than 30 days.
    """
    async def run_cleanup():
        from .database import get_managed_session
        async with get_managed_session() as session:
            query = text("""
                DELETE FROM system_outbox 
                WHERE status IN ('completed', 'failed', 'dead_letter')
                AND created_at < NOW() - INTERVAL '30 days'
            """)
            await session.execute(query)
            await session.commit()
            
    background_tasks.add_task(run_cleanup)
    return {"status": "accepted", "message": "Cleanup started"}
